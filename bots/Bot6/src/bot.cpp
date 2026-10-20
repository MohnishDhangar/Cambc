// V6.0: independent macro-strategy policy + shared team task claims.
// Deliberately conservative executor: legal actions first, optimization later.
#include "bot.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <optional>
#include <span>
#include <variant>

using namespace cambc;
namespace {
int distance(vec2 a, vec2 b) { return int(a.chebyshev_distance(b)); }
bitboard around(vec2 p, int radius) {
    bitboard b;
    b.draw_chebyshev(p, radius);
    return b;
}
unsigned identity(const champion& c) {
    return static_cast<unsigned>(static_cast<handle_champion_t>(c));
}
bitboard occupied() {
    auto b = vision::champion_tiles() | vision::camp_tiles() | vision::teleport_tiles();
    b.set(self().position(), false);
    return b;
}
float clamp_value(float x, float a, float b) { return std::max(a, std::min(x,b)); }
const char* mode_name(MacroMode m) {
    switch(m) {
        case MacroMode::economy: return "economy";
        case MacroMode::tempo_farm: return "tempo";
        case MacroMode::contest: return "contest";
        case MacroMode::objective: return "objective";
        default: return "adaptive";
    }
}
const char* job_name(Job j) {
    switch(j) {
        case Job::bank: return "bank";
        case Job::recover: return "recover";
        case Job::intercept: return "intercept";
        case Job::siege: return "siege";
        default: return "farm";
    }
}
}

void Bot::initialize() {
    action = "initialize";
    auto& me = self();
    allies = champions(team::ally);
    enemies = champions(team::enemy);
    std::sort(allies.begin(), allies.end(), [](const auto& a, const auto& b) {
        return identity(a) < identity(b);
    });
    for (int i=0;i<int(allies.size());++i)
        if (allies[i] == me) slot=i;

    terrain = map::walls() | map::holes() | map::altars() | map::spawn_region(team::enemy);
    for (const auto& g: map::camp_groups()) {
        if (g.camps().empty()) continue;
        CampPlan p{g, g.camps().front().spawn_position()};
        for (const auto& member:g) {
            p.base_hp += member.base_stats().base_health;
            p.base_damage += member.base_stats().base_strength;
            ++p.members;
        }
        // Engine-provided design statistics avoid hard-coded Week 2 camp IDs.
        p.major = p.base_hp >= 4200.f && g.gem_value() > 0;
        camps.push_back(p);
    }
    bitboard visited;
    home_distance.compute(terrain, map::spawn_region(team::ally), visited);
    bitboard bank_goals;
    for (auto p: map::altars().positions())
        bank_goals |= around(p, constants::submit_gems_range);
    bank_goals &= ~terrain;
    if (!bank_goals.is_empty()) altar_distance.compute(terrain, bank_goals, visited);

    auto type=me.champion_name();
    caster = type == champion_type::stellar || type == champion_type::prism
        || type == champion_type::cassi || type == champion_type::tavi;
    if (slot < 8) shared_memory[slot]=0;
    me.set_priority(90-slot);
    initialized=true;
}

void Bot::observe() {
    action="observe";
    shared_memory.read(0, std::span{claims});
}

float Bot::danger(vec2 p) const {
    float total=0.f;
    for (const auto& e:enemies) {
        if (!e.is_alive() || !e.is_visible()) continue;
        if (distance(p,e.position())<=e.attack_range()+1)
            total += e.strength()+45.f;
    }
    return total;
}

float Bot::clear_time(const CampPlan& g) const {
    const auto& me=self();
    float dps=std::max(28.f,me.strength());
    for (const auto& a:me.abilities())
        if (a.is_damage() || a.is_aoe_damage()) dps+=a.damage_amount()/10.f;
    if (me.champion_name()==champion_type::varg)
        dps *= std::min(2.2f,1.f+0.32f*(g.members-1));
    return g.base_hp/std::max(28.f,dps);
}

