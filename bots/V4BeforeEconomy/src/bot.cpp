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
    // Spread static work over startup turns. In particular, never compute one
    // full distance field per altar (18 on the long supplied map).
    if (initialization_stage == 1) {
        bitboard visited;
        home_distance.compute(terrain, map::spawn_region(team::ally), visited);
        home_values = home_distance.export_linear_buffer();
        initialization_stage = 2;
        return;
    }
    if (initialization_stage == 2) {
        bitboard visited, goals;
        for (const auto& altar : altars) goals |= around(altar.position, constants::submit_gems_range);
        altar_distance.compute(terrain, goals & ~terrain, visited);
        altar_values = altar_distance.export_linear_buffer();
        initialized = true;
        return;
    }
    width = map::width();
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
        entry.positions = tiles.positions();
        entry.full_health = entry.health;
        entry.full_damage = entry.damage;
        entry.gems = g.gem_value();
        entry.gold = g.gold_value();
        int x = 0, y = 0;
        for (const auto& c : g) { x += c.spawn_position().x; y += c.spawn_position().y; }
        entry.centre = {x / entry.members, y / entry.members};
        for (const auto& c : g) {
            entry.radius = std::max(entry.radius, dist(c.spawn_position(), entry.centre));
            int hits = 0;
            for (const auto& other : g) hits += dist(c.spawn_position(), other.spawn_position()) <= 1;
            entry.splash_targets = std::max(entry.splash_targets, hits);
        }
        entry.major = entry.gems && (entry.monolith || entry.full_health >= 10000);
        has_monolith |= entry.monolith;
        ordinary_gems |= g.gem_value() > 0 && !entry.monolith;
        groups.push_back(std::move(entry));
    }
    monolith_map = has_monolith && !ordinary_gems;
    objective_map = std::any_of(groups.begin(), groups.end(), [](const Group& g) { return g.major; })
        && std::none_of(groups.begin(), groups.end(), [](const Group& g) { return g.gems && !g.major; });
    const auto type = me.champion_name();
    caster_build = type == champion_type::cassi || type == champion_type::stellar
        || type == champion_type::ren || type == champion_type::prism || type == champion_type::willow
        || (type == champion_type::tavi && objective_map);
    const auto home = map::spawn_region(team::ally).positions().front();
    const auto away = map::spawn_region(team::enemy).positions().front();
    contested = std::max(map::width(), map::height()) <= 65 || dist(home, away) <= 42;
    enemy_memory.resize(enemy_roster.size());
    for (auto p : map::altars().positions()) altars.push_back(Altar{p, 0, (around(p, 1) & ~terrain).positions()});
    me.set_priority(100 - slot);
    initialization_stage = 1;
}

void Bot::claim(int index) {
    target = index;
    // Zero means unassigned. Groups beyond byte range still work without claims.
    if (slot < 6) {
        const int limit = objective_map ? 126 : 254;
        auto value = static_cast<std::uint8_t>(index >= 0 && index < limit ? index + 1 : 0);
        if (objective_map && objective_ready) value |= 128;
        shared_memory[slot] = value;
        claims[slot] = value;
    }
}

unsigned Bot::assignment(int index) const {
    return objective_map ? claims[index] & 127 : claims[index];
}

void Bot::update_readiness() {
    if (!objective_map) return;
    refresh_farmers();
    objective_ready = false;
    for (const auto& f : farmers) if (f.slot == slot && f.health >= f.max_health * .7f && !returning && !f.gems) {
        // Advertise useful current damage, not ownership of an arbitrary item.
        for (const auto& g : groups) if (g.major && clear_rate(f, g) >= (g.monolith ? 110.f : 220.f))
            objective_ready = true;
    }
    claim(target);
}

