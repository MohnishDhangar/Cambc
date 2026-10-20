#include "bot.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <optional>

using namespace cambc;
namespace {
int dist(vec2 a, vec2 b) { return static_cast<int>(a.chebyshev_distance(b)); }
bitboard around(vec2 p, int r) {
    bitboard b;
    b.draw_chebyshev(p, r);
    return b;
}
unsigned id(const champion& c) { return static_cast<unsigned>(static_cast<handle_champion_t>(c)); }
// Query engine-provided camp designs. This covers Week 2 balance changes
// and new camp types without indexing a pre-patch five-element array.
float camp_health(const camp& c) { return c.base_stats().base_health; }
float camp_damage(const camp& c) { return c.base_stats().base_strength; }
bitboard occupied() {
    auto b = vision::champion_tiles() | vision::camp_tiles() | vision::teleport_tiles();
    b.set(self().position(), false);
    return b;
}
}

void Bot::initialize() {
    action = "initialize";
    auto& me = self();
    terrain = map::walls() | map::holes() | map::altars() | map::spawn_region(team::enemy);
    allies = champions(team::ally);
    enemy_roster = champions(team::enemy);
    std::sort(allies.begin(), allies.end(), [](const auto& a, const auto& b) { return id(a) < id(b); });
    for (int i = 0; i < static_cast<int>(allies.size()); ++i)
        if (allies[i] == me) slot = i;
    for (auto& g : map::camp_groups()) {
        auto tiles = g.spawn_tiles();
        Group entry{g, tiles, g.camps().front().spawn_position()};
        for (const auto& c : g) {
            entry.health += camp_health(c);
            entry.damage += camp_damage(c);
            ++entry.members;
        }
        // Week 2 adds a 5,000 HP Golem; treat large objectives as siege work.
        entry.major = g.gem_value() && entry.health >= 4500;
        groups.push_back(std::move(entry));
    }
    objective_map = std::any_of(groups.begin(), groups.end(), [](const Group& g) { return g.major; })
        && std::none_of(groups.begin(), groups.end(), [](const Group& g) { return g.camp.gem_value() && !g.major; });
    const auto type = me.champion_name();
    caster_build = type == champion_type::stellar || type == champion_type::prism || type == champion_type::ren
        || type == champion_type::cassi || (type == champion_type::tavi && objective_map);
    bitboard visited;
    home_distance.compute(terrain, map::spawn_region(team::ally), visited);
    bitboard altar_goals;
    for (auto p : map::altars().positions()) altar_goals |= around(p, constants::submit_gems_range);
    altar_goals &= ~terrain;
    altar_distance.compute(terrain, altar_goals, visited);
    me.set_priority(100 - slot);
    initialized = true;
}

void Bot::claim(int index) {
    target = index;
    // Zero means unassigned. Groups beyond byte range still work without claims.
    if (slot < 8) shared_memory[slot] = index >= 0 && index < 254 ? index + 1 : 0;
}

void Bot::observe() {
    action = "observe";
    shared_memory.read(0, std::span{claims});
    const auto visible = vision::visible_tiles();
    const auto camp_tiles = vision::camp_tiles();
    for (auto& g : groups) {
        g.visible = false;
        for (const auto& c : g.camp)
            if (visible.is_set(c.spawn_position())) { g.visible = true; break; }
        if (!g.visible) {
            if (g.state == 2 && round >= g.ready_round) g.state = 0;
            continue;
        }
        auto state = g.camp.state();
        if (auto respawn = std::get_if<map::camp_group_respawning>(&state)) {
            g.recipient = -1;
            g.state = 2;
            g.ready_round = round + std::max(0, respawn->timer);
        } else if (std::holds_alternative<map::camp_group_reward_available>(state)) {
            g.state = 1;
            g.health = g.damage = 0;
            g.members = 0;
        } else {
            g.recipient = -1;
            g.state = 0;
            g.health = g.damage = 0;
            g.members = 0;
            for (const auto& c : g.camp) {
                const auto p = c.spawn_position();
                if (visible.is_set(p) && !camp_tiles.is_set(p)) continue;
                g.health += c.is_visible() ? c.health() : camp_health(c);
                g.damage += camp_damage(c);
                ++g.members;
            }
        }
    }
}

