"""Command-line entry point for Fly-in."""

import argparse
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

from parser import MapParser, MapParserError
from simulation import Simulation


EXIT_SUCCESS = 0
EXIT_FAILURE = 1


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    argument_parser = argparse.ArgumentParser(
        prog="fly-in",
        description=(
            "Route drones through a capacity-constrained network."
        ),
    )

    argument_parser.add_argument(
        "map_file",
        type=Path,
        help="Path to the Fly-in map file.",
    )

    argument_parser.add_argument(
        "--max-paths",
        type=int,
        default=None,
        help="Maximum number of candidate paths.",
    )

    argument_parser.add_argument(
        "--max-turns",
        type=int,
        default=10_000,
        help="Maximum number of simulation turns.",
    )

    argument_parser.add_argument(
        "--debug",
        action="store_true",
        help="Display a complete traceback when an error occurs.",
    )

    argument_parser.add_argument(
        "--show-turn-count",
        action="store_true",
        help="Display the total number of simulation turns.",
    )

    argument_parser.add_argument(
        "--show-plan",
        action="store_true",
        help="Display candidate paths and drone assignments.",
    )

    argument_parser.add_argument(
        "--visual",
        action="store_true",
        help="Open the Arcade replay window.",
    )

    return argument_parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Load a map, run the simulation and print the result."""
    argument_parser = build_argument_parser()
    arguments = argument_parser.parse_args(argv)

    if not arguments.map_file.is_file():
        print(
            f"Error: Map file does not exist: "
            f"{arguments.map_file}",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    try:
        drone_map = MapParser().parse_file(
            arguments.map_file
        )

        simulation = Simulation(
            drone_map=drone_map,
            max_paths=arguments.max_paths,
        )

        result = simulation.run(
            max_turns=arguments.max_turns,
        )

        if arguments.visual:
            from visualization import run_visualization
            run_visualization(result)

    except (
        MapParserError,
        OSError,
        ValueError,
        RuntimeError,
    ) as error:
        if arguments.debug:
            traceback.print_exc()
        else:
            print(
                f"Error: {type(error).__name__}: {error}",
                file=sys.stderr,
            )

        return EXIT_FAILURE

    if result.output:
        print(result.output)

    if arguments.show_turn_count:
        print(
            f"Total turns: {result.total_turns}",
            file=sys.stderr,
        )
    if arguments.show_plan:
        print("Candidate paths:", file=sys.stderr)

        path_numbers = {
            id(path): index
            for index, path in enumerate(
                result.plan.paths,
                start=1,
            )
        }

        for index, path in enumerate(
            result.plan.paths,
            start=1,
        ):
            print(
                f"  Path {index}: "
                f"cost={path.total_cost}, "
                f"zones={' -> '.join(path.zones)}",
                file=sys.stderr,
            )

        print("Assignments:", file=sys.stderr)

        for assignment in result.plan.assignments:
            path_number = path_numbers.get(
                id(assignment.path),
                "?",
            )

            print(
                f"  Path {path_number}: "
                f"{assignment.drone_count} drones "
                f"{assignment.drone_ids}",
                file=sys.stderr,
            )

    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
