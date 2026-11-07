"""Thin wrapper around the compiled C++ router (build/metro).

The binary is an interactive CLI. We feed it one command per request on stdin and parse the
human-readable output. It starts in a few milliseconds (it only loads two small CSVs), so a
process-per-request keeps the integration stateless and easy to reason about.
"""
import re
import subprocess

from .config import METRO_BIN, ROOT

FARE_NOTE = (
    "Fare is an estimate: the engine approximates distance as ~1.2 km per station hop and uses "
    "distance slabs. The official DMRC fare for the journey can differ."
)

_HEADER = re.compile(
    r"Route \((\d+) stations, (\d+) interchanges?, ~([\d.]+) min, fare \u20b9(\d+)\)"
)
_SEGMENT = re.compile(r"^\s*\[(.+)\]\s*$")
_STATION = re.compile(r"^\s{4}[o|*]\s(.+?)\s*$")


class MetroError(Exception):
    """The router could not answer (binary missing, bad input, or timeout)."""


class MetroBinaryMissing(MetroError):
    pass


def _run(command: str, timeout: float = 10.0) -> str:
    if not METRO_BIN.exists():
        raise MetroBinaryMissing(f"{METRO_BIN} not found. Build it first with `make`.")
    try:
        proc = subprocess.run(
            [str(METRO_BIN)],
            input=f"{command}\nquit\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise MetroError("Router timed out.") from exc
    # stdout = banner, prompt, response, prompt. Splitting on the prompt isolates the response.
    chunks = proc.stdout.split("metro> ")
    if len(chunks) < 2:
        raise MetroError(f"Unexpected router output (exit code {proc.returncode}): {proc.stderr[:200]}")
    return chunks[1].strip("\n")


def parse_route(text: str) -> dict:
    """Parse the CLI's route output into a dict."""
    if "No route found" in text:
        return {"found": False}
    header = _HEADER.search(text)
    if not header:
        raise MetroError(f"Could not parse router output: {text[:200]!r}")

    segments: list[dict] = []
    for line in text.splitlines():
        seg = _SEGMENT.match(line)
        if seg:
            segments.append({"line": seg.group(1), "stations": []})
            continue
        st = _STATION.match(line)
        if st and segments:
            segments[-1]["stations"].append(st.group(1))

    path: list[str] = []
    for seg in segments:
        for name in seg["stations"]:
            if not path or path[-1] != name:  # an interchange station ends one segment, starts the next
                path.append(name)

    return {
        "found": True,
        "stations": int(header.group(1)),
        "interchanges": int(header.group(2)),
        "minutes": float(header.group(3)),
        "fare_inr": int(header.group(4)),
        "fare_note": FARE_NOTE,
        "segments": [
            {
                "line": s["line"],
                "from": s["stations"][0],
                "to": s["stations"][-1],
                "stops": max(len(s["stations"]) - 1, 0),
            }
            for s in segments
            if s["stations"]
        ],
        "interchange_at": [segments[i]["stations"][-1] for i in range(len(segments) - 1) if segments[i]["stations"]],
        "path": path,
    }


def find_route(source: str, destination: str, mode: str = "fastest") -> dict:
    """Run Dijkstra in the C++ engine. `source`/`destination` should be canonical station names."""
    if mode not in ("fastest", "least_interchange"):
        raise ValueError("mode must be 'fastest' or 'least_interchange'")
    command = f"route {source} to {destination}" + (" least" if mode == "least_interchange" else "")
    text = _run(command)
    if text.lstrip().startswith(("No station matching", "Ambiguous station", "Usage:")):
        raise MetroError(text.strip())
    result = parse_route(text)
    result.update({"from": source, "to": destination, "mode": mode})
    return result
