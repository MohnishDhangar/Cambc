#include <cambc.h>
#include "draft.h"
#include <algorithm>
#include <array>
#include <iostream>

void play_draft() {
    using C = cambc::champion_draft;
    const auto picked = cambc::draft::current_draft(cambc::team::ally);
    const auto groups = cambc::map::camp_groups();
    unsigned packed = 0;
    bool monoliths = false, ordinary_gems = false;
    for (const auto& group : groups) {
        if (group.camps().size() >= 3) ++packed;
        bool monolith = false;
        for (const auto& camp : group) monolith |= camp.is_monolith();
        monoliths |= monolith;
        ordinary_gems |= group.gem_value() > 0 && !monolith;
    }
    const bool monolith_only = monoliths && !ordinary_gems;
    const auto a = cambc::map::spawn_region(cambc::team::ally).positions().front();
    const auto b = cambc::map::spawn_region(cambc::team::enemy).positions().front();
    const bool contested = std::max(cambc::map::width(), cambc::map::height()) <= 65
        || a.chebyshev_distance(b) <= 42;

    // Tavi converts income into damage without a shopping trip. Varg's splash
    // clears connected packs; Vendetta chains resets through individual kills.
    std::array order{C::tavi, C::varg, C::vendetta, C::ryth, C::vesper_vale,
        C::marcella, C::ren, C::stellar, C::prism, C::willow, C::cassi_and_issac};
    if (packed * 3 > groups.size()) std::swap(order[0], order[1]);
    // Preserve the successful spacious-map farmers. Compact maps add health,
    // stun immunity and control; monolith maps need sustained allied healing.
    if (contested) order = {C::varg, C::tavi, C::marcella, C::ryth, C::ren,
        C::stellar, C::vendetta, C::willow, C::vesper_vale, C::prism, C::cassi_and_issac};
    if (monolith_only) order = {C::varg, C::willow, C::tavi, C::vendetta, C::ryth,
        C::marcella, C::ren, C::stellar, C::vesper_vale, C::prism, C::cassi_and_issac};
    for (auto choice : order) {
        if (std::find(picked.begin(), picked.end(), choice) != picked.end()) continue;
        const std::array<std::uint8_t, 4> plan{2, static_cast<std::uint8_t>(monolith_only),
            static_cast<std::uint8_t>(cambc::draft::team_size()), static_cast<std::uint8_t>(contested)};
        cambc::draft_memory = plan;
        cambc::draft::pick(choice);
        std::cout << "draft " << static_cast<int>(choice) << '\n';
        return;
    }
}
