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
int tribute_ticks(unsigned gems) {
    return std::max(constants::submit_gem_minimum_duration, constants::submit_gem_base_duration
        + static_cast<int>(std::ceil(gems * constants::submit_gem_duration_multiplier)));
}
float camp_health(camp_type kind) {
    constexpr float values[]{1350, 2400, 500, 500, 20000};
    return values[static_cast<int>(kind)];
}
float camp_damage(camp_type kind) {
    constexpr float values[]{20, 60, 0, 0, 200};
    return values[static_cast<int>(kind)];
}
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
    bool has_monolith = false, ordinary_gems = false;
    for (auto& g : map::camp_groups()) {
        auto tiles = g.spawn_tiles();
        Group entry{g, tiles, g.camps().front().spawn_position()};
        for (const auto& c : g) {
            entry.health += camp_health(c.kind());
            entry.damage += camp_damage(c.kind());
            ++entry.members;
            entry.monolith |= c.is_monolith();
            if (c.is_monolith()) entry.centre = c.spawn_position();
        }
        has_monolith |= entry.monolith;
        ordinary_gems |= g.gem_value() > 0 && !entry.monolith;
        groups.push_back(std::move(entry));
    }
    monolith_map = has_monolith && !ordinary_gems;
    const auto home = map::spawn_region(team::ally).positions().front();
    const auto away = map::spawn_region(team::enemy).positions().front();
    contested = std::max(map::width(), map::height()) <= 65 || dist(home, away) <= 42;
    enemy_memory.resize(enemy_roster.size());
    bitboard visited;
    home_distance.compute(terrain, map::spawn_region(team::ally), visited);
    bitboard altar_goals;
    for (auto p : map::altars().positions()) {
        auto approaches = around(p, constants::submit_gems_range) & ~terrain;
        altar_goals |= approaches;
        Altar altar{p, distance_field{}, 0};
        altar.distance.compute(terrain, approaches, visited);
        altars.push_back(std::move(altar));
    }
    altar_goals &= ~terrain;
    altar_distance.compute(terrain, altar_goals, visited);
    me.set_priority(100 - slot);
    initialized = true;
}