MacroMode Bot::macro_mode() const {
#ifndef V6_DEFAULT_MACRO
#define V6_DEFAULT_MACRO 4
#endif
    constexpr int selected=V6_DEFAULT_MACRO;
    if (selected>=0 && selected<4) return static_cast<MacroMode>(selected);
    // Auto-switching policy: does not assume an unobservable opponent state.
    const auto& me=self();
    if (me.gem_count() >= static_cast<unsigned>(params.bank_gems))
        return MacroMode::tempo_farm;
    if (round<200 && me.gold_count()<static_cast<unsigned>(params.shop_gold))
        return MacroMode::economy;
    for (const auto& enemy:enemies)
        if (enemy.is_alive() && enemy.is_visible()
            && distance(me.position(),enemy.position())<=5
            && enemy.gem_count()>=15 && me.health()>me.max_health()*.62f)
            return MacroMode::contest;
    bool only_major=true;
    for (const auto& g:camps)
        if (g.group.gem_value()>0 && !g.major) only_major=false;
    if (only_major) return MacroMode::objective;
    return MacroMode::tempo_farm;
}

float Bot::camp_utility(int i, MacroMode mode) const {
    const auto& me=self();
    const auto& g=camps[i];
    if (round<g.avoid_until) return -1e8f;
    int d=distance(me.position(),g.centre);
    if (g.group.gem_value()==0 && round>450) return -1e8f;

    // Observe lifecycle only when the camp's spawn location is visible.
    bool visible=false,ready=false;
    for (const auto& c:g.group)
        if (vision::visible_tiles().is_set(c.spawn_position())) {visible=true;break;}
    if (visible) {
        auto state=g.group.state();
        if (auto respawn=std::get_if<map::camp_group_respawning>(&state)) {
            if (respawn->timer>std::max(12,d+3)) return -1e8f;
        }
        ready=std::holds_alternative<map::camp_group_reward_available>(state);
    }
    const float work=ready?0.f:clear_time(g);
    const float exposed=(!ready && g.base_damage>0)
        ?g.base_damage*(work/7.f + 1.f)/std::max(1.f,me.health()) : 0.f;
    if (exposed>1.75f && !g.major) return -1e8f;
    if (g.major && (round<160 || (!caster && me.strength()<145.f))) return -1e8f;
    float gold=params.gold_weight;
    if (mode==MacroMode::economy) gold=.8f;
    if (mode==MacroMode::tempo_farm) gold=.11f;
    float bounty=float(g.group.gem_value()) + gold*float(g.group.gold_value());
    if (ready) bounty+=12.f;
    float reward=bounty/std::max(3.f, 4.f + params.distance_weight*d + work);
    reward*=g.major?(mode==MacroMode::objective?2.0f:0.7f):1.f;
    if (mode==MacroMode::tempo_farm) reward*=params.farm_bonus;
    float bank_dist=float(altar_distance.get(g.centre));
    if (bank_dist < distance_field::unreachable)
        reward /= 1.f + .004f * bank_dist;
    const float peril=danger(g.centre) * params.risk_weight
        /std::max(1.f,me.health());
    reward /= 1.f+peril+std::max(0.f,exposed-0.5f);
    // Team task reservations are stronger than per-champion greedy choices.
    for (int j=0;j<int(allies.size()) && j<8;++j)
        if (j!=slot && claims[j]==i+1)
            reward *= ready?0.015f:0.25f;
    if (held_target==i) reward*=1.14f; // prevent pointless oscillation
    return reward;
}

Bot::Plan Bot::select_plan(MacroMode mode) {
    auto& me=self();
    Plan best;
    best.macro=mode;
    if (!me.is_alive()) return best;
    const bool home=map::spawn_region(team::ally).is_set(me.position());
    const auto hp=me.health()/std::max(1.f,me.max_health());

    bool bank_now=me.gem_count()>=static_cast<unsigned>(params.bank_gems)
        || (me.gem_count()>0 && (hp<.52f || danger(me.position())>0
             || round>1200));
    if (me.gem_count()>0 && mode==MacroMode::tempo_farm && me.gem_count()>=12)
        bank_now=true;
    if (bank_now) {best.job=Job::bank;best.utility=1e6f;return best;}
    if (!home && (hp<params.health_reserve
        || (me.gem_count()==0 && me.gold_count()>=static_cast<unsigned>(params.shop_gold)
           && round>last_shop_round+60 && hp<.87f))) {
        best.job=Job::recover;best.utility=1e5f;return best;
    }

    const bool pressure=(mode==MacroMode::contest);
    if (pressure && hp>.5f) {
        for (const auto& e:enemies) {
            if (!e.is_visible() || !e.is_alive()) continue;
            int d=distance(me.position(),e.position());
            if (d>7) continue;
            float score=50.f/(1+d)+e.gem_count()*1.7f
                +clamp_value((me.health()-e.health())/120.f,-8.f,8.f);
            if (score>best.utility) {
                best.job=Job::intercept;
                best.enemy_target=e.position();
                best.utility=score*params.contest_bonus;
            }
        }
        if (best.job==Job::intercept && best.utility>6.f) return best;
    }

    best.utility=-1e8f;
    for (int i=0;i<int(camps.size());++i) {
        if (fuel_remaining()<28000) break;
        float u=camp_utility(i,mode);
        if (u>best.utility) {
            best.utility=u;
            best.camp_index=i;
            best.job=camps[i].major?Job::siege:Job::farm;
        }
    }
    if (best.utility<0) {
        best.job=Job::recover;
        best.camp_index=-1;
    }
    return best;
}

