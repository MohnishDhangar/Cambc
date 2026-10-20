#include <cambc.h>
#include "draft.h"
#include <algorithm>
#include <array>
#include <iostream>

void play_draft() {
    using C = cambc::champion_draft;
    const auto picked = cambc::draft::current_draft(cambc::team::ally);
    const auto groups = cambc::map::camp_groups();
    unsigned packs = 0, gems = 0, major_gems = 0;
    bool monolith = false;
    for (const auto& group : groups) {
        unsigned wolves = 0, elks = 0, clusters = 0;
        bool mono = false;
        for (const auto& c : group) {
            wolves += c.kind() == cambc::camp_type::wolf;
            elks += c.kind() == cambc::camp_type::elk;
            mono |= c.is_monolith();
            ++clusters;
        }
        packs += group.camps().size() >= 3;
        if (group.gem_value()) {
            ++gems;
            major_gems += mono || wolves * 1350 + elks * 2400 + (clusters - wolves - elks) * 500 >= 10000;
        }
        monolith |= mono;
    }
    const bool objective = gems && gems == major_gems;
    const bool distributed = !objective && std::min(cambc::map::width(), cambc::map::height()) >= 65;
    // Ordinary maps retain the measured v1 farming roster. The caster
    // composition is reserved for maps whose gem groups require a siege.
    std::array order{C::tavi, C::varg, C::vendetta, C::ryth, C::vesper_vale,
        C::marcella, C::ren, C::stellar, C::prism, C::willow, C::cassi_and_issac};
    if (packs * 3 > groups.size()) std::swap(order[0], order[1]);
    if (objective)
        order = {C::varg, C::ren, C::stellar, C::tavi, C::ryth,
            C::prism, C::cassi_and_issac, C::vendetta, C::vesper_vale, C::marcella, C::willow};
    if (objective && monolith)
        order = {C::stellar, C::prism, C::tavi, C::ren, C::varg,
            C::cassi_and_issac, C::ryth, C::vendetta, C::vesper_vale, C::marcella, C::willow};
    // Screened as R09 on 6 maps and validated on 11 different training maps
    // (21/34 wins vs frozen v4, 82.4 mean gem margin). Preserve the prior siege draft on objective maps.
    // Independent combination test required with current economy policy.
    if (!objective) order = {C::prism, C::tavi, C::vesper_vale,
        C::varg, C::vendetta, C::ryth, C::marcella, C::ren,
        C::stellar, C::heart_of_ruin, C::willow};
    for (auto choice : order) {
        if (std::find(picked.begin(), picked.end(), choice) != picked.end()) continue;
        // A small auditable map plan; gameplay still checks current live state.
        const std::array<std::uint8_t, 5> plan{4, static_cast<std::uint8_t>(objective),
            static_cast<std::uint8_t>(cambc::draft::team_size()), static_cast<std::uint8_t>(distributed),
            static_cast<std::uint8_t>(monolith)};
        cambc::draft_memory = plan;
        cambc::draft::pick(choice);
        std::cout << "draft " << static_cast<int>(choice) << '\n';
        return;
    }
}
