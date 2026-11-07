#pragma once

#include "metro.hpp"

#include <string>
#include <vector>

enum class RouteMode { LeastTime, LeastInterchange };

struct PathHop {
    std::string station_id;
    std::string line;
};

struct RouteResult {
    bool found = false;
    std::vector<PathHop> hops;
    double minutes = 0.0;
    int stations_count = 0;
    int interchanges = 0;
    int fare_inr = 0;
};

class Router {
public:
    explicit Router(const MetroNetwork& network);

    RouteResult find(const std::string& from_id, const std::string& to_id, RouteMode mode) const;
    int fare(int hops) const;
    void print(const RouteResult& route) const;

private:
    const MetroNetwork& network_;
};