void Bot::buy_items() {
    action = "buy_items";
    auto& me = self();
    const bool home = me.is_alive() && map::spawn_region(team::ally).is_set(me.position());
    const auto type = me.champion_name();
    if (me.is_alive() && !home && type != champion_type::tavi) return;
    // A crystal is an escape from disconnected terrain and blocked corridors.
    if ((home || !me.is_alive()) && me.can_buy(consumable_type::tp_crystal))
        me.buy(consumable_type::tp_crystal);
    auto counts = me.item_count();
    while (me.gold_count() >= 30 && fuel_remaining() > 15000) {
        item_type item = item_type::power_shard_of_strength;
        if (counts[item_type::monster_emblem_of_strength] == 0)
            item = item_type::monster_shard_of_strength;
        else if (counts[item_type::jungle_emblem_of_strength] == 0)
            item = item_type::jungle_shard_of_strength;
        else if (home && me.max_health() < me.base_stats().base_health + 500)
            item = item_type::power_shard_of_health;
        if (caster_build) {
            item = item_type::power_shard_of_focus;
            if (counts[item_type::power_emblem_of_focus] >= 2 && home
                && !counts[item_type::durability_emblem_of_health]) item = item_type::durability_shard_of_health;
        }
        if (!me.can_buy(item)) break;
        me.buy(item);
        counts = me.item_count();
        last_shop_round = round;
    }
}

float Bot::expected_damage(const Group& g) const {
    float dps = farm_dps;
    if (splash) dps *= std::min(3, std::max(1, g.members));
    const float turns = g.health / std::max(1.f, dps);
    float damage = g.damage * incoming_multiplier;
    if (g.members > 1) damage *= .65f;
    return std::max(0.f, damage * (turns + 2) - std::ceil(turns / 8) * shield_cycle);
}

int Bot::select_camp() {
    action = "select_camp";
    auto& me = self();
    farm_dps = me.strength();
    shield_cycle = 0;
    splash = me.champion_name() == champion_type::varg;
    incoming_multiplier = 1;
    for (const auto& a : me.abilities()) {
        if (a.is_attack_reset()) farm_dps += me.strength() / 8;
        else if (a.is_damage() || a.is_cc() || a.is_aoe_damage()) farm_dps += a.damage_amount() / 8;
        else if (a.is_shield()) shield_cycle = a.shield_amount();
    }
    const auto counts = me.item_count();
    if (counts[item_type::jungle_emblem_of_strength]) incoming_multiplier *= .7f;
    if (counts[item_type::durability_emblem_of_strength]) incoming_multiplier *= .9f;
    const auto health_reserve = me.health() - std::max(120.f, me.max_health() * .18f);
    const auto strength = me.strength();
    const auto enemy_spawn = map::spawn_region(team::enemy).positions().front();
    distance_field travel;
    bitboard visited;
    travel.compute(terrain, around(me.position(), 0), visited);
    float best = -1;
    int choice = -1;
    for (int pass = 0; pass < 2 && choice < 0; ++pass)
    for (int i = 0; i < static_cast<int>(groups.size()); ++i) {
        if (fuel_remaining() < 33000) break;
        const auto& g = groups[i];
        if (g.avoid_until > round || (objective_map && g.major)) continue;
        int distance = distance_field::unreachable;
        for (const auto& c : g.camp) distance = std::min(distance, int(travel.get(c.spawn_position())));
        if (distance == distance_field::unreachable) continue;
        int wait = g.state == 2 ? std::max(0, int(g.ready_round) - int(round) - distance) : 0;
        if (wait > 12) continue;
        int assigned = 0;
        if (i < 254)
            for (int j = 0; j < static_cast<int>(allies.size()) && j < 8; ++j)
                if (j != slot && claims[j] == i + 1) ++assigned;
        // Do not interrupt a teammate's capture or duplicate its farming route.
        if (pass == 0 ? assigned != 0 : (assigned == 0 || g.state != 0)) continue;
        const float damage = g.state == 1 ? 0 : expected_damage(g) / ((assigned + 1) * (assigned + 1));
        if (damage > health_reserve) continue;
        float work = g.state == 1 ? 0 : g.health / std::max(1.f, strength * 1.25f);
        if (me.champion_name() == champion_type::varg) work /= std::min(3, std::max(1, g.members));
        const float bank_trip = altar_distance.get(g.centre) == distance_field::unreachable ? 100.f : altar_distance.get(g.centre);
        const float value = g.camp.gem_value() + g.camp.gold_value() * (round < 700 ? .32f : .12f);
        float score = value / (distance + wait + work / (assigned + 1) + 6 + bank_trip * .35f);
        if (dist(g.centre, enemy_spawn) + 4 < home_distance.get(g.centre)) score *= .65f;
        if (i == target) score *= 1.3f;
        if (score > best) { best = score; choice = i; }
    }
    return choice;
}

