// Joint draft/early macro configuration. Different from frozen v4's fixed core.
#include <cambc.h>
#include "draft.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>

void play_draft() {
    using namespace cambc;
    using C=champion_draft;
    auto already=draft::current_draft(team::ally);
    const auto clusters=map::camp_groups();
    unsigned multi=0,gem_objectives=0,major=0;
    for (const auto& g:clusters) {
        float health=0.f;
        for (const auto& c:g) health+=c.base_stats().base_health;
        if (g.camps().size()>1) ++multi;
        if (g.gem_value()) {
            ++gem_objectives;
            if (health>=4200.f) ++major;
        }
    }
    const bool boss_only=gem_objectives>0 && gem_objectives==major;
    const bool spread=std::min(map::width(),map::height())>=65;
    // These are deliberately *different* composition hypotheses. The aim is
    // to optimize the downstream mode, not assume v4's Ren/Varg/Vendetta core.
    std::array<C,11> order{
        C::vesper_vale,C::varg,C::tavi,C::stellar,C::ryth,
        C::prism,C::vendetta,C::marcella,C::ren,C::willow,C::cassi_and_issac
    };
    if (multi*3 > clusters.size()) order={
        C::varg,C::vesper_vale,C::tavi,C::stellar,C::ryth,
        C::vendetta,C::prism,C::marcella,C::ren,C::willow,C::cassi_and_issac
    };
    if (spread) order={
        C::tavi,C::vesper_vale,C::stellar,C::varg,C::prism,
        C::ryth,C::vendetta,C::willow,C::marcella,C::ren,C::cassi_and_issac
    };
    if (boss_only) order={
        C::stellar,C::prism,C::tavi,C::varg,C::vesper_vale,
        C::cassi_and_issac,C::willow,C::ryth,C::marcella,C::vendetta,C::ren
    };
    // Draft bytes: version, objective-only flag, large-map flag, multi-camp flag.
    const std::array<std::uint8_t,4> message{
        6,static_cast<std::uint8_t>(boss_only),
        static_cast<std::uint8_t>(spread),
        static_cast<std::uint8_t>(multi*3>clusters.size())
    };
    draft_memory=message;
    for (auto pick:order) {
        if (std::find(already.begin(),already.end(),pick)!=already.end()) continue;
        draft::pick(pick);
        std::cout<<"v6 draft "<<static_cast<int>(pick)<<"\n";
        return;
    }
}