void Bot::refresh_farmers() {
    if (farmers_round == round) return;
    farmers_round = round;
    farmers.clear();
    for (int j = 0; j < static_cast<int>(allies.size()); ++j) {
        const auto& a = allies[j];
        if (!a.is_visible() || !a.is_alive() || a.is_recalling() || a.is_submitting_gems() || a.is_teleporting()) continue;
        float mitigation = 1;
        const auto counts = a.item_count();
        if (counts[item_type::jungle_emblem_of_strength] || counts[item_type::jungle_emblem_of_focus]
            || counts[item_type::jungle_emblem_of_health]) mitigation *= .7f;
        if (counts[item_type::durability_emblem_of_strength] || counts[item_type::durability_emblem_of_focus]
            || counts[item_type::durability_emblem_of_health]) mitigation *= .9f;
        farmers.push_back({j, a.position(), a.champion_name(), a.health(), a.max_health(), a.strength(), a.focus(),
            mitigation, a.attack_range(), a.gem_count()});
    }
}

float Bot::clear_rate(const Farmer& f, const Group& g) const {
    const float hits = std::min(g.splash_targets, std::max(1, g.members));
    switch (f.type) {
        case champion_type::varg: return f.strength * 1.125f * hits;
        case champion_type::ryth: return f.strength * 1.125f + f.focus * hits / 8;
        case champion_type::tavi: return f.strength * 1.125f + f.focus * 2.2f / 8;
        case champion_type::ren: return f.strength + f.focus * 1.25f / 8
            + f.focus * .2f * std::min(g.members, static_cast<int>(g.damage / 20));
        case champion_type::cassi: case champion_type::prism: return f.strength + f.focus * 2 / 8;
        case champion_type::stellar: return f.strength + f.focus * std::max(2.f, 1.4f * hits) / 8;
        default: return f.strength * 1.125f;
    }
}

int Bot::capture_recipient(int index) {
    refresh_farmers();
    const auto& g = groups[index];
    int best = slot;
    float best_score = 1e9f;
    for (const auto& f : farmers) {
        if (f.gems || f.health < 120 || dist(f.position, g.centre) > g.radius + 6) continue;
        const bool occupant = g.tiles.is_set(f.position);
        if (!occupant && f.slot != slot && assignment(f.slot) != static_cast<unsigned>(index + 1)) continue;
        // Preserve a capture already in progress. Otherwise prefer the nearest
        // useful farmer, with stable slot order breaking exact ties.
        const float score = (occupant ? -1000.f : dist(f.position, g.centre) * 8.f)
            + (f.range > 1 ? 2.f : 0.f) + f.strength * .01f + f.focus * .005f + f.slot * .001f;
        if (score < best_score) { best_score = score; best = f.slot; }
    }
    return best;
}

bool Bot::capture_group(int index) {
    auto& g = groups[index];
    const int recipient = capture_recipient(index);
    if (recipient == slot) {
        claim(index);
        if (!g.tiles.is_set(self().position())) navigate(g.tiles);
        else stalled = 0;
        return true;
    }
    // Helpers must leave the reward region; then they may immediately choose
    // the next job. Reward shares never require every helper to bank.
    g.avoid_until = round + 12;
    claim(-1);
    if (g.tiles.is_set(self().position())) {
        navigate(around(self().position(), 2) & ~g.tiles & ~terrain);
        return true;
    }
    return false;
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
    const bool can_heal = home || !me.is_alive();
    auto counts = me.item_count();
    while (me.gold_count() >= 30 && fuel_remaining() > 22000) {
        const auto power = caster_build ? item_type::power_emblem_of_focus : item_type::power_emblem_of_strength;
        const auto jungle = caster_build ? item_type::jungle_emblem_of_focus : item_type::jungle_emblem_of_strength;
        item_type item = caster_build ? item_type::power_shard_of_focus : item_type::power_shard_of_strength;
        if (counts[power] && !counts[jungle] && (me.attack_range() == 1 || objective_map))
            item = caster_build ? item_type::jungle_shard_of_focus : item_type::jungle_shard_of_strength;
        else if (counts[power] && can_heal && !counts[item_type::durability_emblem_of_health]
            && (contested || objective_map)) item = item_type::durability_shard_of_health;
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
        our_damage += (c.dps + c.burst * .15f + c.healing * .5f) * weight;
        ++our_count;
    }
    for (const auto& c : enemies) {
        if (dist(c.position, point) > c.reach + 1) continue;
        const float weight = dist(c.position, point) <= 3 ? 1.f : .5f;
        their_health += c.health * weight;
        their_damage += (c.dps + c.burst * .15f) * weight;
        ++their_count;
    }
    if (!their_count) return true;
    if (their_count > our_count + 1) return false;
    return our_health * our_damage > their_health * their_damage * (carrier ? 1.3f : 1.05f);
}