void Bot::publish_claim(int target) {
    held_target=target;
    if (slot<8) shared_memory[slot]=(target>=0 && target<254)?target+1:0;
}

bool Bot::buy() {
    action="shop";
    auto& me=self();
    if (!me.is_alive()) return false;
    const bool home=map::spawn_region(team::ally).is_set(me.position());
    if (!home && me.champion_name()!=champion_type::tavi) return false;
    bool done=false;
    auto counts=me.item_count();
    for (int n=0;n<8 && fuel_remaining()>16000;++n) {
        item_type item=caster?item_type::power_shard_of_focus:item_type::power_shard_of_strength;
        if (!caster && counts[item_type::monster_emblem_of_strength]==0)
            item=item_type::monster_shard_of_strength;
        else if (!caster && counts[item_type::jungle_emblem_of_strength]==0)
            item=item_type::jungle_shard_of_strength;
        else if (home && me.champion_name()==champion_type::ryth
                 && counts[item_type::durability_emblem_of_health]==0)
            item=item_type::durability_shard_of_health;
        if (!me.can_buy(item)) break;
        me.buy(item);
        done=true;
        counts=me.item_count();
        last_shop_round=round;
    }
    return done;
}

bool Bot::try_combat(const unit& target,bool is_enemy) {
    auto& me=self();
    if (fuel_remaining()<18000 || !target.is_visible() || target.health()<=0)
        return false;
    const vec2 goal=target.position();
    bool acted=false;
    if (me.can_cast()) {
        float best=-1.f;
        std::optional<ability> selected;
        for (const auto& spell:me.abilities()) {
            if (!spell.is_ready() || !spell.info()) continue;
            if (!(spell.is_damage() || spell.is_aoe_damage() || spell.is_cc())) continue;
            if (!spell.valid_tiles().is_set(goal)) continue;
            if (is_enemy?!(spell.can_target_enemies() || spell.can_target_ground())
                       :!(spell.can_target_camps() || spell.can_target_ground())) continue;
            const bool exclusive=std::visit([](const auto& data){
                return data.exclusive_with_movement;},*spell.info());
            if (walked && exclusive) continue;
            float value=spell.damage_amount()+(spell.is_cc()?45.f:0.f);
            if (value>best) {best=value;selected=spell;}
        }
        if (selected) {
            action="cast";
            if (selected->can_target_ground()) acted=selected->use(goal);
            else if (is_enemy) acted=selected->use(static_cast<const champion&>(target));
            else acted=selected->use(static_cast<const camp&>(target));
        }
    }
    for (int n=0;n<3 && fuel_remaining()>14000;++n) {
        if (!target.is_visible() || target.health()<=0
            || !me.attack_tiles().is_set(target.position())) break;
        if (!me.can_attack()) {
            bool reset=false;
            for (const auto& a:me.abilities())
                if (a.is_attack_reset() && a.is_ready()) {
                    reset=a.use(); break;
                }
            if (!reset || !me.can_attack()) break;
        }
        action="attack";
        me.attack(target);
        acted=true;
    }
    return acted;
}

bool Bot::attack_visible_enemy(bool chase) {
    auto& me=self();
    std::optional<champion> victim;
    float top=-1e8f;
    for (const auto& e:enemies) {
        if (!e.is_visible() || !e.is_alive()) continue;
        int d=distance(me.position(),e.position());
        if (d>(chase?7:me.attack_range()+1)) continue;
        float value=100.f/(1+d)+e.gem_count()*2.f
            -e.health()*.005f;
        if (value>top) {top=value;victim=e;}
    }
    if (!victim || me.health()<me.max_health()*.32f) return false;
    if (try_combat(*victim,true)) return true;
    if (!chase) return false;
    bitboard goals=around(victim->position(),me.attack_range());
    return navigate(goals,true);
}