void Bot::claim(int index) {
    target = index;
    // Zero means unassigned. Groups beyond byte range still work without claims.
    if (slot < 6) {
        const auto value = static_cast<std::uint8_t>(index >= 0 && index < 254 ? index + 1 : 0);
        shared_memory[slot] = value;
        claims[slot] = value;
    }
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
            if (g.state == 2 && round >= g.ready_round) {
                g.state = 0;
                g.health = g.damage = 0;
                g.members = 0;
                for (const auto& c : g.camp) {
                    g.health += camp_health(c.kind());
                    g.damage += camp_damage(c.kind());
                    ++g.members;
                }
            }
            continue;
        }
        auto state = g.camp.state();
        if (auto respawn = std::get_if<map::camp_group_respawning>(&state)) {
            g.state = 2;
            g.ready_round = round + std::max(0, respawn->timer);
        } else if (std::holds_alternative<map::camp_group_reward_available>(state)) {
            g.state = 1;
            g.health = g.damage = 0;
            g.members = 0;
        } else {
            g.state = 0;
            g.health = g.damage = 0;
            g.members = 0;
            for (const auto& c : g.camp) {
                const auto p = c.spawn_position();
                if (visible.is_set(p) && !camp_tiles.is_set(p)) continue;
                g.health += c.is_visible() ? c.health() : camp_health(c.kind());
                g.damage += camp_damage(c.kind());
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
    const bool healer = type == champion_type::willow;
    const bool caster = healer || type == champion_type::stellar || type == champion_type::cassi;
    const bool can_heal = home || !me.is_alive();
    auto counts = me.item_count();
    while (me.gold_count() >= 30 && fuel_remaining() > 15000) {
        const auto monster = caster ? item_type::monster_emblem_of_focus : item_type::monster_emblem_of_strength;
        const auto jungle = caster ? item_type::jungle_emblem_of_focus : item_type::jungle_emblem_of_strength;
        item_type item = caster ? item_type::power_shard_of_focus : item_type::power_shard_of_strength;
        if (!counts[monster])
            item = caster ? item_type::monster_shard_of_focus : item_type::monster_shard_of_strength;
        else if ((contested || monolith_map) && can_heal && !counts[item_type::durability_emblem_of_health])
            item = item_type::durability_shard_of_health;
        else if (!counts[jungle])
            item = caster ? item_type::jungle_shard_of_focus : item_type::jungle_shard_of_strength;
        else if (can_heal && me.max_health() < me.base_stats().base_health + (contested ? 750 : 500))
            item = item_type::power_shard_of_health;
        else if (type == champion_type::tavi && counts[item_type::power_emblem_of_focus] == 0)
            item = item_type::power_shard_of_focus;
        if (!me.can_buy(item)) break;
        me.buy(item);
        counts = me.item_count();
        last_shop_round = round;
    }
    // Equipment comes first. Do not spend the opening camp reward on a crystal.
    if (can_heal && me.gold_count() >= 240 && !me.consumables()[consumable_type::tp_crystal].count()
        && me.can_buy(consumable_type::tp_crystal)) me.buy(consumable_type::tp_crystal);
}

Bot::Fighter Bot::inspect(const champion& c) const {
    const auto position = c.position();
    const float strength = c.strength(), focus = c.focus();
    Fighter result{c, position, c.health(), c.max_health(), strength, strength * 2, 0, 0, c.attack_range() + 1};
    float cast_damage = 0, reset_damage = 0, ready_damage = 0;
    const auto design = champion_designs[static_cast<int>(c.champion_name())].abilities();
    const auto live = c.abilities();
    for (int slot = 0; slot < 2; ++slot) {
        if (!design[slot].info()) continue;
        const bool ready = live[slot].cooldown() <= 1;
        std::visit([&](const auto& a) {
            using A = std::decay_t<decltype(a)>;
            if constexpr (std::is_same_v<A, ability_attack_reset>) {
                reset_damage = strength;
                if (ready) ready_damage = std::max(ready_damage, strength);
            } else if constexpr (std::is_same_v<A, ability_damage> || std::is_same_v<A, ability_aoe_damage>
                || std::is_same_v<A, ability_cc>) {
                const float damage = focus * a.modifier;
                cast_damage = std::max(cast_damage, damage);
                if (ready) {
                    ready_damage = std::max(ready_damage, damage + (std::is_same_v<A, ability_cc> ? strength * .5f : 0.f));
                    result.reach = std::max(result.reach, static_cast<int>(std::ceil(a.range)) + 1);
                }
            } else if constexpr (std::is_same_v<A, ability_dash>) {
                if (ready) result.reach = std::max(result.reach, c.attack_range() + 1 + static_cast<int>(a.range));
            } else if constexpr (std::is_same_v<A, ability_heal>) result.healing = focus * a.modifier / 8;
            else if constexpr (std::is_same_v<A, ability_shield>) result.shielding = focus * a.modifier / 8;
        }, *design[slot].info());
    }
    result.dps += (cast_damage + reset_damage) / 8;
    result.burst += ready_damage;
    return result;
}

bool Bot::favorable(vec2 point, bool carrier) const {
    float our_health = 0, our_damage = 0, their_health = 0, their_damage = 0;
    int our_count = 0, their_count = 0;
    for (const auto& c : friends) {
        const int distance = dist(c.position, point);
        if (distance > 6) continue;
        const float weight = distance <= 3 ? 1.f : .5f;
        our_health += c.health * weight;
        our_damage += (c.dps + c.healing * .5f) * weight;
        ++our_count;
    }
    for (const auto& c : enemies) {
        if (dist(c.position, point) > c.reach + 1) continue;
        their_health += c.health;
        their_damage += c.dps + c.burst * .15f;
        ++their_count;
    }
    if (!their_count) return true;
    if (their_count > our_count + 1) return false;
    return our_health * our_damage > their_health * their_damage * (carrier ? 1.65f : 1.15f);
}

bool Bot::under_pressure() const {
    return danger(self().position(), true) > 0;
}

bool Bot::support() {
    action = "support";
    auto& me = self();
    for (const auto& a : me.abilities()) {
        if (!a.is_heal() || !a.is_ready()) continue;
        const auto range = a.valid_tiles();
        std::optional<champion> patient;
        float best = 0;
        for (const auto& ally : allies) {
            if (ally == me || !ally.is_visible() || !ally.is_alive() || !range.is_set(ally.position())) continue;
            const float missing = ally.max_health() - ally.health();
            const float score = std::min(missing, a.heal_amount()) * (ally.health() < ally.max_health() * .45f ? 2 : 1);
            if (missing >= 80 && score > best) { best = score; patient = ally; }
        }
        if (patient && a.use(*patient)) return true;
    }
    return false;
}

void Bot::farm_power() {
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
    if (counts[item_type::jungle_emblem_of_strength] || counts[item_type::jungle_emblem_of_focus]
        || counts[item_type::jungle_emblem_of_health]) incoming_multiplier *= .7f;
    if (counts[item_type::durability_emblem_of_strength] || counts[item_type::durability_emblem_of_focus]
        || counts[item_type::durability_emblem_of_health]) incoming_multiplier *= .9f;
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
    farm_power();
    const auto health_reserve = me.health() - std::max(160.f, me.max_health() * .3f);
    const auto enemy_spawn = map::spawn_region(team::enemy).positions().front();
    const auto our_score = global_submitted_gems(team::ally), enemy_score = global_submitted_gems(team::enemy);
    const bool endgame = our_score >= constants::winning_gems * .8f || enemy_score >= constants::winning_gems * .8f
        || round >= constants::max_rounds * .875f;
    const float remaining = static_cast<float>(constants::max_rounds > round ? constants::max_rounds - round : 0);
    float deadline = remaining;
    if (enemy_score >= constants::winning_gems * .8f && enemy_gem_rate > .1f)
        deadline = std::min(deadline, (constants::winning_gems - enemy_score) / enemy_gem_rate + 8);
    distance_field travel;
    bitboard visited;
    travel.compute(terrain, around(me.position(), 0), visited);
    float best = -1;
    int choice = -1;
    for (int pass = 0; pass < (endgame && !monolith_map ? 2 : 1) && choice < 0; ++pass)
    for (int i = 0; i < static_cast<int>(groups.size()); ++i) {
        if (fuel_remaining() < 33000) break;
        const auto& g = groups[i];
        if (g.avoid_until > round) continue;
        if (g.monolith && monolith_map) continue; // The team planner owns this objective.
        if (endgame && !monolith_map && ((pass == 0) != (g.camp.gem_value() > 0))) continue;
        bool exposed = false;
        for (const auto& enemy : enemies)
            if (dist(enemy.position, g.centre) <= enemy.reach + 2) exposed = true;
        if (exposed && !favorable(g.centre)) continue;
        int distance = distance_field::unreachable;
        for (const auto& c : g.camp) distance = std::min(distance, int(travel.get(c.spawn_position())));
        if (distance == distance_field::unreachable) continue;
        int wait = g.state == 2 ? std::max(0, int(g.ready_round) - int(round) - distance) : 0;
        if (wait > 12) continue;
        int assigned = 0, nearby_helpers = 0;
        if (i < 254)
            for (int j = 0; j < static_cast<int>(allies.size()) && j < 6; ++j)
                if (j != slot && claims[j] == i + 1) {
                    ++assigned;
                    const auto& ally = allies[j];
                    if (ally.is_visible() && ally.is_alive() && ally.health() > ally.max_health() * .5f
                        && dist(ally.position(), g.centre) <= 7) ++nearby_helpers;
                }
        // Compare help on a live camp with solo work in the same pass. Otherwise
        // a harmless gold cluster can keep a weak farmer from ever helping to
        // clear the gem camp that a teammate has already started.
        if (assigned && g.state != 0) continue;
        const float damage = g.state == 1 ? 0 : expected_damage(g) / ((nearby_helpers + 1) * (nearby_helpers + 1));
        if (damage > health_reserve) continue;
        float work = g.state == 1 ? 0 : g.health / std::max(1.f, farm_dps);
        if (me.champion_name() == champion_type::varg) work /= std::min(3, std::max(1, g.members));
        const float bank_trip = altar_distance.get(g.centre) == distance_field::unreachable ? 100.f : altar_distance.get(g.centre);
        if (g.camp.gem_value() && altar_distance.get(g.centre) == distance_field::unreachable) continue;
        const float delivery = distance + wait + work / (assigned + 1) + constants::capture_time + 1
            + bank_trip + tribute_ticks(g.camp.gem_value() / (assigned + 1));
        if (g.camp.gem_value() && delivery >= remaining) continue;
        const float value = g.camp.gem_value() * (endgame ? 1.6f : 1.f)
            + g.camp.gold_value() * (monolith_map ? .65f : endgame ? .03f : round < 500 ? .3f : .12f);
        float score = value / (distance + wait + work / (assigned + 1) + 6 + bank_trip * .35f);
        score /= assigned + 1; // Capturing together splits the reward.
        if (endgame && g.camp.gem_value() && delivery > deadline) score *= .2f;
        if (dist(g.centre, enemy_spawn) + 4 < home_distance.get(g.centre)) score *= contested ? .3f : .6f;
        if (round < respawn_round + 30 && home_distance.get(g.centre) > 16) score *= .35f;
        if (i == target) score *= 1.3f;
        if (score > best) { best = score; choice = i; }
    }
    return choice;
}

void Bot::refresh_threats() {
    threats.clear();
    visible_enemies.clear();
    friends.clear();
    enemies.clear();
    for (const auto& ally : allies) {
        if (!ally.is_visible() || !ally.is_alive()) continue;
        if (ally != self() && (ally.is_recalling() || ally.is_submitting_gems() || ally.is_teleporting())) continue;
        friends.push_back(inspect(ally));
    }
    for (std::size_t i = 0; i < enemy_roster.size(); ++i) {
        const auto& enemy = enemy_roster[i];
        if (!enemy.is_visible()) {
            if (enemy_memory[i].seen && round - enemy_memory[i].seen <= 3) threats.push_back(enemy_memory[i]);
            continue;
        }
        if (!enemy.is_alive()) { enemy_memory[i].seen = 0; continue; }
        visible_enemies.push_back(enemy);
        auto fighter = inspect(enemy);
        enemy_memory[i] = {fighter.position, fighter.burst / 2, fighter.reach, -1, true, round};
        threats.push_back(enemy_memory[i]);
        enemies.push_back(std::move(fighter));
    }
    const auto visible = vision::visible_tiles();
    for (int i = 0; i < static_cast<int>(groups.size()); ++i) {
        const auto& g = groups[i];
        if (!g.visible && (g.tiles & visible).is_empty()) continue;
        for (const auto& c : g.camp)
            if (camp_damage(c.kind()) > 0 && c.is_visible() && c.health() > 0 && c.is_awake())
                threats.push_back({c.position(), c.strength(), c.attack_range(), i, false, round});
    }
}

float Bot::danger(vec2 tile, bool enemies_only) const {
    float value = 0;
    for (const auto& t : threats)
        if ((!enemies_only || t.enemy) && dist(tile, t.position) <= t.range) value += t.damage;
    return value;
}

bool Bot::navigate(bitboard goals, bool escape, bool use_dash) {
    action = "navigate";
    if (fuel_remaining() < 16000) return false;
    auto& me = self();
    const auto start = me.position();
    auto units = occupied();
    auto blocked = terrain | units;
    blocked.set(start, false);
    goals &= ~blocked;
    if (goals.is_empty()) return false;
    if (goals.is_set(start)) return false;

    bitboard avoid;
    for (const auto& threat : threats)
        if (threat.enemy || escape || threat.group != target)
            avoid |= around(threat.position, threat.range);
    const auto safe_goals = goals & ~avoid;
    distance_field field;
    bitboard visited;
    bool planned = false;
    if (!safe_goals.is_empty()) {
        auto safe_walls = blocked | avoid;
        safe_walls.set(start, false);
        field.compute(safe_walls, safe_goals, visited);
        planned = field.get(start) != distance_field::unreachable;
        if (!planned) {
            // Starting inside danger must still permit an escape. Route to the
            // safe component that connects to the destination, then continue
            // around danger on subsequent turns.
            auto exits = visited & ~blocked & ~avoid;
            if (!exits.is_empty()) {
                field.compute(blocked, exits, visited);
                planned = field.get(start) != distance_field::unreachable;
            }
        }
    } else if (escape && danger(start) > 0) {
        auto exits = around(start, 8) & ~blocked & ~avoid;
        if (!exits.is_empty()) {
            field.compute(blocked, exits, visited);
            planned = field.get(start) != distance_field::unreachable;
        }
    }
    if (!planned) field.compute(blocked, goals, visited);
    const auto anchor = goals.positions().front();
    const int distance = field.get(start);
    if (anchor != nav_anchor || distance < best_nav_distance) {
        nav_anchor = anchor;
        best_nav_distance = distance;
        last_nav_progress = round;
    }
    auto score = [&](vec2 p) {
        return float(field.get(p)) * 10 + danger(p) * .02f;
    };
    auto origin = start;
    if (use_dash) for (const auto& ability : me.abilities()) {
        if (!ability.is_dash() || !ability.is_ready()) continue;
        auto dash_walls = map::walls() | map::altars() | map::spawn_region(team::enemy) | units;
        auto candidates = dash_walls.reachable_tiles(origin, static_cast<int>(ability.get<ability_dash>().range)) & ~blocked;
        auto best = origin;
        float value = score(origin) - 15;
        for (auto p : candidates.positions()) {
            if (field.get(p) >= field.get(origin)) continue;
            if (escape && danger(p) > danger(origin) && avoid.is_set(p)) continue;
            if (score(p) < value) { value = score(p); best = p; }
        }
        action = "navigate dash";
        if (best != origin && ability.use(best)) {
            origin = me.position();
            units = occupied();
            blocked = terrain | units;
            blocked.set(origin, false);
            refresh_threats();
        }
    }
    if (me.can_move()) {
        auto candidates = blocked.reachable_tiles(origin, me.base_stats().base_move_speed).positions();
        std::sort(candidates.begin(), candidates.end(), [&](vec2 a, vec2 b) { return score(a) < score(b); });
        for (auto p : candidates) {
            if (p == origin || field.get(p) >= field.get(origin)) continue;
            if (occupied().is_set(p)) continue;
            action = "navigate walk";
            if (me.move_absolute(p)) { walked = true; return true; }
        }
        // Congestion recovery also applies to banking and retreat. A lateral
        // step is allowed after prolonged lack of progress, with risk bounded.
        if (stalled >= 4 || round > last_nav_progress + 12) {
            for (auto p : candidates) {
                if (p == origin || danger(p) > danger(origin) || occupied().is_set(p)) continue;
                if (field.get(p) == distance_field::unreachable) continue;
                action = "navigate unstick";
                if (me.move_absolute(p)) { walked = true; last_nav_progress = round; return true; }
            }
        }
    }
    if (me.consumables()[consumable_type::tp_crystal].count() && danger(origin) == 0
        && !me.restrictions().contains(buff_restrictions::consumable)) {
        auto landings = around(origin, 3) & ~blocked;
        auto best = origin;
        float value = float(field.get(origin)) - 5;
        for (auto p : landings.positions())
            if (field.get(p) < value && danger(p) == 0) { value = field.get(p); best = p; }
        action = "navigate crystal";
        if (best != origin && me.consumables()[consumable_type::tp_crystal].use(best)) return true;
    }
    return me.position() != start;
}

bool Bot::fight(const unit& victim, bool enemy) {
    action = "fight";
    if (fuel_remaining() < 16000) return false;
    auto& me = self();
    if (!victim.is_visible() || victim.health() <= 0) return false;
    const auto position = victim.position();
    const float hp = victim.health();
    bool acted = false;
    // Shield before spending the shared cast on an attack reset when tanking a
    // large camp, or when a fight already threatens our health reserve.
    if ((!enemy && victim.strength() >= 60 && dist(me.position(), position) <= victim.attack_range())
        || (danger(me.position()) > 0 && me.health() < me.max_health() * .55f)) {
        for (const auto& a : me.abilities())
            if (a.is_shield() && a.is_ready()) { acted = a.use(); break; }
    }
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
            if (enemy) {
                for (const auto& c : visible_enemies)
                    if (c.is_visible() && c.is_alive() && c.position() != position && dist(c.position(), position) <= radius)
                        value += a.damage_amount();
            } else {
                for (const auto& c : vision::camps())
                    if (c.position() != position && dist(c.position(), position) <= radius) value += a.damage_amount();
            }
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
        if (!favorable(c.position(), me.gem_count() > 0)) continue;
        // Fight nearby threats and secure exposed carriers, without chasing.
        float value = 2000.f / (c.health() + 100) + c.gem_count() * .05f - d * .1f;
        if (value > score) { score = value; victim = c; }
    }
    if (!victim) return false;
    if (me.health() < me.max_health() * .35f && victim->health() > me.strength() * 2) return false;
    return fight(*victim, true);
}