void Bot::refresh_threats() {
    threats.clear();
    visible_enemies.clear();
    for (const auto& enemy : enemy_roster) {
        if (!enemy.is_visible() || !enemy.is_alive()) continue;
        visible_enemies.push_back(enemy);
        threats.push_back({enemy.position(), enemy.strength() + 35, enemy.attack_range() + 1});
    }
    for (const auto& g : groups) {
        if (g.state != 0 || !g.visible) continue;
        for (const auto& c : g.camp)
            if (camp_damage(c) > 0 && c.is_visible() && c.health() > 0 && c.is_awake())
                threats.push_back({c.position(), c.strength(), c.attack_range()});
    }
}

float Bot::danger(vec2 tile) const {
    float value = 0;
    for (const auto& t : threats)
        if (dist(tile, t.position) <= t.range) value += t.damage;
    return value;
}

bool Bot::navigate(bitboard goals, bool escape, bool use_dash) {
    action = "navigate";
    if (fuel_remaining() < 18000) return false;
    auto& me = self();
    if (goals.is_set(me.position())) return false;
    auto units = occupied();
    auto blocked = terrain | units;
    blocked.set(me.position(), false);
    goals &= ~blocked;
    if (goals.is_empty()) return false;
    distance_field field;
    bitboard visited;
    // Compute the complete field so dash/crystal destinations in a separate
    // component can be evaluated too.
    field.compute(blocked, goals, visited);
    auto origin = me.position();
    float current = field.get(origin);
    if (escape) current += danger(origin) * 2;
    auto score = [&](vec2 p) {
        return float(field.get(p)) + (escape ? danger(p) * 2 : 0.f);
    };
    // Dashes use the SDK's reachable mask with holes traversable but illegal
    // as landing squares. Normal walking has its own stricter mask below.
    if (use_dash) for (const auto& a : me.abilities()) {
        if (!a.is_dash() || !a.is_ready()) continue;
        auto dash_walls = map::walls() | map::altars() | map::spawn_region(team::enemy) | units;
        auto candidates = dash_walls.reachable_tiles(origin, 2) & ~blocked;
        auto best = origin;
        float value = current - 1.5f;
        for (auto p : candidates.positions()) if (score(p) < value) { value = score(p); best = p; }
        action = "navigate dash";
        if (best != origin && a.use(best)) {
            origin = me.position();
            // A dash changes vision. Refresh occupants before an ordinary step.
            units = occupied();
            blocked = terrain | units;
            blocked.set(origin, false);
            refresh_threats();
            current = score(origin);
        }
    }
    if (me.can_move()) {
        auto candidates = blocked.reachable_tiles(origin, me.base_stats().base_move_speed).positions();
        std::sort(candidates.begin(), candidates.end(), [&](vec2 a, vec2 b) { return score(a) < score(b); });
        for (auto p : candidates) {
            if (p == origin || score(p) >= current) continue;
            action = "navigate walk";
            if (me.move_absolute(p)) { walked = true; return true; } // Retry on hidden occupants.
        }
    }
    // A three-tick crystal is useful only when it beats walking by at least
    // five tiles, or connects a component that walking cannot reach.
    if (me.consumables()[consumable_type::tp_crystal].count() && danger(origin) == 0) {
        auto landings = around(origin, 3) & ~blocked;
        auto best = origin;
        float value = field.get(origin) - 5.f;
        for (auto p : landings.positions())
            if (field.get(p) < value && danger(p) == 0) { value = field.get(p); best = p; }
        action = "navigate crystal";
        if (best != origin && me.consumables()[consumable_type::tp_crystal].use(best)) return true;
    }
    return me.position() != previous;
}

