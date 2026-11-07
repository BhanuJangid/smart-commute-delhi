#include "router.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <queue>
#include <unordered_map>
#include <utility>

namespace {

constexpr double kInterchangePenaltyMinutes = 5.0;
constexpr double kInterchangeWeight = 10000.0;

struct Node {
    std::string station;
    std::string line;
    bool operator==(const Node& o) const { return station == o.station && line == o.line; }
};

struct NodeHash {
    std::size_t operator()(const Node& n) const {
        return std::hash<std::string>{}(n.station) ^ (std::hash<std::string>{}(n.line) << 1);
    }
};

struct AdjEdge {
    Node to;
    double minutes;
    bool interchange;
};

struct PQItem {
    double cost;
    Node node;
    bool operator>(const PQItem& o) const { return cost > o.cost; }
};

}  // namespace

Router::Router(const MetroNetwork& network) : network_(network) {}

int Router::fare(int hops) const {
    // DMRC distance slabs approximated at ~1.2 km per hop.
    const double km = std::max(0, hops) * 1.2;
    if (km <= 2) return 10;
    if (km <= 5) return 20;
    if (km <= 12) return 30;
    if (km <= 21) return 40;
    if (km <= 32) return 50;
    return 60;
}

RouteResult Router::find(const std::string& from_id, const std::string& to_id, RouteMode mode) const {
    RouteResult result;
    if (from_id == to_id) {
        result.found = true;
        result.hops.push_back({from_id, ""});
        result.stations_count = 1;
        result.fare_inr = 10;
        return result;
    }

    std::unordered_map<std::string, std::vector<std::pair<std::string, std::string>>> neighbors;
    std::unordered_map<std::string, std::vector<std::string>> lines_at;
    for (const auto& e : network_.connections()) {
        neighbors[e.from_id].push_back({e.to_id, e.line});
        neighbors[e.to_id].push_back({e.from_id, e.line});
        lines_at[e.from_id].push_back(e.line);
        lines_at[e.to_id].push_back(e.line);
    }
    for (auto& [sid, lines] : lines_at) {
        std::sort(lines.begin(), lines.end());
        lines.erase(std::unique(lines.begin(), lines.end()), lines.end());
    }

    std::unordered_map<Node, std::vector<AdjEdge>, NodeHash> adj;
    for (const auto& [sid, lines] : lines_at) {
        for (const auto& line : lines) {
            for (const auto& [nbr, nbr_line] : neighbors[sid]) {
                if (nbr_line == line) {
                    adj[{sid, line}].push_back({{nbr, line}, 2.2, false});
                }
            }
        }
        for (std::size_t i = 0; i < lines.size(); ++i) {
            for (std::size_t j = i + 1; j < lines.size(); ++j) {
                adj[{sid, lines[i]}].push_back({{sid, lines[j]}, kInterchangePenaltyMinutes, true});
                adj[{sid, lines[j]}].push_back({{sid, lines[i]}, kInterchangePenaltyMinutes, true});
            }
        }
    }

    auto weight = [&](const AdjEdge& e) {
        if (mode == RouteMode::LeastInterchange) {
            return e.interchange ? kInterchangeWeight : 1.0;
        }
        return e.minutes;
    };

    std::unordered_map<Node, double, NodeHash> dist;
    std::unordered_map<Node, Node, NodeHash> parent;
    std::priority_queue<PQItem, std::vector<PQItem>, std::greater<PQItem>> pq;

    for (const auto& line : lines_at[from_id]) {
        Node start{from_id, line};
        dist[start] = 0.0;
        pq.push({0.0, start});
    }

    Node goal{"", ""};
    double best = std::numeric_limits<double>::infinity();
    while (!pq.empty()) {
        auto [cost, u] = pq.top();
        pq.pop();
        if (cost > dist[u]) {
            continue;
        }
        if (u.station == to_id && cost < best) {
            best = cost;
            goal = u;
        }
        for (const auto& e : adj[u]) {
            const double nc = cost + weight(e);
            auto it = dist.find(e.to);
            if (it == dist.end() || nc < it->second) {
                dist[e.to] = nc;
                parent[e.to] = u;
                pq.push({nc, e.to});
            }
        }
    }

    if (goal.station.empty()) {
        return result;
    }

    std::vector<Node> rev;
    Node cur = goal;
    rev.push_back(cur);
    while (!(cur.station == from_id && dist[cur] == 0.0)) {
        auto it = parent.find(cur);
        if (it == parent.end()) {
            break;
        }
        cur = it->second;
        rev.push_back(cur);
    }
    std::reverse(rev.begin(), rev.end());

    result.found = true;
    for (const auto& n : rev) {
        result.hops.push_back({n.station, n.line});
    }
    std::string last_station;
    std::string last_line;
    for (const auto& hop : result.hops) {
        if (hop.station_id != last_station) {
            ++result.stations_count;
            last_station = hop.station_id;
        }
        if (!last_line.empty() && hop.line != last_line) {
            ++result.interchanges;
        }
        last_line = hop.line;
    }
    result.minutes = 0.0;
    for (std::size_t i = 1; i < result.hops.size(); ++i) {
        if (result.hops[i].station_id == result.hops[i - 1].station_id) {
            result.minutes += kInterchangePenaltyMinutes;
        } else {
            result.minutes += 2.2;
        }
    }
    result.fare_inr = fare(std::max(0, result.stations_count - 1));
    return result;
}

void Router::print(const RouteResult& route) const {
    if (!route.found) {
        std::cout << "No route found.\n";
        return;
    }
    std::cout << "\n  Route (" << route.stations_count << " stations, "
              << route.interchanges << " interchange"
              << (route.interchanges == 1 ? "" : "s") << ", ~" << route.minutes
              << " min, fare ₹" << route.fare_inr << ")\n\n";

    std::string current_line;
    int seg_start = 0;
    for (std::size_t i = 0; i < route.hops.size(); ++i) {
        const auto& hop = route.hops[i];
        if (current_line.empty()) {
            current_line = hop.line;
            seg_start = static_cast<int>(i);
        }
        const bool last = i + 1 == route.hops.size();
        const bool line_change = !last && route.hops[i + 1].line != current_line;
        if (last || line_change) {
            std::cout << "  [" << current_line << "]\n";
            for (int j = seg_start; j <= static_cast<int>(i); ++j) {
                const std::string mark = (j == seg_start) ? "o" : (j == static_cast<int>(i) ? "*" : "|");
                std::cout << "    " << mark << " " << network_.display_name(route.hops[j].station_id)
                          << "\n";
            }
            if (line_change) {
                std::cout << "    -> interchange\n";
                current_line = route.hops[i + 1].line;
                seg_start = static_cast<int>(i + 1);
                if (route.hops[i + 1].station_id != hop.station_id) {
                    seg_start = static_cast<int>(i);
                }
            }
        }
    }
    std::cout << "\n";
}
