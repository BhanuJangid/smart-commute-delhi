CXX := g++
CXXFLAGS := -std=c++17 -O2 -Wall -Wextra -Wpedantic
SRC := src/metro.cpp src/router.cpp src/main.cpp
BIN := build/metro

.PHONY: all run data clean venv install ingest serve test benchmark eval

all: data $(BIN)

$(BIN): $(SRC) src/metro.hpp src/router.hpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -o $(BIN) $(SRC)

data:
	python3 scripts/build_graph.py

run: all
	./$(BIN)

clean:
	rm -rf build

# ---- Python API, RAG and agent ----
VENV := .venv

venv:
	python3 -m venv $(VENV)

install: venv
	$(VENV)/bin/pip install -r requirements-dev.txt

ingest:
	$(VENV)/bin/python scripts/ingest_knowledge.py

serve: all
	$(VENV)/bin/uvicorn api.main:app --reload

test: all
	$(VENV)/bin/python -m pytest -q

benchmark: all
	$(VENV)/bin/python scripts/benchmark.py

eval:
	$(VENV)/bin/python scripts/eval_agent.py
