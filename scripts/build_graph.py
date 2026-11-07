#!/usr/bin/env python3
"""Convert stations-lite.json + edge.json into CSVs used by the C++ CLI."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

LINE_BY_COLOR = {
    "#c1282b": "Red",
    "#f5d618": "Yellow",
    "#3e77bc": "Blue",
    "#015b97": "Blue Branch",
    "#52aa55": "Green",
    "#8115ff": "Violet",
    "#FF00FF": "Magenta",
    "#e692be": "Pink",
    "#d4d4d6": "Grey",
    "#eb8923": "Orange (Airport)",
}

# Average DMRC hop time used for shortest-time routing.
MINUTES_PER_HOP = 2.2


def main() -> None:
    stations = json.loads((DATA / "stations-lite.json").read_text())
    edges = json.loads((DATA / "edge.json").read_text())

    by_id = {s["id"]: s for s in stations}

    station_rows = []
    for s in stations:
        station_rows.append(
            {
                "id": s["id"],
                "name": str(s.get("text") or s.get("name") or s["id"]).strip(),
                "latitude": s.get("Latitude") or s.get("latitude") or "",
                "longitude": s.get("Longitude") or s.get("longitude") or "",
            }
        )

    seen_undirected = set()
    connection_rows = []
    missing = set()
    for e in edges:
        a, b = e["from"], e["to"]
        if a not in by_id or b not in by_id:
            missing.add((a, b))
            continue
        color = e.get("stroke", "")
        line = LINE_BY_COLOR.get(color, "Unknown")
        key = tuple(sorted((a, b))) + (line,)
        if key in seen_undirected:
            continue
        seen_undirected.add(key)
        connection_rows.append(
            {
                "from_id": a,
                "to_id": b,
                "line": line,
                "color": color,
                "minutes": MINUTES_PER_HOP,
            }
        )

    lines_of = defaultdict(set)
    for row in connection_rows:
        lines_of[row["from_id"]].add(row["line"])
        lines_of[row["to_id"]].add(row["line"])

    with (DATA / "stations.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "name", "latitude", "longitude"])
        w.writeheader()
        w.writerows(sorted(station_rows, key=lambda r: r["name"].lower()))

    with (DATA / "connections.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["from_id", "to_id", "line", "color", "minutes"]
        )
        w.writeheader()
        w.writerows(connection_rows)

    interchange_count = sum(1 for sid, ls in lines_of.items() if len(ls) > 1)
    print(
        f"Wrote {len(station_rows)} stations, {len(connection_rows)} undirected hops, "
        f"{interchange_count} interchange stations. missing_edges={len(missing)}"
    )


if __name__ == "__main__":
    main()