bool Bot::under_pressure() const {
    return danger(self().position(), true) > 0;
}

bool Bot::support() {
    action = "support";
    if (fuel_remaining() < 16000 || round_number() != round) return false;
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
    if (farm_power_round == round) return;
    farm_power_round = round;
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
    action = "select camp";
    refresh_farmers();
    auto mine = std::find_if(farmers.begin(), farmers.end(), [&](const Farmer& f) { return f.slot == slot; });
    if (mine == farmers.end() || fuel_remaining() < 40000) return -1;
    const auto& me = *mine;
    const auto enemy_spawn = map::spawn_region(team::enemy).positions().front();
    distance_field travel;
    bitboard visited;
    travel.compute(terrain, around(me.position, 0), visited);
    const auto distances = travel.export_linear_buffer();
    float best = -1;
    int choice = -1;
    const bool closing = global_submitted_gems(team::enemy) >= 800 || global_submitted_gems(team::ally) >= 800;
    for (int i = 0; i < static_cast<int>(groups.size()); ++i) {
        if (fuel_remaining() < 42000) break;
        const auto& g = groups[i];
        if (g.avoid_until > round || (objective_map && g.major)) continue;
        int distance = distance_field::unreachable;
        for (auto p : g.positions) distance = std::min(distance, int(distances[p.y * width + p.x]));
        if (distance == distance_field::unreachable) continue;
        const int wait = g.state == 2 ? std::max(0, int(g.ready_round) - int(round) - distance) : 0;
        if (wait > 8) continue;
        int helpers = 0, claims_count = 0;
        float rate = clear_rate(me, g), pool = std::max(0.f, me.health - std::max(140.f, me.max_health * .24f));
        float shield = me.type == champion_type::varg ? me.focus * 2.5f / 8 : 0;
        float mitigation = me.mitigation;
        for (int j = 0; j < static_cast<int>(allies.size()) && j < 6; ++j)
            if (j != slot && assignment(j) == static_cast<unsigned>(i + 1)) ++claims_count;
        if (g.state == 1 && claims_count && capture_recipient(i) != slot) continue;
        for (const auto& f : farmers) {
            if (f.slot == slot || assignment(f.slot) != static_cast<unsigned>(i + 1) || f.gems
                || f.health < f.max_health * .3f || dist(f.position, g.centre) > g.radius + 8
                || dist(f.position, g.centre) > distance + g.radius + 5) continue;
            ++helpers;
            rate += clear_rate(f, g);
            pool += std::max(0.f, f.health - std::max(140.f, f.max_health * .24f));
            mitigation = std::min(mitigation, f.mitigation);
            if (f.type == champion_type::varg) shield += f.focus * 2.5f / 8;
        }
        // Avoid draining four champions into a job that two can finish. Cheap
        // unclaimed gold camps remain useful opening work for distant allies.
        if (g.state != 1 && claims_count >= (g.full_health >= 4000 ? 3 : 2)) continue;
        const float work = g.state == 1 ? 0 : g.health / std::max(1.f, rate);
        const float incoming = std::max(0.f, g.damage * mitigation * (g.members > 1 ? .6f : 1.f) - shield);
        if (g.state != 1 && incoming * (work + 2) > pool) continue;
        bool unsafe = false;
        for (const auto& e : enemies) if (dist(e.position, g.centre) <= g.radius + 4 && !favorable(g.centre)) unsafe = true;
        if (unsafe) continue;
        const auto bank = altar_steps(g.centre);
        if (g.gems && (bank == distance_field::unreachable || round + distance + work + bank + 8 >= constants::max_rounds)) continue;
        const float gold_weight = objective_map ? .8f : closing ? .06f : .28f;
        const float value = g.gems + g.gold * gold_weight;
        const float duration = distance + wait + work + 6 + (g.gems ? bank * .3f : 0);
        // Help is valued by the team's throughput; capture ownership is elected
        // separately. Do not divide every helper's value by the reward split.
        float score = value / std::max(1.f, duration) / (1 + helpers * .35f);
        if (g.state == 1) score *= 1.3f;
        if (distance > 35 && helpers == 0) score *= .7f;
        if (dist(g.centre, enemy_spawn) + 4 < home_steps(g.centre)) score *= .5f;
        if (score > best) { best = score; choice = i; }
    }
    return choice;
}