bool Bot::fight(const unit& victim, bool enemy) {
    action = "fight";
    if (fuel_remaining() < 16000) return false;
    auto& me = self();
    if (!victim.is_visible() || victim.health() <= 0) return false;
    const auto position = victim.position();
    const float hp = victim.health();
    bool acted = false;
    // Use targeted and area spells before walking; exclusivity is checked
    // against our record of an ordinary move this turn.
    std::optional<ability> best_spell;
    float best_value = 0;
    for (const auto& a : me.abilities()) {
        if (!a.is_ready() || !a.info()) continue;
        const bool moved = walked;
        const bool exclusive = std::visit([](const auto& info) { return info.exclusive_with_movement; }, *a.info());
        if (moved && exclusive) continue;
        if (!(a.is_damage() || a.is_aoe_damage() || a.is_cc())) continue;
        if (!a.valid_tiles().is_set(position)) continue;
        if (enemy ? !(a.can_target_enemies() || a.can_target_ground()) : !(a.can_target_camps() || a.can_target_ground())) continue;
        float value = a.damage_amount();
        if (a.is_aoe_damage()) {
            const auto radius = a.get<ability_aoe_damage>().radius;
            for (const auto& c : vision::camps())
                if (c.position() != position && dist(c.position(), position) <= radius) value += a.damage_amount();
        }
        if (a.is_cc()) value += enemy ? 60 : victim.strength();
        if (value > best_value) { best_value = value; best_spell = a; }
    }
    if (best_spell && (hp > me.strength() || dist(me.position(), position) > me.attack_range())) {
        bool result;
        if (best_spell->can_target_ground()) result = best_spell->use(position);
        else if (enemy) result = best_spell->use(static_cast<const champion&>(victim));
        else result = best_spell->use(static_cast<const camp&>(victim));
        acted = result;
    }
    action = "fight attacks";
    // Vendetta can reset again after a kill. Every query below is fresh.
    for (int attacks = 0; attacks < 3; ++attacks) {
        if (!victim.is_visible() || victim.health() <= 0 || dist(me.position(), position) > me.attack_range()) break;
        if (!me.can_attack()) {
            bool reset = false;
            for (const auto& a : me.abilities())
                if (a.is_attack_reset() && a.is_ready()) { reset = a.use(); break; }
            if (!reset || !me.can_attack()) break;
        }
        me.attack(victim);
        acted = true;
    }
    action = "fight shield";
    if (!enemy && victim.is_visible() && victim.health() > 0 && danger(me.position()) > 0)
        for (const auto& a : me.abilities())
            if (a.is_shield() && a.is_ready()) { a.use(); acted = true; break; }
    if (acted) stalled = 0;
    return acted;
}

bool Bot::defend() {
    action = "defend";
    auto& me = self();
    std::optional<champion> victim;
    float score = -1;
    for (const auto& c : visible_enemies) {
        if (!c.is_visible() || !c.is_alive()) continue;
        const int d = dist(me.position(), c.position());
        if (d > 4) continue;
        // Fight nearby threats and secure exposed carriers, without chasing.
        float value = 2000.f / (c.health() + 100) + c.gem_count() * .05f - d * .1f;
        if (value > score) { score = value; victim = c; }
    }
    if (!victim) return false;
    if (me.health() < me.max_health() * .35f && victim->health() > me.strength() * 2) return false;
    return fight(*victim, true);
}