bool Bot::navigate(bitboard goals,bool flee) {
    action="navigate";
    auto& me=self();
    if (fuel_remaining()<25000 || !me.can_move() || me.is_teleporting()
        || me.is_recalling() || me.is_submitting_gems()) return false;
    const vec2 origin=me.position();
    auto blocked=terrain | occupied();
    blocked.set(origin,false);
    goals &= ~blocked;
    if (goals.is_empty() || goals.is_set(origin)) return false;
    distance_field field;
    bitboard visited;
    field.compute(blocked,goals,visited);
    const float here=field.get(origin);
    if (here>=distance_field::unreachable) return false;
    bitboard legal=(blocked.reachable_tiles(origin,me.base_stats().base_move_speed) & ~blocked);
    const float limit=here + (flee?danger(origin)*.13f:0.f);
    std::vector<std::pair<float,vec2>> options;
    for (auto tile:legal.positions()) {
        if (tile==origin || occupied().is_set(tile) || terrain.is_set(tile)) continue;
        const float remaining=field.get(tile);
        if (remaining>=distance_field::unreachable) continue;
        const float value=remaining+(flee?danger(tile)*.13f:0.f);
        if (value<limit-.005f) options.emplace_back(value,tile);
    }
    std::sort(options.begin(),options.end(),[](const auto& x,const auto& y) {
        return x.first<y.first;
    });
    // SDK reachable_tiles can suggest occupied landings. Error 22 is a
    // recoverable destination rejection (seen in live v5 and v6 smoke logs).
    // Try alternatives; propagate other engine errors rather than hiding bugs.
    for (const auto& option:options) {
        if (fuel_remaining()<18000) break;
        const vec2 tile=option.second;
        if (occupied().is_set(tile) || terrain.is_set(tile)) continue;
        action="walk";
        try {
            if (me.move_absolute(tile)) {walked=true;return true;}
        } catch (const cambc::error& e) {
            if (e.code()!=error_code::invalid_action_move_bad_destination)
                throw;
        }
    }
    return false;
}

bool Bot::do_bank() {
    action="bank";
    auto& me=self();
    if (!me.gem_count()) return false;
    bitboard goals;
    for (auto altar:map::altars().positions()) {
        if (distance(me.position(),altar)<=constants::submit_gems_range) {
            if (vision::has_altar_lock(altar)) {
                const auto lock=vision::altar_lock_at(altar);
                if (lock.is_enemy()) {
                    if (me.can_attack() && me.attack_tiles().is_set(altar)) {
                        action="unlock";
                        me.attack(lock);
                    }
                    continue;
                }
            }
            if (danger(me.position())*std::max(2.f,me.gem_count()/10.f)
                 <me.health()*.90f) {
                action="submit";
                me.submit_gems(altar);
                return true;
            }
        }
        goals |= around(altar, constants::submit_gems_range);
    }
    return navigate(goals,true);
}

bool Bot::do_recover() {
    action="recover";
    auto& me=self();
    if (map::spawn_region(team::ally).is_set(me.position())) return false;
    if (danger(me.position())<1.f &&
        home_distance.get(me.position())>constants::recall_time+2) {
        me.recall();
        return true;
    }
    return navigate(map::spawn_region(team::ally),true);
}

bool Bot::cast_or_attack_camp(const CampPlan& g) {
    action="farm-action";
    auto& me=self();
    std::optional<camp> choice;
    float best=1e9f;
    for (const auto& c:g.group) {
        if (!c.is_visible() || c.health()<=0) continue;
        float value=c.health()+distance(me.position(),c.position())*70.f;
        if (value<best) {best=value;choice=c;}
    }
    if (!choice) return false;
    if (try_combat(*choice,false)) return true;
    // Don't stand on top of camp or teleport tiles.
    if (choice->is_visible() && choice->health()>0) {
        bitboard positions=around(choice->position(),me.attack_range());
        if (navigate(positions)) {
            if (me.can_attack()) try_combat(*choice,false);
            return true;
        }
    }
    return false;
}

