# Fly-in Makefile
# Examples:
#   make run
#   make visual
#   make v M=medium/02_circular_loop.txt
#   make plan M=hard/03_ultimate_challenge.txt
#   make check

PYTHON := uv run python
MAIN := main.py

# Default map. Override with: M=medium/02_circular_loop.txt
M ?= easy/01_linear_path.txt

# Accept both:
#   M=easy/01_linear_path.txt
#   M=maps/easy/01_linear_path.txt
MAP := $(if $(filter maps/%,$(M)),$(M),maps/$(M))

# Extra CLI options, e.g.:
#   make run FLAGS="--max-paths 16"
FLAGS ?=

.DEFAULT_GOAL := help

.PHONY: help run visual plan turns run-all test lint typecheck check clean
.PHONY: r v p t c

help:
	@echo ""
	@echo "Fly-in commands"
	@echo "---------------"
	@echo "make run                         Run default map"
	@echo "make visual                      Run visualizer"
	@echo "make plan                        Show plan + turn count"
	@echo "make turns                       Show turn count"
	@echo "make run-all                     Run every map"
	@echo "make lint                        Run flake8"
	@echo "make typecheck                   Run mypy"
	@echo "make check                       Run lint + mypy"
	@echo "make clean                       Remove Python caches"
	@echo ""
	@echo "Choose a map:"
	@echo "  make visual M=medium/02_circular_loop.txt"
	@echo ""
	@echo "Extra options:"
	@echo '  make run M=hard/03_ultimate_challenge.txt FLAGS="--max-paths 16"'
	@echo ""
	@echo "Short aliases:"
	@echo "  make r   = run"
	@echo "  make v   = visual"
	@echo "  make p   = plan"
	@echo "  make t   = test"
	@echo "  make c   = check"
	@echo ""

run:
	$(PYTHON) $(MAIN) $(MAP) $(FLAGS)

visual:
	$(PYTHON) $(MAIN) $(MAP) --visual $(FLAGS)

plan:
	$(PYTHON) $(MAIN) $(MAP) --show-plan --show-turn-count $(FLAGS)

turns:
	$(PYTHON) $(MAIN) $(MAP) --show-turn-count $(FLAGS)

run-all:
	@set -e; \
	for map in $$(find maps -type f -name '*.txt' | sort); do \
		echo ""; \
		echo "==> $$map"; \
		$(PYTHON) $(MAIN) "$$map" --show-turn-count; \
	done

lint:
	uv run flake8 .

typecheck:
	uv run mypy .

check: lint typecheck turns

clean:
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	@rm -rf .pytest_cache .mypy_cache
	@echo "Caches removed."

# Short aliases
r: run
v: visual
p: plan
t: turns
c: check
