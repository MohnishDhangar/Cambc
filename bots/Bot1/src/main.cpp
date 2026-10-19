// Dispatch draft and gameplay; a failed turn is logged and still yields.
#include <cambc.h>
#include <iostream>
#include "bot.h"
#include "draft.h"

int main() {
    Bot bot;
    std::cout << "Bot1 strategy v4 (SDK 2.2.5)" << std::endl;
    while (true) {
        const auto started = cambc::round_number();
        try {
            if (cambc::is_draft())
                play_draft();
            else
                bot.play_turn();
        } catch (const std::exception& error) {
            std::cout << "bot error at " << bot.action << ": " << error.what() << std::endl;
        } catch (...) {
            std::cout << "bot error: unknown exception" << std::endl;
        }

        if (!cambc::is_draft() && cambc::round_number() != started)
            std::cout << "fuel spill at " << bot.action << " from " << started << " to " << cambc::round_number() << '\n';
        cambc::end_turn();
    }
}