void Bot::recover() {
    action = "recover";
    auto& me = self();
    claim(-1);
    const int home = home_distance.get(me.position());
    if (danger(me.position()) == 0 && home > constants::recall_time + 1) {
        me.recall();
        return;
    }
    navigate(map::spawn_region(team::ally), true);
    if (!me.is_teleporting() && me.can_attack()) defend();
}

bool Bot::bank() {
    action = "bank";
    auto& me = self();
    if (!me.gem_count()) return false;
    claim(-1);
    bitboard goals;
    for (auto p : map::altars().positions()) {
        if (dist(me.position(), p) <= constants::submit_gems_range) {
            // submit_gems also attacks an enemy lock. Own locks permit tribute.
            if (vision::has_altar_lock(p)) {
                const auto lock = vision::altar_lock_at(p);
                if (lock.is_enemy()) {
                    if (me.can_attack()) me.attack(lock);
                    // Attack-reset champions can remove five-hit Week 2
                    // altar locks faster, without spending another turn.
                    for (const auto& a : me.abilities()) {
                        if (!me.can_attack() && a.is_attack_reset() && a.is_ready() && a.use()) {
                            if (me.can_attack()) me.attack(lock);
                            break;
                        }
                    }
                    return true;
                }
            }
            const float incoming = danger(me.position());
            const int duration = std::max(1, int(std::ceil(me.gem_count() / 10.f)));
            if (incoming * (duration + 1) + 60.f < me.health() || incoming <= 0.f) {
                me.submit_gems(p);
                return true;
            }
            // If an occupied altar approach looks lethal, attempt a safe
            // approach rather than idling forever on the goal tile.
            bitboard safe_approaches;
            for (auto altar : map::altars().positions())
                for (auto q : (around(altar, constants::submit_gems_range) & ~terrain).positions())
                    if (danger(q) < incoming * .25f) safe_approaches.set(q, true);
            safe_approaches.set(me.position(), false);
            if (!safe_approaches.is_empty() && navigate(safe_approaches, true)) return true;
            returning = true;
            recover();
            return true;
        }
        goals |= around(p, constants::submit_gems_range);
    }
    navigate(goals, me.health() < me.max_health() * .5f);
    return true;
}

bool Bot::capture_group(int index) {
    auto& g = groups[index];
    if (g.recipient >= 0) {
        const auto& a = allies[g.recipient];
        if (!a.is_visible() || !a.is_alive() || a.is_recalling() || a.gem_count()
            || (g.recipient != slot && claims[g.recipient] != index + 1 && !g.tiles.is_set(a.position()))) g.recipient = -1;
    }
    int recipient = g.recipient;
    float best = 1e9f;
    if (recipient < 0) for (int j = 0; j < static_cast<int>(allies.size()); ++j) {
        const auto& a = allies[j];
        if (!a.is_visible() || !a.is_alive() || a.gem_count() || a.is_recalling()
            || a.is_submitting_gems() || a.is_teleporting()) continue;
        const auto position = a.position();
        if (!g.tiles.is_set(position) && (j != slot && (j >= 8 || claims[j] != index + 1))) continue;
        int distance = 65535;
        for (auto p : g.tiles.positions()) distance = std::min(distance, dist(position, p));
        if (distance > 6) continue;
        const auto items = a.item_count();
        int investment = 0, item_index = 0;
        for (const auto count : items) { investment += count * (item_index % 2 ? 5 : 1); ++item_index; }
        const float score = std::min(investment, 20) * 3.f + distance * 4.f - (distance == 0 ? 4.f : 0.f) + j * .001f;
        if (score < best) { best = score; recipient = j; }
    }
    if (recipient < 0) recipient = slot;
    g.recipient = recipient;
    if (recipient == slot) { navigate(g.tiles); stalled = 0; return true; }
    g.avoid_until = round + 12;
    claim(-1);
    if (g.tiles.is_set(self().position())) {
        navigate(around(self().position(), 2) & ~g.tiles & ~terrain);
        return true;
    }
    return false;
}

