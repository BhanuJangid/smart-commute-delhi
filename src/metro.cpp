#include "metro.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>

std::string to_lower(std::string s) {
    for (char& c : s) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    return s;
}

std::string normalize_key(const std::string& s) {
    std::string out;
    for (unsigned char c : to_lower(s)) {
        if (std::isalnum(c)) {
            out.push_back(static_cast<char>(c));
        }
    }
    return out;
}

std::string trim(const std::string& s) {
    std::size_t a = 0;
    while (a < s.size() && std::isspace(static_cast<unsigned char>(s[a]))) {
        ++a;
    }
    std::size_t b = s.size();
    while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) {
        --b;
    }
    return s.substr(a, b - a);
}

std::vector<std::string> split_csv(const std::string& line) {
    std::vector<std::string> cols;
    std::string cur;
    bool in_quotes = false;
    for (char c : line) {
        if (c == '"') {
            in_quotes = !in_quotes;
        } else if (c == ',' && !in_quotes) {
            cols.push_back(trim(cur));
            cur.clear();
        } else {
            cur.push_back(c);
        }
    }
    cols.push_back(trim(cur));
    return cols;
}

bool MetroNetwork::load(const std::string& stations_csv, const std::string& connections_csv) {
    stations_.clear();
    connections_.clear();
    by_id_.clear();
    by_name_lower_.clear();
    by_norm_.clear();
    aliases_.clear();

    std::ifstream sf(stations_csv);
    if (!sf) {
        return false;
    }
    std::string line;
    std::getline(sf, line);  // header
    while (std::getline(sf, line)) {
        if (trim(line).empty()) {
            continue;
        }
        auto cols = split_csv(line);
        if (cols.size() < 2) {
            continue;
        }
        Station st;
        st.id = cols[0];
        st.name = cols[1];
        if (cols.size() > 2 && !cols[2].empty()) {
            st.latitude = std::stod(cols[2]);
        }
        if (cols.size() > 3 && !cols[3].empty()) {
            st.longitude = std::stod(cols[3]);
        }
        by_id_[st.id] = stations_.size();
        by_id_[to_lower(st.id)] = stations_.size();
        by_name_lower_[to_lower(st.name)] = stations_.size();
        by_norm_[normalize_key(st.name)] = stations_.size();
        stations_.push_back(std::move(st));
    }

    aliases_["hudacitycentre"] = "HCC";
    aliases_["hudacitycenter"] = "HCC";

    std::ifstream cf(connections_csv);
    if (!cf) {
        return false;
    }
    std::getline(cf, line);  // header
    while (std::getline(cf, line)) {
        if (trim(line).empty()) {
            continue;
        }
        auto cols = split_csv(line);
        if (cols.size() < 5) {
            continue;
        }
        Connection e;
        e.from_id = cols[0];
        e.to_id = cols[1];
        e.line = cols[2];
        e.color = cols[3];
        e.minutes = std::stod(cols[4]);
        connections_.push_back(e);
    }
    return !stations_.empty() && !connections_.empty();
}

const Station* MetroNetwork::find_station(const std::string& query) const {
    const std::string q = to_lower(trim(query));
    const std::string nq = normalize_key(query);
    if (q.empty()) {
        return nullptr;
    }
    auto id_it = by_id_.find(query);
    if (id_it == by_id_.end()) {
        id_it = by_id_.find(q);
    }
    if (id_it != by_id_.end()) {
        return &stations_[id_it->second];
    }
    auto nit = by_name_lower_.find(q);
    if (nit != by_name_lower_.end()) {
        return &stations_[nit->second];
    }
    auto nrm = by_norm_.find(nq);
    if (nrm != by_norm_.end()) {
        return &stations_[nrm->second];
    }
    auto al = aliases_.find(nq);
    if (al != aliases_.end()) {
        auto mapped = by_id_.find(al->second);
        if (mapped != by_id_.end()) {
            return &stations_[mapped->second];
        }
    }
    const Station* best = nullptr;
    int matches = 0;
    for (const auto& st : stations_) {
        const std::string name = to_lower(st.name);
        const std::string nn = normalize_key(st.name);
        if (name.find(q) != std::string::npos || nn.find(nq) != std::string::npos) {
            ++matches;
            best = &st;
        }
    }
    return matches == 1 ? best : nullptr;
}

std::vector<const Station*> MetroNetwork::search(const std::string& query) const {
    const std::string q = to_lower(trim(query));
    std::vector<const Station*> out;
    for (const auto& st : stations_) {
        if (q.empty() || to_lower(st.name).find(q) != std::string::npos ||
            to_lower(st.id).find(q) != std::string::npos ||
            normalize_key(st.name).find(normalize_key(q)) != std::string::npos) {
            out.push_back(&st);
        }
    }
    std::sort(out.begin(), out.end(), [](const Station* a, const Station* b) {
        return a->name < b->name;
    });
    return out;
}

std::vector<std::string> MetroNetwork::lines_at(const std::string& station_id) const {
    std::vector<std::string> lines;
    for (const auto& e : connections_) {
        if (e.from_id == station_id || e.to_id == station_id) {
            if (std::find(lines.begin(), lines.end(), e.line) == lines.end()) {
                lines.push_back(e.line);
            }
        }
    }
    std::sort(lines.begin(), lines.end());
    return lines;
}

std::vector<std::string> MetroNetwork::all_lines() const {
    std::vector<std::string> lines;
    for (const auto& e : connections_) {
        if (std::find(lines.begin(), lines.end(), e.line) == lines.end()) {
            lines.push_back(e.line);
        }
    }
    std::sort(lines.begin(), lines.end());
    return lines;
}

std::string MetroNetwork::display_name(const std::string& station_id) const {
    auto it = by_id_.find(station_id);
    if (it == by_id_.end()) {
        return station_id;
    }
    return stations_[it->second].name;
}
