#pragma once

#include <string>
#include <unordered_map>
#include <vector>

struct Station {
    std::string id;
    std::string name;
    double latitude = 0.0;
    double longitude = 0.0;
};

struct Connection {
    std::string from_id;
    std::string to_id;
    std::string line;
    std::string color;
    double minutes = 2.2;
};

class MetroNetwork {
public:
    bool load(const std::string& stations_csv, const std::string& connections_csv);

    const std::vector<Station>& stations() const { return stations_; }
    const std::vector<Connection>& connections() const { return connections_; }

    const Station* find_station(const std::string& query) const;
    std::vector<const Station*> search(const std::string& query) const;
    std::vector<std::string> lines_at(const std::string& station_id) const;
    std::vector<std::string> all_lines() const;

    std::string display_name(const std::string& station_id) const;

private:
    std::vector<Station> stations_;
    std::vector<Connection> connections_;
    std::unordered_map<std::string, std::size_t> by_id_;
    std::unordered_map<std::string, std::size_t> by_name_lower_;
    std::unordered_map<std::string, std::size_t> by_norm_;
    std::unordered_map<std::string, std::string> aliases_;
};

std::string to_lower(std::string s);
std::string trim(const std::string& s);
std::string normalize_key(const std::string& s);
std::vector<std::string> split_csv(const std::string& line);
