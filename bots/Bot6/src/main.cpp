#include <cambc.h>
#include <iostream>
#include <exception>
#include "bot.h"
#include "draft.h"

int main() {
    Bot bot;
    std::cout << "Bot6 v6.0 macro-controller" << std::endl;
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else bot.play_turn();
        } catch (const std::exception& e) {
            std::cout << "v6 error at " << bot.action << ": " << e.what() << '\n';
        } catch (...) {
            std::cout << "v6 error unknown at " << bot.action << '\n';
        }
        cambc::end_turn();
    }
}