void Bot::evade() {
    action = "evade";
    auto& me = self();
    if (target >= 0) groups[target].avoid_until = round + 35;
    claim(-1);
    auto goals = map::spawn_region(team::ally);
    float nearest = home_distance.get(me.position());
    for (const auto& ally : friends) {
        if (ally.champion == me || ally.health < ally.max_health * .6f) continue;
        if (danger(ally.position, true) > 0) continue;
        const int distance = dist(me.position(), ally.position);
        if (distance > 2 && distance + 3 < nearest) {
            nearest = distance + 3;
            goals = around(ally.position, 1);
        }
    }
    for (const auto& a : me.abilities())
        if (a.is_shield() && a.is_ready() && danger(me.position()) > 0) { a.use(); break; }
    navigate(goals, true);
    if (me.can_attack()) {
        for (const auto& enemy : visible_enemies) {
            if (!enemy.is_visible() || !enemy.is_alive() || enemy.health() > me.strength()) continue;
            if (dist(me.position(), enemy.position()) <= me.attack_range()) { me.attack(enemy); break; }
        }
    }
}

void Bot::recover() {
    action = "recover";
    auto& me = self();
    claim(-1);
    const int home = home_distance.get(me.position());
    bool can_recall = danger(me.position()) == 0;
    for (const auto& threat : threats)
        if (threat.enemy && dist(threat.position, me.position()) <= threat.range + constants::recall_time)
            can_recall = false;
    if (can_recall && home > constants::recall_time + 1) {
        me.recall();
        return;
    }
    navigate(map::spawn_region(team::ally), true);
    // Escape movement has priority over spending a turn on optional combat.
}