bool Bot::do_farm() {
    action="farm";
    if (plan.camp_index<0 || plan.camp_index>=int(camps.size())) return false;
    auto& g=camps[plan.camp_index];
    bool visible=false;
    const auto seen=vision::visible_tiles();
    for (const auto& member:g.group)
        if (seen.is_set(member.spawn_position())) {visible=true;break;}
    if (visible) {
        const auto state=g.group.state();
        if (std::holds_alternative<map::camp_group_reward_available>(state)) {
            // A single designated ally finishes capture while others move on.
            return navigate(g.group.spawn_tiles());
        }
        if (std::holds_alternative<map::camp_group_respawning>(state)) {
            g.avoid_until=round+12;
            publish_claim(-1);
            return false;
        }
        if (cast_or_attack_camp(g)) return true;
    }
    bitboard goals;
    for (const auto& c:g.group)
        goals |= around(c.spawn_position(),std::max(1,self().attack_range()));
    return navigate(goals);
}

bool Bot::do_intercept() {
    action="intercept";
    // Recheck current vision after planner; do not chase speculative positions.
    if (attack_visible_enemy(true)) return true;
    return false;
}

bool Bot::do_siege() {
    action="siege";
    if (plan.camp_index<0) return false;
    // Same legal executor, different macro allocation and objective value.
    return do_farm();
}

void Bot::ward() {
    action="ward";
    auto& me=self();
    if (!me.is_alive() || me.is_teleporting() || me.is_recalling()
        || me.is_submitting_gems() || fuel_remaining()<15000
        || me.ward_cooldown()>0
        || me.restrictions().contains(buff_restrictions::ward)) return;
    auto choice=me.ward_placement_tiles() & map::bushes()
        & ~map::walls() & ~vision::ward_tiles(team::ally);
    auto unseen=choice & ~vision::visible_tiles();
    if (!unseen.is_empty()) choice=unseen;
    if (choice.is_empty()) return;
    // Observation utility: prefer bushes near the selected objective.
    vec2 target=self().position();
    if (plan.camp_index>=0) target=camps[plan.camp_index].centre;
    if (plan.job==Job::intercept) target=plan.enemy_target;
    vec2 best=choice.positions().front();
    for (auto p:choice.positions())
        if (distance(p,target)<distance(best,target)) best=p;
    me.place_ward(best);
}

void Bot::play_turn() {
    if (!initialized) {initialize();return;}
    round=round_number();
    walked=false;
    auto& me=self();
    if (!me.is_alive()) {publish_claim(-1);return;}
    if (me.is_recalling() || me.is_submitting_gems() || me.is_teleporting()) {
        publish_claim(-1);
        return;
    }
    buy(); // Buying need not consume the movement or attack action.
    if (!me.can_move() && !me.can_attack() && !me.can_cast()) {
        publish_claim(-1);
        return;
    }
    observe();
    const auto now=me.position();
    stalled_turns=now==last_position?stalled_turns+1:0;
    last_position=now;
    if (stalled_turns>12 && held_target>=0 && held_target<int(camps.size())) {
        camps[held_target].avoid_until=round+30;
        publish_claim(-1);
        stalled_turns=0;
    }
    const MacroMode mode=macro_mode();
    plan=select_plan(mode);
    if (plan.job==Job::farm || plan.job==Job::siege) publish_claim(plan.camp_index);
    else publish_claim(-1);
    // Avoid spamming long stdout logs: one compact event every ~100 rounds.
    if (slot==0 && round%100==0) {
        std::cout<<"v6 macro "<<round<<" "<<mode_name(mode)<<" "
                 <<job_name(plan.job)<<" target "<<plan.camp_index<<"\n";
    }
    if (plan.job!=Job::bank && me.gem_count()>0 && me.health()<me.max_health()*.45f)
        plan.job=Job::bank;
    if (plan.job==Job::bank) {do_bank();return;}
    if (plan.job==Job::recover) {do_recover();return;}
    // An immediate attack is a tactical opportunity, not a macro-mode switch.
    if (attack_visible_enemy(false)) {ward();return;}
    switch(plan.job) {
        case Job::intercept: do_intercept();break;
        case Job::siege: do_siege();break;
        case Job::farm: do_farm();break;
        case Job::bank: do_bank();break;
        case Job::recover: do_recover();break;
    }
    ward();
}
