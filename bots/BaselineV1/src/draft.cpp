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
    for (const auto& group : groups)
        if (group.camps().size() >= 3) ++packed;

    // Tavi converts income into damage without a shopping trip. Varg's splash
    // clears connected packs; Vendetta chains resets through individual kills.
    std::array order{C::tavi, C::varg, C::vendetta, C::ryth, C::vesper_vale,
        C::marcella, C::ren, C::stellar, C::prism, C::willow, C::cassi_and_issac};
    if (packed * 3 > groups.size()) std::swap(order[0], order[1]);
    for (auto choice : order) {
        if (std::find(picked.begin(), picked.end(), choice) != picked.end()) continue;
        const std::array<std::uint8_t, 4> plan{1, static_cast<std::uint8_t>(packed > 0),
            static_cast<std::uint8_t>(cambc::draft::team_size()), 0};
        cambc::draft_memory = plan;
        cambc::draft::pick(choice);
        std::cout << "draft " << static_cast<int>(choice) << '\n';
        return;
    }
}