bool Bot::bank() {
    action = "bank";
    auto& me = self();
    if (!me.gem_count()) { bank_altar = -1; return false; }
    claim(-1);
    if (altars.empty()) return false;
    if (bank_altar >= 0 && (stalled >= 5 || round > last_nav_progress + 24)) {
        std::cout << "bank replan r=" << round << " altar=" << bank_altar << " gems=" << me.gem_count() << '\n';
        altars[bank_altar].avoid_until = round + 24;
        bank_altar = -1;
        stalled = 0;
    }
    if (bank_altar < 0) {
        float best = std::numeric_limits<float>::max();
        for (int i = 0; i < static_cast<int>(altars.size()); ++i) {
            const auto& altar = altars[i];
            const auto distance = altar.distance.get(me.position());
            if (distance == distance_field::unreachable) continue;
            float risk = std::numeric_limits<float>::max();
            for (auto p : (around(altar.position, 1) & ~terrain).positions()) risk = std::min(risk, danger(p));
            const float score = distance + risk * .4f + (altar.avoid_until > round ? 80 : 0);
            if (score < best) { best = score; bank_altar = i; }
        }
        last_nav_progress = round;
        best_nav_distance = distance_field::unreachable;
        nav_anchor = {-1, -1};
    }
    if (bank_altar < 0) { recover(); return true; }
    const auto altar = altars[bank_altar].position;
    const auto position = me.position();
    if (dist(position, altar) <= constants::submit_gems_range) {
        if (vision::has_altar_lock(altar) && vision::altar_lock_at(altar).is_enemy()) {
            if (me.can_attack()) me.attack(vision::altar_lock_at(altar));
            return true;
        }
        const int duration = tribute_ticks(me.gem_count());
        const float enemy_risk = danger(position, true);
        const float camp_risk = danger(position) - enemy_risk;
        const bool wins = global_submitted_gems(team::ally) + me.gem_count() >= constants::winning_gems;
        const float exposure = enemy_risk * std::min(duration + 1, 3) + camp_risk * (duration + 1);
        if (exposure < me.health() * (wins ? .9f : .7f)
            && (enemy_risk == 0 || favorable(position, true))) {
            action = "tribute";
            me.submit_gems(altar);
            stalled = 0;
            return true;
        }
    }
    auto goals = around(altar, constants::submit_gems_range) & ~terrain;
    // Refusing tribute cannot leave our current unsafe tile as a completed goal.
    goals.set(position, false);
    if (goals.is_empty()) { evade(); return true; }
    navigate(goals, true);
    return true;
}