bool Bot::siege_objective() {
    auto& me = self();
    if (!objective_map || !caster_build || me.health() < me.max_health() * .45f
        || (round < 400 && me.focus() < 180)) return false;
    if (target >= 0 && !groups[target].major && groups[target].state == 1) return false;
    int index = -1, best = 65535;
    for (int i = 0; i < static_cast<int>(groups.size()); ++i) {
        const auto& g = groups[i];
        if (!g.major || g.avoid_until > round || (g.state == 2 && g.ready_round > round + 10)) continue;
        const int score = home_distance.get(g.centre) + (g.state == 2 ? 20 : 0);
        if (score < best) { best = score; index = i; }
    }
    if (index < 0) return false;
    auto& g = groups[index];
    claim(index);
    if (g.state == 1) return capture_group(index);
    bitboard unsafe, firing;
    const auto visible = vision::visible_tiles(), live = vision::camp_tiles();
    for (const auto& c : g.camp) {
        const auto p = c.spawn_position();
        if (visible.is_set(p) && !live.is_set(p)) continue;
        if (camp_damage(c) > 0) unsafe |= around(p, c.attack_range());
    }
    for (const auto& c : g.camp) {
        const auto p = c.spawn_position();
        if (visible.is_set(p) && !live.is_set(p)) continue;
        for (auto q : (around(p, 4) & ~terrain & ~unsafe).positions()) {
            const int dx = q.x - p.x, dy = q.y - p.y;
            if (dx * dx + dy * dy <= 16) firing.set(q, true);
        }
    }
    // Week 2 expands Elk/Monolith ranges and adds Golems. Some objectives
    // have no risk-free spell tile; never abandon all gem income in that case.
    const bool has_safe_firing = !firing.is_empty();
    if (!has_safe_firing) {
        for (const auto& c : g.camp) {
            const auto p = c.spawn_position();
            if (visible.is_set(p) && !live.is_set(p)) continue;
            for (auto q : (around(p, 4) & ~terrain).positions()) {
                const int dx = q.x - p.x, dy = q.y - p.y;
                if (dx * dx + dy * dy <= 16) firing.set(q, true);
            }
        }
    }
    if (firing.is_empty()) return false;
    if (!firing.is_set(me.position())) { navigate(firing, has_safe_firing); return true; }
    if (g.state == 2) return true;
    bool visible_target = false;
    for (const auto& c : g.camp) {
        if (!c.is_visible() || c.health() <= 0) continue;
        const auto p = c.position(), q = me.position();
        const int dx = q.x - p.x, dy = q.y - p.y;
        if (dx * dx + dy * dy > 16) continue;
        visible_target = true;
        fight(c, false);
        if (std::holds_alternative<map::camp_group_reward_available>(g.camp.state())) { g.state = 1; capture_group(index); }
        break;
    }
    if (!visible_target) {
        // Move to another firing lane when terrain blocks line of sight.
        firing &= ~around(me.position(), 1);
        navigate(firing, true);
    }
    scout();
    return true;
}

