# Fly-in

Fly-in is a drone routing and simulation project.

The program calculates paths for drones through a graph-based map and simulates their movement turn by turn.

## Requirements

- Python 3.13+
- `uv`
- Arcade (installed through the project dependencies)

## Installation

Install the project dependencies with:

```bash
uv sync
```

## Running the simulation

Run a map with:

```bash
make run M=easy/01_linear_path.txt
```

You can also use the Python command directly:

```bash
uv run python main.py maps/easy/01_linear_path.txt
```

## Available maps

Maps are organized by difficulty:

```text
maps/
├── easy/
├── medium/
├── hard/
└── challenger/
```

Example:

```bash
make run M=medium/02_circular_loop.txt
```

## Show turn count

```bash
make turns M=medium/02_circular_loop.txt
```

or:

```bash
make t M=medium/02_circular_loop.txt
```

## Show the calculated plan

```bash
make plan M=medium/02_circular_loop.txt
```

This displays the candidate paths, path costs and drone assignments.

## Visualization

Start the Arcade visualization with:

```bash
make visual M=easy/01_linear_path.txt
```

Short form:

```bash
make v M=easy/01_linear_path.txt
```

### Visualization controls

| Key / Action | Function |
|---|---|
| `SPACE` | Start / pause simulation |
| `RIGHT` | Next turn |
| `R` | Reset simulation |
| `C` | Reset camera |
| `W` / `UP` | Increase speed |
| `S` / `DOWN` | Decrease speed |
| `X` | Reset speed |
| `+` / `-` | Change speed |
| `ESC` | Close visualization |
| Left mouse + drag | Move camera |
| Mouse wheel | Zoom |

The visualization shows the drones, zones, connections and their movement through the simulation.

## Run all maps

To execute all map files:

```bash
make run-all
```

The turn count is displayed for every map.

## Tests

Run the complete test suite:

```bash
make test
```

For the complete project check:

```bash
make check
```

This runs:

- `flake8`
- `mypy`
- `pytest`

## Additional options

Additional arguments can be passed through `FLAGS`.

For example, to limit the number of candidate paths:

```bash
make run \
    M=medium/02_circular_loop.txt \
    FLAGS="--max-paths 16"
```

## Make commands

| Command | Description |
|---|---|
| `make run` | Run a map |
| `make visual` | Run the Arcade visualization |
| `make plan` | Show the calculated plan |
| `make turns` | Show the total turn count |
| `make run-all` | Run all maps |
| `make test` | Run tests |
| `make check` | Run linting, type checking and tests |
| `make clean` | Remove Python caches |

Short aliases:

```text
make r  → make run
make v  → make visual
make p  → make plan
make t  → show turn count
make c  → make check
```

## Example workflow

A typical workflow is:

```bash
uv sync
make test
make run M=easy/01_linear_path.txt
make plan M=medium/02_circular_loop.txt
make visual M=medium/02_circular_loop.txt
make run-all
```
