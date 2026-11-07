#include "metro.hpp"
#include "router.hpp"

#include <algorithm>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string data_path(const std::string& argv0, const std::string& file) {
    const auto slash = argv0.find_last_of("/\\");
    const std::string dir = slash == std::string::npos ? std::string(".") : argv0.substr(0, slash);
    // binary lives in ./build or project root
    const std::vector<std::string> candidates = {
        dir + "/../data/" + file,
        dir + "/data/" + file,
        "data/" + file,
        "../data/" + file,
    };
    return candidates[0];
}

void print_help() {
    std::cout <<
        "Smart Commute Delhi — terminal metro router\n"
        "Commands:\n"
        "  help                         Show this help\n"
        "  stations [query]             List / search stations\n"
        "  lines                        List metro lines\n"
        "  info <station>               Station details\n"
        "  route <from> to <to>         Fastest route (default)\n"
        "  route <from> to <to> least   Fewest interchanges\n"
        "  fare <from> to <to>          Estimated DMRC fare\n"
        "  quit                         Exit\n"
        "\nStation names can be partial (e.g. \"rajiv\" or \"Huda City Centre\").\n";
}

std::vector<std::string> tokenize(const std::string& line) {
    std::istringstream in(line);
    std::vector<std::string> tokens;
    std::string tok;
    while (in >> tok) {
        tokens.push_back(tok);
    }
    return tokens;
}

std::pair<std::string, std::string> split_from_to(const std::vector<std::string>& tokens, std::size_t start) {
    std::string from, to;
    bool seen_to = false;
    for (std::size_t i = start; i < tokens.size(); ++i) {
        const std::string& t = tokens[i];
        if (to_lower(t) == "to" && !seen_to) {
            seen_to = true;
            continue;
        }
        if (to_lower(t) == "least") {
            continue;
        }
        if (!seen_to) {
            if (!from.empty()) from += " ";
            from += t;
        } else {
            if (!to.empty()) to += " ";
            to += t;
        }
    }
    return {from, to};
}

void print_station(const MetroNetwork& metro, const Station& st) {
    auto lines = metro.lines_at(st.id);
    std::cout << "  " << st.name << "  [" << st.id << "]\n    lines: ";
    for (std::size_t i = 0; i < lines.size(); ++i) {
        if (i) std::cout << ", ";
        std::cout << lines[i];
    }
    if (st.latitude != 0.0) {
        std::cout << "\n    coords: " << st.latitude << ", " << st.longitude;
    }
    std::cout << "\n";
}

}  // namespace

int main(int argc, char** argv) {
    const std::string argv0 = argc > 0 ? argv[0] : "metro";
    MetroNetwork metro;
    const std::string stations_csv = data_path(argv0, "stations.csv");
    const std::string connections_csv = data_path(argv0, "connections.csv");
    if (!metro.load(stations_csv, connections_csv)) {
        // fall back to CWD layout used by `make run`
        if (!metro.load("data/stations.csv", "data/connections.csv")) {
            std::cerr << "Failed to load metro data. Run from the project root after `make`.\n";
            return 1;
        }
    }

    Router router(metro);
    std::cout << "Smart Commute Delhi  |  " << metro.stations().size() << " stations, "
              << metro.connections().size() << " hops, " << metro.all_lines().size()
              << " lines\nType 'help' for commands.\n\n";

    auto resolve = [&](const std::string& q) -> const Station* {
        const Station* st = metro.find_station(q);
        if (st) {
            return st;
        }
        auto matches = metro.search(q);
        if (matches.size() == 1) {
            return matches[0];
        }
        if (matches.empty()) {
            std::cout << "No station matching \"" << q << "\".\n";
            return nullptr;
        }
        std::cout << "Ambiguous station \"" << q << "\". Matches:\n";
        for (std::size_t i = 0; i < std::min(matches.size(), static_cast<std::size_t>(12)); ++i) {
            std::cout << "  - " << matches[i]->name << "\n";
        }
        return nullptr;
    };

    std::string line;
    while (true) {
        std::cout << "metro> " << std::flush;
        if (!std::getline(std::cin, line)) {
            std::cout << "\n";
            break;
        }
        auto tokens = tokenize(line);
        if (tokens.empty()) {
            continue;
        }
        const std::string cmd = to_lower(tokens[0]);
        if (cmd == "quit" || cmd == "exit" || cmd == "q") {
            break;
        }
        if (cmd == "help" || cmd == "h" || cmd == "?") {
            print_help();
            continue;
        }
        if (cmd == "stations") {
            std::string q;
            for (std::size_t i = 1; i < tokens.size(); ++i) {
                if (!q.empty()) q += " ";
                q += tokens[i];
            }
            auto hits = metro.search(q);
            std::cout << hits.size() << " station(s)\n";
            const std::size_t limit = q.empty() ? 40 : hits.size();
            for (std::size_t i = 0; i < std::min(hits.size(), limit); ++i) {
                auto lines = metro.lines_at(hits[i]->id);
                std::cout << "  " << hits[i]->name;
                if (!lines.empty()) {
                    std::cout << "  (";
                    for (std::size_t j = 0; j < lines.size(); ++j) {
                        if (j) std::cout << ", ";
                        std::cout << lines[j];
                    }
                    std::cout << ")";
                }
                std::cout << "\n";
            }
            if (q.empty() && hits.size() > limit) {
                std::cout << "  ... " << (hits.size() - limit) << " more. Search with: stations <query>\n";
            }
            continue;
        }
        if (cmd == "lines") {
            for (const auto& l : metro.all_lines()) {
                std::cout << "  " << l << "\n";
            }
            continue;
        }
        if (cmd == "info") {
            std::string q;
            for (std::size_t i = 1; i < tokens.size(); ++i) {
                if (!q.empty()) q += " ";
                q += tokens[i];
            }
            const Station* st = resolve(q);
            if (st) {
                print_station(metro, *st);
            }
            continue;
        }
        if (cmd == "route" || cmd == "fare") {
            bool least = false;
            for (const auto& t : tokens) {
                if (to_lower(t) == "least") {
                    least = true;
                }
            }
            auto [from_q, to_q] = split_from_to(tokens, 1);
            if (from_q.empty() || to_q.empty()) {
                std::cout << "Usage: route <from> to <to> [least]\n";
                continue;
            }
            const Station* from = resolve(from_q);
            if (!from) continue;
            const Station* to = resolve(to_q);
            if (!to) continue;
            const auto mode = least ? RouteMode::LeastInterchange : RouteMode::LeastTime;
            auto result = router.find(from->id, to->id, mode);
            if (cmd == "fare") {
                if (!result.found) {
                    std::cout << "No route found.\n";
                } else {
                    std::cout << "Estimated fare " << from->name << " -> " << to->name
                              << ": ₹" << result.fare_inr << " (" << result.stations_count
                              << " stations, ~" << result.minutes << " min)\n";
                }
            } else {
                router.print(result);
            }
            continue;
        }
        std::cout << "Unknown command. Type 'help'.\n";
    }
    return 0;
}