void Bot::refresh_threats() {
    threats.clear();
    visible_enemies.clear();
    friends.clear();
    enemies.clear();
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
    const int objective = claims[6] ? claims[6] - 1 : -1;
    const bool near_objective = objective_map && objective >= 0 && objective < static_cast<int>(groups.size())
        && dist(self().position(), groups[objective].centre) <= 8;
    // Building ten detailed fighter models every empty farming turn consumed
    // action fuel. Model allies only when combat or a nearby rally needs them.
    if (!enemies.empty() || near_objective) for (const auto& ally : allies) {
        if (!ally.is_visible() || !ally.is_alive()) continue;
        if (ally != self() && (ally.is_recalling() || ally.is_submitting_gems() || ally.is_teleporting())) continue;
        friends.push_back(inspect(ally));
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
    if (round_number() != round || fuel_remaining() < 26000) return false;
    action = "navigate";
    auto& me = self();
    const auto start = me.position();
    action = "navigate occupancy";
    auto units = occupied();
    action = "navigate masks";
    auto blocked = terrain | units;
    blocked.set(start, false);
    goals &= ~blocked;
    if (goals.is_empty() || goals.is_set(start)) return false;
    action = "navigate goals";
    const auto anchor = goals.positions().front();
    const float starting_risk = danger(start);
    if (fuel_remaining() < 40000) {
        // A bounded emergency step is preferable to exhausting the turn while
        // constructing another map-wide field during an expensive team fight.
        if (!me.can_move()) return false;
        auto best = start;
        float value = dist(start, anchor) + (escape ? starting_risk * 2 : 0);
        for (auto p : blocked.reachable_tiles(start, me.base_stats().base_move_speed).positions()) {
            const float cost = dist(p, anchor) + (escape ? danger(p) * 2 : 0);
            if (cost < value) { value = cost; best = p; }
        }
        if (best != start && round_number() == round && fuel_remaining() >= 6000 && me.move_absolute(best)) {
            walked = true;
            return true;
        }
        return false;
    }
    action = "navigate avoidance";
    bitboard avoid;
    for (const auto& threat : threats)
        if (threat.enemy || escape || threat.group != target)
            avoid |= around(threat.position, threat.range);
    // One search per turn; failure schedules a less restrictive search next
    // turn. Chaining three full searches caused v3's navigation fuel spills.
    if (navigation_round == round || fuel_remaining() < 40000) return false;
    navigation_round = round;
    const auto safe_goals = goals & ~avoid;
    auto search_walls = blocked;
    auto search_goals = goals;
    if (!relax_route && !safe_goals.is_empty()) {
        search_walls |= avoid;
        search_walls.set(start, false);
        search_goals = safe_goals;
        // When already in danger, cross its boundary instead of demanding
        // that the whole immediate neighborhood be safe.
        if (avoid.is_set(start)) search_walls &= ~(around(start, 2) & ~blocked);
    }
    distance_field field;
    bitboard visited;
    action = "navigate search";
    field.compute_to(search_walls, search_goals, around(start, 0), visited);
    if (round_number() != round) return false;
    action = "navigate distances";
    const auto distances = field.export_linear_buffer();
    const auto field_distance = [&](vec2 p) { return int(distances[p.y * width + p.x]); };
    if (field_distance(start) == distance_field::unreachable) {
        relax_route = true;
        return false;
    }
    relax_route = false;
    if (round_number() != round || fuel_remaining() < 10000) return false;
    auto origin = start;
    int origin_distance = field_distance(origin);
    if (anchor != nav_anchor || origin_distance < best_nav_distance) {
        nav_anchor = anchor;
        best_nav_distance = origin_distance;
        last_nav_progress = round;
    }
    if (use_dash && fuel_remaining() > 28000) for (const auto& ability : me.abilities()) {
        if (!ability.is_dash() || !ability.is_ready()) continue;
        auto dash_walls = map::walls() | map::altars() | map::spawn_region(team::enemy) | units;
        const auto landings = dash_walls.reachable_tiles(origin, static_cast<int>(ability.get<ability_dash>().range)) & ~blocked;
        auto best = origin;
        float value = origin_distance * 10 + starting_risk * .02f - 15;
        for (auto p : landings.positions()) {
            const int distance = field_distance(p);
            if (distance >= origin_distance) continue;
            const float risk = danger(p);
            if (escape && risk > starting_risk && avoid.is_set(p)) continue;
            const float cost = distance * 10 + risk * .02f;
            if (cost < value) { value = cost; best = p; }
        }
        action = "navigate dash";
        if (round_number() != round || fuel_remaining() < 10000) return false;
        if (best != origin && ability.use(best)) {
            origin = me.position();
            origin_distance = field_distance(origin);
            units = occupied();
            blocked = terrain | units;
            blocked.set(origin, false);
        }
    }
    if (me.can_move()) {
        struct Step { vec2 position; int distance; float risk, cost; };
        std::vector<Step> steps;
        for (auto p : blocked.reachable_tiles(origin, me.base_stats().base_move_speed).positions()) {
            if (p == origin) continue;
            const int distance = field_distance(p);
            const float risk = danger(p);
            steps.push_back({p, distance, risk, distance * 10 + risk * .02f});
        }
        // Sorting must not make SDK calls: the old comparator repeatedly read
        // distance buffers and consumed the fuel reserved for the action.
        std::sort(steps.begin(), steps.end(), [](const Step& a, const Step& b) { return a.cost < b.cost; });
        for (const auto& step : steps) {
            if (step.distance >= origin_distance || units.is_set(step.position)) continue;
            action = "navigate walk";
            if (round_number() != round || fuel_remaining() < 7000) return false;
            if (me.move_absolute(step.position)) { walked = true; return true; }
            units = occupied(); // Only refresh after a hidden-occupant failure.
        }
        if (stalled >= 4 || oscillating || round > last_nav_progress + 12) {
            const float risk = danger(origin);
            for (const auto& step : steps) {
                if (step.risk > risk || step.distance == distance_field::unreachable || units.is_set(step.position)) continue;
                action = "navigate unstick";
                if (round_number() != round || fuel_remaining() < 7000) return false;
                if (me.move_absolute(step.position)) { walked = true; last_nav_progress = round; return true; }
                units = occupied();
            }
        }
    }
    if (fuel_remaining() > 18000 && me.consumables()[consumable_type::tp_crystal].count() && danger(origin) == 0
        && !me.restrictions().contains(buff_restrictions::consumable)) {
        auto landings = around(origin, 3) & ~blocked;
        auto best = origin;
        float value = float(field_distance(origin)) - 5;
        for (auto p : landings.positions()) {
            const int distance = field_distance(p);
            if (distance < value && danger(p) == 0) { value = distance; best = p; }
        }
        action = "navigate crystal";
        if (round_number() == round && best != origin && me.consumables()[consumable_type::tp_crystal].use(best)) return true;
    }
    return me.position() != start;
}

bool Bot::fight(const unit& victim, bool enemy) {
    action = "fight";
    if (fuel_remaining() < 22000 || round_number() != round) return false;
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
    objective_ready = false;
    if (me.gem_count() && bank_altar >= 0) {
        altars[bank_altar].avoid_until = round + 40;
        bank_altar = -1;
    }
    claim(-1);
    auto goals = map::spawn_region(team::ally);
    float nearest = home_steps(me.position());
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
    objective_ready = false;
    claim(-1);
    const int home = home_steps(me.position());
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
    if (bank_altar >= 0) {
        const int distance = std::max(0, dist(me.position(), altars[bank_altar].position) - 1);
        if (distance < bank_best_distance) {
            bank_best_distance = distance;
            bank_progress_round = round;
        }
    }
    if (bank_altar >= 0 && ((round > bank_progress_round + 10 && (stalled >= 5 || oscillating)) || round > bank_progress_round + 40)) {
        std::cout << "bank replan r=" << round << " altar=" << bank_altar << " gems=" << me.gem_count() << '\n';
        altars[bank_altar].avoid_until = round + 24;
        bank_altar = -1;
        stalled = 0;
    }
    if (bank_altar < 0) {
        float best = std::numeric_limits<float>::max();
        action = "bank choose altar";
        std::vector<std::pair<float, int>> candidates;
        const auto position = me.position();
        for (int i = 0; i < static_cast<int>(altars.size()); ++i)
            candidates.push_back({float(std::max(0, dist(altars[i].position, position) - 1)
                + (altars[i].avoid_until > round ? 80 : 0)), i});
        std::sort(candidates.begin(), candidates.end());
        for (const auto& [distance, i] : candidates) {
            if (distance >= best) break;
            float risk = std::numeric_limits<float>::max();
            for (auto p : altars[i].approaches) risk = std::min(risk, danger(p));
            const float score = distance + risk * .4f;
            if (score < best) { best = score; bank_altar = i; }
        }
        position_samples = 0;
        oscillating = false;
        stalled = 0;
        last_nav_progress = round;
        bank_progress_round = round;
        bank_best_distance = bank_altar >= 0 ? std::max(0, dist(me.position(), altars[bank_altar].position) - 1) : distance_field::unreachable;
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
    if (!objective_map || round < 150 || round < objective_backoff || fuel_remaining() < 40000) return false;
    if (target >= 0 && !groups[target].major && groups[target].state == 1) return false;
    refresh_farmers();
    auto& me = self();
    const unsigned age = static_cast<std::uint8_t>(static_cast<std::uint8_t>(round) - claims[7]);
    int index = claims[6] ? claims[6] - 1 : -1;
    if (age > 30 || index >= static_cast<int>(groups.size()) || (index >= 0 && !groups[index].major)) index = -1;
    if (index < 0) {
        int ready = 0;
        for (int j = 0; j < static_cast<int>(allies.size()) && j < 6; ++j) ready += (claims[j] & 128) != 0;
        if (!objective_ready || ready < std::max(2, static_cast<int>(allies.size()) - 2)) return false;
        int best = distance_field::unreachable;
        for (int i = 0; i < static_cast<int>(groups.size()) && i < 126; ++i) {
            const auto& g = groups[i];
            if (!g.major || g.avoid_until > round || (g.state == 2 && g.ready_round > round + 20)) continue;
            const auto distance = home_steps(g.centre);
            if (distance < best) { best = distance; index = i; }
        }
        if (index < 0) return false;
        shared_memory[6] = static_cast<std::uint8_t>(index + 1);
        std::cout << "objective rally r=" << round << " group=" << index << '\n';
    }
    auto& g = groups[index];
    if (g.state == 2 && g.ready_round > round + 8) {
        shared_memory[6] = 0;
        rally_group = -1;
        objective_backoff = round + 20;
        if (target == index) claim(-1);
        return false;
    }
    if (me.health() < me.max_health() * .5f) return false;
    if (rally_group != index) { rally_group = index; rally_since = round; }
    claim(index);
    shared_memory[7] = static_cast<std::uint8_t>(round);
    if (g.state == 1) return capture_group(index);
    const auto staging = around(g.centre, g.radius + 4) & ~around(g.centre, g.radius + 3) & ~terrain;
    if (dist(me.position(), g.centre) > g.radius + 7) {
        if (round > rally_since + 100) {
            objective_backoff = round + 60; rally_group = -1; claim(-1); return false;
        }
        navigate(staging);
        return true;
    }
    float damage = 0, pool = 0, mitigation = 1, shield = 0;
    int ready = 0;
    for (const auto& f : farmers) {
        if (f.gems || f.health < f.max_health * .4f || dist(f.position, g.centre) > g.radius + 7
            || assignment(f.slot) != static_cast<unsigned>(index + 1)) continue;
        ++ready;
        damage += clear_rate(f, g);
        pool += std::max(0.f, f.health - std::max(180.f, f.max_health * .25f));
        mitigation = std::min(mitigation, f.mitigation);
        if (f.type == champion_type::varg) shield += f.focus * 2.5f / 8;
        if (f.type == champion_type::willow) shield += f.focus * 3 / 8;
    }
    const float turns = g.health / std::max(1.f, damage) + 2;
    const float incoming = std::max(0.f, g.damage * mitigation * (g.monolith ? 1.f : .65f) - shield);
    if (ready < 2 || incoming * turns > pool * .9f) {
        if (round > rally_since + 70) {
            std::cout << "objective backoff r=" << round << " ready=" << ready << " pool=" << pool << '\n';
            shared_memory[6] = 0; g.avoid_until = round + 50;
            objective_backoff = round + 50; rally_group = -1; claim(-1);
            return false;
        }
        navigate(staging, true);
        return true;
    }
    if (me.champion_name() == champion_type::willow) { navigate(staging); return true; }
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
    if (fuel_remaining() < 22000 || round_number() != round) return;
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
    if (!initialized) { initialize(); return; }
    auto& me = self();
    walked = false;
    if (!me.is_alive()) {
        buy_items();
        objective_ready = false;
        claim(-1);
        returning = false;
        was_alive = false;
        bank_altar = rally_group = -1;
        previous = {-1, -1};
        position_samples = 0;
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
    if (fuel_remaining() < 18000 || round_number() != round) return;
    const auto enemy_score = global_submitted_gems(team::enemy);
    if (round >= score_sample_round + 24) {
        const float rate = float(enemy_score - score_sample_value) / std::max(1u, round - score_sample_round);
        enemy_gem_rate = enemy_gem_rate == 0 ? rate : enemy_gem_rate * .65f + rate * .35f;
        score_sample_round = round;
        score_sample_value = enemy_score;
    }
    const auto position = me.position();
    unsigned repeats = 0;
    for (unsigned i = 0; i < std::min(position_samples, 8u); ++i)
        repeats += position_history[i] == position;
    oscillating = repeats >= 3;
    position_history[position_cursor++ % 8] = position;
    ++position_samples;
    stalled = position == previous ? stalled + 1 : 0;
    previous = position;
    const bool home = map::spawn_region(team::ally).is_set(position);
    if (home) {
        returning = false;
        if (me.health() < me.max_health() * .98f) return;
    }
    const bool carrier = me.gem_count() > 0;
    update_readiness();
    if (round_number() != round) return;
    if (!carrier) bank_altar = -1;
    const float enemy_damage = danger(position, true);
    if (!home && under_pressure()
        && (!favorable(position, carrier) || me.health() < enemy_damage * 2 + me.max_health() * .2f)) {
        if (me.health() < me.max_health() * .48f) returning = true;
        escape_until = round + 6;
        evade();
        return;
    }
    if (!home && round < escape_until) {
        evade();
        return;
    }
    support();
    const float reserve = std::max(180.f, me.max_health() * (carrier ? .3f : .4f));
    const bool deadline_race = enemy_score >= constants::winning_gems * .8f
        || global_submitted_gems(team::ally) >= constants::winning_gems * .8f;
    if (!home && (me.health() < reserve
        || (me.champion_name() != champion_type::tavi && me.gold_count() >= (objective_map ? 150u : 180u)
            && round > last_shop_round + 40 && !carrier && (!deadline_race || objective_map)))) returning = true;
    if (returning) { recover(); return; }
    // Deliver every captured bag before taking an optional fight or new farm.
    if (carrier) { bank(); return; }
    if (stalled > 10 && target >= 0 && groups[target].state != 1
        && !(objective_map && rally_group == target)) {
        groups[target].avoid_until = round + 35;
        claim(-1);
        stalled = 0;
    }
    if (defend()) return;
    if (team_objective()) return;
    if (objective_map && target >= 0 && groups[target].major) claim(-1);
    farm();
}
