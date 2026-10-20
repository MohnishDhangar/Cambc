#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <vector>

// V6 is a new, parameterised macro controller. It does not inherit Bot1's
// target-selection decision tree. Only SDK-facing safe primitives are reused.
enum class MacroMode : std::uint8_t {
    economy=0, tempo_farm=1, contest=2, objective=3, adaptive=4
};
enum class Job : std::uint8_t {
    farm=0, bank=1, recover=2, intercept=3, siege=4
};

class Bot {
    struct CampPlan {
        cambc::map::camp_group group;
        cambc::vec2 centre;
        float base_hp = 0.f;
        float base_damage = 0.f;
        int members = 0;
        bool major = false;
        unsigned avoid_until = 0;
    };
    struct Plan {
        MacroMode macro = MacroMode::adaptive;
        Job job = Job::farm;
        int camp_index = -1;
        cambc::vec2 enemy_target{-1,-1};
        float utility = -1e9f;
    };
    struct Params {
        float risk_weight = 0.9f;
        float distance_weight = 1.0f;
        float gold_weight = 0.22f;
        float escort_weight = 1.0f;
        float contest_bonus = 1.0f;
        float farm_bonus = 1.0f;
        float objective_bonus = 1.0f;
        float health_reserve = 0.26f;
        int bank_gems = 8;
        int shop_gold = 180;
        int max_danger_distance = 5;
    };

    bool initialized = false;
    bool caster = false;
    bool walked = false;
    int slot = 0;
    int held_target = -1;
    int stalled_turns = 0;
    unsigned round = 0;
    unsigned last_shop_round = 0;
    cambc::vec2 last_position{-1,-1};
    cambc::bitboard terrain;
    cambc::distance_field altar_distance;
    cambc::distance_field home_distance;
    std::vector<cambc::champion> allies;
    std::vector<cambc::champion> enemies;
    std::vector<CampPlan> camps;
    std::array<std::uint8_t,8> claims{};
    Params params;
    Plan plan;

    void initialize();
    void observe();
    float danger(cambc::vec2 pos) const;
    float clear_time(const CampPlan& group) const;
    float camp_utility(int i, MacroMode mode) const;
    MacroMode macro_mode() const;
    Plan select_plan(MacroMode mode);
    void publish_claim(int target);
    bool buy();
    bool try_combat(const cambc::unit& target, bool is_enemy);
    bool attack_visible_enemy(bool chase);
    bool cast_or_attack_camp(const CampPlan& group);
    bool navigate(cambc::bitboard goals, bool flee=false);
    bool do_bank();
    bool do_recover();
    bool do_farm();
    bool do_intercept();
    bool do_siege();
    void ward();
public:
    const char* action = "boot";
    void play_turn();
};
