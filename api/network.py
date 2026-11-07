"""Loads the metro graph data (the same CSVs the C++ router reads) into Python.

The C++ engine owns routing. Python only needs station metadata for name resolution,
station info answers and the RAG station documents.
"""
import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import DATA_DIR


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    latitude: float
    longitude: float
    lines: tuple[str, ...]
    # line name -> names of the stations adjacent to this one on that line
    neighbours: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def is_interchange(self) -> bool:
        return len(self.lines) > 1


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=4)
def load_stations(data_dir: Path = DATA_DIR) -> tuple[Station, ...]:
    stations = _read_csv(Path(data_dir) / "stations.csv")
    connections = _read_csv(Path(data_dir) / "connections.csv")
    names = {s["id"]: s["name"] for s in stations}

    lines: dict[str, set[str]] = {s["id"]: set() for s in stations}
    adjacent: dict[str, dict[str, set[str]]] = {s["id"]: {} for s in stations}
    for c in connections:
        a, b, line = c["from_id"], c["to_id"], c["line"]
        for here, there in ((a, b), (b, a)):
            if here in lines and there in names:
                lines[here].add(line)
                adjacent[here].setdefault(line, set()).add(names[there])

    result = []
    for s in stations:
        sid = s["id"]
        result.append(
            Station(
                id=sid,
                name=s["name"],
                latitude=float(s["latitude"]),
                longitude=float(s["longitude"]),
                lines=tuple(sorted(lines[sid])),
                neighbours=tuple(
                    (line, tuple(sorted(adjacent[sid][line]))) for line in sorted(adjacent[sid])
                ),
            )
        )
    return tuple(result)


def station_describe(st: Station) -> str:
    """Plain-text description used for both the station-info tool and the RAG documents."""
    parts = [f"{st.name} (station id {st.id}) is served by the {', '.join(st.lines)} line(s)."]
    if st.is_interchange:
        parts.append(f"It is an interchange station between the {' and '.join(st.lines)} lines.")
    for line, adj in st.neighbours:
        parts.append(f"On the {line} line it is adjacent to: {', '.join(adj)}.")
    parts.append(f"Coordinates: {st.latitude}, {st.longitude}.")
    return " ".join(parts)