void Bot::farm() {
    action = "farm";
    auto& me = self();
    if (target >= 0 && (groups[target].state == 2 || groups[target].avoid_until > round)) claim(-1);
    // Preserve an active target to finish the whole group and its capture.
    if (target < 0) claim(select_camp());
    if (target < 0) {
        if (me.health() < me.max_health() * .85f || me.gold_count() >= 150) { returning = true; recover(); }
        else {
            // No safe unclaimed camp: wait near spawn, allowing teammates to
            // finish rather than pulling a camp this champion cannot survive.
            navigate(map::spawn_region(team::ally));
        }
        return;
    }
    auto& g = groups[target];
    if (g.state == 1) {
        if (capture_group(target)) return;
        claim(select_camp());
        if (target >= 0) navigate(around(groups[target].centre, 1));
        return;
    }
    // Do not stand on a respawn tile while waiting for the camp to reappear.
    if (g.state == 2) {
        auto waiting = around(g.centre, 2) & ~g.tiles;
        navigate(waiting);
        return;
    }
    std::optional<camp> victim;
    float value = std::numeric_limits<float>::max();
    for (const auto& c : g.camp) {
        if (!c.is_visible() || c.health() <= 0) continue;
        float score = c.health() + dist(me.position(), c.position()) * 80.f;
        if (me.champion_name() == champion_type::varg) {
            for (const auto& other : g.camp)
                if (other != c && other.is_visible() && dist(c.position(), other.position()) <= 1) score -= 300;
        }
        if (score < value) { value = score; victim = c; }
    }
    if (!victim) { navigate(around(g.centre, 1)); return; }
    fight(*victim, false);
    if (victim->is_visible() && victim->health() > 0) {
        const int range = me.attack_range();
        auto goals = around(victim->position(), range) & ~vision::camp_tiles();
        if (navigate(goals, false, !me.can_attack())) fight(*victim, false);
    } else {
        action = "farm killed camp state";
        // Recheck immediately after a kill; capture can start next round.
        if (std::holds_alternative<map::camp_group_reward_available>(g.camp.state())) {
            g.state = 1;
            capture_group(target);
        }
    }
    action = "farm scout";
    scout();
}

void Bot::scout() {
    action = "scout";
    if (fuel_remaining() < 12000) return;
    auto& me = self();
    if (me.ward_cooldown() > 0 || me.restrictions().contains(buff_restrictions::ward)) return;
    // Put vision into the bush ahead without occupying the destination.
    auto choices = me.ward_placement_tiles() & map::bushes() & ~map::walls() & ~vision::ward_tiles(team::ally);
    if (choices.is_empty()) return;
    const auto unseen = choices & ~vision::visible_tiles();
    if (!unseen.is_empty()) choices = unseen;
    me.place_ward(choices.positions().front());
}

void Bot::play_turn() {
    if (!initialized) { initialize(); return; }
    auto& me = self();
    round = round_number();
    walked = false;
    if (me.is_alive() && (me.is_recalling() || me.is_submitting_gems() || me.is_teleporting())) return;
    buy_items(); // Dead champions may shop too.
    if (!me.is_alive()) { claim(-1); returning = false; return; }
    if (me.is_recalling() || me.is_submitting_gems() || me.is_teleporting()) return;
    if (!me.can_move() && !me.can_attack() && !me.can_cast()) return;
    observe();
    refresh_threats();
    const auto position = me.position();
    stalled = position == previous ? stalled + 1 : 0;
    previous = position;
    const bool home = map::spawn_region(team::ally).is_set(position);
    if (home) {
        returning = false;
        if (me.health() < me.max_health() * .98f) return; // Healing occurs at turn end.
    }
    if (!home && (me.health() < std::max(180.f, me.max_health() * .28f)
        || (me.champion_name() != champion_type::tavi && me.gold_count() >= 180
            && round > last_shop_round + 40 && me.gem_count() == 0))) returning = true;
    if (returning) { recover(); return; }
    if (stalled > 14 && target >= 0 && groups[target].state != 1 && !(objective_map && groups[target].major)) {
        groups[target].avoid_until = round + 35;
        claim(-1);
        stalled = 0;
    }
    // Ordinary damage does not cancel tribute. Avoid discretionary PvP while
    // carrying gems: secure the bag before looking for combat opportunities.
    if (me.gem_count() && bank()) return;
    if (defend()) return;
    if (siege_objective()) return;
    if (objective_map && target >= 0 && groups[target].major) claim(-1);
    farm();
}
