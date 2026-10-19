#pragma once

#include <cambc.h>
#include <array>
#include <cstdint>
#include <vector>

// One persistent instance per champion. Six shared bytes advertise assignments;
// the last two hold a leased team objective. Live observations stay local.
class Bot {
    struct Group {
        cambc::map::camp_group camp;
        cambc::bitboard tiles;
        cambc::vec2 centre;
        float health = 0, damage = 0;
        int members = 0;
        bool visible = false;
        bool monolith = false;
        bool major = false;
        int radius = 0, splash_targets = 1;
        float full_health = 0, full_damage = 0;
        unsigned gems = 0, gold = 0;
        std::vector<cambc::vec2> positions;
        int state = 0; // 0 alive/unknown, 1 reward, 2 respawning
        unsigned ready_round = 0;
        unsigned avoid_until = 0;
    };

    bool initialized = false;
    int initialization_stage = 0;
    bool relax_route = false;
    unsigned navigation_round = 0;
    bool returning = false;
    bool walked = false;
    bool splash = false;
    bool monolith_map = false;
    bool objective_map = false;
    bool caster_build = false;
    bool contested = false;
    bool was_alive = true;
    bool objective_ready = false;
    float farm_dps = 0, shield_cycle = 0, incoming_multiplier = 1;
    int slot = 0;
    int target = -1;
    int stalled = 0;
    int bank_altar = -1;
    int rally_group = -1;
    cambc::vec2 previous{-1, -1};
    unsigned round = 0;
    unsigned last_shop_round = 0;
    unsigned respawn_round = 0;
    unsigned score_sample_round = 0, score_sample_value = 0;
    float enemy_gem_rate = 0;
    unsigned rally_since = 0, objective_backoff = 0;
    unsigned last_nav_progress = 0;
    unsigned escape_until = 0;
    unsigned bank_progress_round = 0;
    int bank_best_distance = 65535;
    unsigned farm_power_round = 0;
    std::array<cambc::vec2, 8> position_history{};
    unsigned position_cursor = 0, position_samples = 0;
    bool oscillating = false;
    int best_nav_distance = 65535;
    cambc::vec2 nav_anchor{-1, -1};
    struct Threat {
        cambc::vec2 position{-1, -1};
        float damage = 0;
        int range = 0, group = -1;
        bool enemy = false;
        unsigned seen = 0;
    };
    struct Fighter {
        cambc::champion champion;
        cambc::vec2 position;
        float health, max_health, dps, burst, healing, shielding;
        int reach;
    };
    struct Altar {
        cambc::vec2 position;
        unsigned avoid_until = 0;
        std::vector<cambc::vec2> approaches;
    };
    std::vector<Threat> threats;
    std::vector<Threat> enemy_memory;
    std::vector<Fighter> friends, enemies;
    struct Farmer {
        int slot;
        cambc::vec2 position;
        cambc::champion_type type;
        float health, max_health, strength, focus, mitigation;
        int range;
        unsigned gems;
    };
    std::vector<Farmer> farmers;
    unsigned farmers_round = 0;
    void refresh_farmers();
    float clear_rate(const Farmer& farmer, const Group& group) const;
    int capture_recipient(int group);
    bool capture_group(int group);
    std::vector<Altar> altars;
    std::vector<Group> groups;
    std::vector<cambc::champion> allies;
    std::vector<cambc::champion> enemy_roster;
    std::vector<cambc::champion> visible_enemies;
    std::array<std::uint8_t, 8> claims{};
    cambc::bitboard terrain;
    int width = 0;
    std::vector<std::uint16_t> home_values, altar_values;
    int home_steps(cambc::vec2 p) const { return home_values[p.y * width + p.x]; }
    int altar_steps(cambc::vec2 p) const { return altar_values[p.y * width + p.x]; }
    cambc::distance_field home_distance;
    cambc::distance_field altar_distance;

    void initialize();
    void observe();
    void refresh_threats();
    void buy_items();
    void claim(int group);
    unsigned assignment(int slot) const;
    void update_readiness();
    void farm_power();
    Fighter inspect(const cambc::champion& champion) const;
    bool favorable(cambc::vec2 point, bool carrier = false) const;
    bool under_pressure() const;
    bool support();
    void evade();
    bool siege_monolith();
    bool team_objective();
    int select_camp();
    float expected_damage(const Group& group) const;
    float danger(cambc::vec2 tile, bool enemies_only = false) const;
    bool navigate(cambc::bitboard goals, bool escape = false, bool dash = true);
    bool fight(const cambc::unit& victim, bool enemy);
    bool defend();
    void recover();
    bool bank();
    void farm();
    void scout();

public:
    const char* action = "startup";
    void play_turn();
};