bool Bot::team_objective() {
    action = "team objective";
    if (!monolith_map || round < 150 || round < objective_backoff || fuel_remaining() < 35000) return false;
    auto& me = self();
    if (me.health() < me.max_health() * .65f) {
        if (rally_group >= 0 && dist(me.position(), groups[rally_group].centre) <= 6
            && groups[rally_group].state == 0) {
            const auto centre = groups[rally_group].centre;
            navigate(around(centre, 4) & ~around(centre, 3) & ~terrain, true);
            return true;
        }
        return false;
    }
    const unsigned age = static_cast<std::uint8_t>(static_cast<std::uint8_t>(round) - claims[7]);
    int index = claims[6] ? claims[6] - 1 : -1;
    if (age > 40 || index >= static_cast<int>(groups.size()) || (index >= 0 && !groups[index].monolith)) index = -1;
    if (index < 0) {
        float best = std::numeric_limits<float>::max();
        for (int i = 0; i < static_cast<int>(groups.size()) && i < 254; ++i) {
            const auto& g = groups[i];
            if (!g.monolith || g.avoid_until > round || (g.state == 2 && g.ready_round > round + 20)) continue;
            const auto distance = home_distance.get(g.centre);
            if (distance == distance_field::unreachable) continue;
            const float cost = distance + altar_distance.get(g.centre) * .25f;
            if (cost < best) { best = cost; index = i; }
        }
        if (index < 0) return false;
        shared_memory[6] = static_cast<std::uint8_t>(index + 1);
        std::cout << "objective rally r=" << round << " group=" << index << '\n';
    }
    shared_memory[7] = static_cast<std::uint8_t>(round);
    auto& group = groups[index];
    if (group.state == 2 && group.ready_round > round + 8) {
        shared_memory[6] = 0;
        rally_group = -1;
        objective_backoff = round + 20;
        if (target == index) claim(-1);
        return false;
    }
    if (rally_group != index) { rally_group = index; rally_since = 0; }
    const auto centre = group.centre;
    if (group.state == 1) {
        unsigned capturer = id(me);
        std::optional<unsigned> occupant;
        for (const auto& ally : friends)
            if (dist(ally.position, centre) <= 6 && ally.health > 180) {
                capturer = std::min(capturer, id(ally.champion));
                if (group.tiles.is_set(ally.position))
                    occupant = std::min(occupant.value_or(id(ally.champion)), id(ally.champion));
            }
        if (occupant) capturer = *occupant;
        if (id(me) == capturer) { claim(index); farm(); return true; }
        if (target == index) claim(-1);
        return false;
    }
    claim(index);
    auto staging = around(centre, 4) & ~around(centre, 3) & ~terrain;
    if (dist(me.position(), centre) > 6) {
        navigate(staging, true);
        return true;
    }
    if (!rally_since) rally_since = round;
    farm_power();
    int ready = 0;
    float damage = 0, healing = 0, shielding = 0, pool = 0, mitigation = 0;
    for (const auto& ally : friends) {
        if (dist(ally.position, centre) > 6 || ally.health < ally.max_health * .65f) continue;
        bool committed = ally.champion == me;
        for (int j = 0; j < static_cast<int>(allies.size()) && j < 6; ++j)
            if (allies[j] == ally.champion && claims[j] == index + 1) committed = true;
        if (!committed) continue;
        ++ready;
        const bool healer = ally.champion.champion_name() == champion_type::willow;
        damage += healer ? 0 : ally.dps;
        healing += ally.healing;
        shielding += ally.shielding;
        pool += std::max(0.f, ally.health - std::max(180.f, ally.max_health * .3f));
        const auto items = ally.champion.item_count();
        float reduction = 1;
        if (items[item_type::jungle_emblem_of_strength] || items[item_type::jungle_emblem_of_focus]
            || items[item_type::jungle_emblem_of_health]) reduction *= .7f;
        if (items[item_type::durability_emblem_of_strength] || items[item_type::durability_emblem_of_focus]
            || items[item_type::durability_emblem_of_health]) reduction *= .9f;
        mitigation += reduction;
    }
    bool active = false;
    for (const auto& camp : group.camp)
        if (camp.is_visible() && camp.health() > 0 && camp.is_awake()) active = true;
    const float turns = group.health / std::max(1.f, damage) + 4;
    const float net_incoming = std::max(20.f, group.damage * mitigation / std::max(1, ready) - healing - shielding);
    const int required = std::max(2, static_cast<int>(allies.size()) - 1);
    const bool engage = (ready >= required && turns * net_incoming < pool * .85f)
        || (active && ready >= 2 && turns * net_incoming < pool);
    if (!engage) {
        if (round > rally_since + 24) {
            std::cout << "objective regroup r=" << round << " ready=" << ready
                << " incoming=" << turns * net_incoming << " reserve=" << pool << '\n';
            shared_memory[6] = 0;
            objective_backoff = round + 45;
            rally_group = -1;
            group.avoid_until = round + 45;
            claim(-1);
            return false;
        }
        // Wait outside the monster's attack range; the healer can restore tanks.
        navigate(staging, true);
        return true;
    }
    rally_since = round;
    if (me.champion_name() == champion_type::willow) {
        navigate(staging, false);
        return true;
    }
    if (danger(me.position()) - danger(me.position(), true) > 0 && me.health() < me.max_health() * .58f) {
        // Leave range before the next camp phase so another healthy ally tanks.
        navigate(staging, true);
        return true;
    }
    farm();
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
        if (g.tiles.is_set(me.position())) { stalled = 0; return; } // Hold through all capture phases.
        navigate(g.tiles);
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
            navigate(g.tiles);
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
    round = round_number();
    if (!initialized) initialize();
    auto& me = self();
    walked = false;
    if (!me.is_alive()) {
        buy_items();
        claim(-1);
        returning = false;
        was_alive = false;
        bank_altar = rally_group = -1;
        previous = {-1, -1};
        return;
    }
    if (!was_alive) {
        was_alive = true;
        respawn_round = round;
        objective_backoff = round + 25;
        stalled = 0;
    }
    // Preserve channels once started. Their safety is checked before starting.
    if (me.is_recalling() || me.is_submitting_gems() || me.is_teleporting()) return;
    buy_items();
    if (!me.can_move() && !me.can_attack() && !me.can_cast()) return;
    observe();
    refresh_threats();
    if (fuel_remaining() < 18000) return;
    const auto enemy_score = global_submitted_gems(team::enemy);
    if (round >= score_sample_round + 24) {
        const float rate = float(enemy_score - score_sample_value) / std::max(1u, round - score_sample_round);
        enemy_gem_rate = enemy_gem_rate == 0 ? rate : enemy_gem_rate * .65f + rate * .35f;
        score_sample_round = round;
        score_sample_value = enemy_score;
    }
    const auto position = me.position();
    stalled = position == previous ? stalled + 1 : 0;
    previous = position;
    const bool home = map::spawn_region(team::ally).is_set(position);
    if (home) {
        returning = false;
        if (me.health() < me.max_health() * .98f) return;
    }
    const bool carrier = me.gem_count() > 0;
    if (!carrier) bank_altar = -1;
    const float enemy_damage = danger(position, true);
    if (!home && under_pressure()
        && (!favorable(position, carrier) || me.health() < enemy_damage * 2 + me.max_health() * .2f)) {
        if (me.health() < me.max_health() * .48f) returning = true;
        evade();
        return;
    }
    support();
    const float reserve = std::max(180.f, me.max_health() * (carrier ? .3f : .43f));
    const bool deadline_race = enemy_score >= constants::winning_gems * .8f
        || global_submitted_gems(team::ally) >= constants::winning_gems * .8f;
    if (!home && (me.health() < reserve
        || (me.champion_name() != champion_type::tavi && me.gold_count() >= (monolith_map ? 120u : 180u)
            && round > last_shop_round + 40 && !carrier && (!deadline_race || monolith_map)))) returning = true;
    if (returning) { recover(); return; }
    // Deliver every captured bag before taking an optional fight or new farm.
    if (carrier) { bank(); return; }
    if (stalled > 10 && target >= 0 && groups[target].state != 1
        && !(monolith_map && rally_group == target)) {
        groups[target].avoid_until = round + 35;
        claim(-1);
        stalled = 0;
    }
    if (defend()) return;
    if (team_objective()) return;
    if (monolith_map && target >= 0 && groups[target].monolith) claim(-1);
    farm();
}
