#pragma once

#include <cambc.h>
#include <array>
#include <cstdint>
#include <vector>

// One persistent instance per champion. Static map data is cached once; camp
// observations remain private, while shared bytes advertise current assignments.
class Bot {
    struct Group {
        cambc::map::camp_group camp;
        cambc::bitboard tiles;
        cambc::vec2 centre;
        float health = 0, damage = 0;
        int members = 0;
        bool visible = false;
        int state = 0; // 0 alive/unknown, 1 reward, 2 respawning
        unsigned ready_round = 0;
        unsigned avoid_until = 0;
    };

    bool initialized = false;
    bool returning = false;
    bool walked = false;
    bool splash = false;
    float farm_dps = 0, shield_cycle = 0, incoming_multiplier = 1;
    int slot = 0;
    int target = -1;
    int stalled = 0;
    cambc::vec2 previous{-1, -1};
    unsigned round = 0;
    unsigned last_shop_round = 0;
    struct Threat { cambc::vec2 position; float damage; int range; };
    std::vector<Threat> threats;
    std::vector<Group> groups;
    std::vector<cambc::champion> allies;
    std::vector<cambc::champion> enemy_roster;
    std::vector<cambc::champion> visible_enemies;
    std::array<std::uint8_t, 8> claims{};
    cambc::bitboard terrain;
    cambc::distance_field home_distance;
    cambc::distance_field altar_distance;

    void initialize();
    void observe();
    void refresh_threats();
    void buy_items();
    void claim(int group);
    int select_camp();
    float expected_damage(const Group& group) const;
    float danger(cambc::vec2 tile) const;
    bool navigate(cambc::bitboard goals, bool escape = false, bool dash = true);
    bool fight(const cambc::unit& victim, bool enemy);
    bool defend();
    void recover();
    bool bank();
    bool capture_group(int index);
    void farm();
    void scout();

public:
    const char* action = "startup";
    void play_turn();
};
