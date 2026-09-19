"""High-level orchestration of the complete drone simulation."""

from dataclasses import dataclass

from allocation import PathAllocator, PathAssignment
from models import DroneMap, Graph
from pathfinding import PathFinder, PathResult

from .drone import Drone
from .output_formatter import OutputFormatter
from .scheduler import Scheduler, TurnResult
from .simulation_state import SimulationState


@dataclass(slots=True)
class SimulationPlan:
    """Prepared objects required to run a simulation."""

    graph: Graph
    paths: list[PathResult]
    assignments: list[PathAssignment]
    state: SimulationState


@dataclass(slots=True)
class SimulationResult:
    """Final result of a completed simulation."""

    plan: SimulationPlan
    turns: list[TurnResult]
    output: str

    @property
    def state(self) -> SimulationState:
        """Return the final simulation state."""
        return self.plan.state

    @property
    def total_turns(self) -> int:
        """Return the total number of simulated turns."""
        return len(self.turns)


class Simulation:
    """Coordinate pathfinding, allocation and scheduling."""

    def __init__(
        self,
        drone_map: DroneMap,
        max_paths: int | None = None,
    ) -> None:
        """Initialize a simulation."""
        if drone_map.drone_count <= 0:
            raise ValueError(
                "drone_count must be positive."
            )

        if max_paths is not None and max_paths <= 0:
            raise ValueError(
                "max_paths must be positive."
            )

        self._drone_map = drone_map
        self._max_paths = (
            drone_map.drone_count
            if max_paths is None
            else max_paths
        )

    def prepare(self) -> SimulationPlan:
        """Create a simulation plan using all candidate paths."""
        graph = Graph(self._drone_map)

        paths = PathFinder(graph).find_paths(
            max_paths=self._max_paths,
        )

        assignments = PathAllocator().allocate(
            drone_count=self._drone_map.drone_count,
            paths=paths,
        )

        return self._build_plan(
            graph=graph,
            paths=paths,
            assignments=assignments,
        )

    def run(
        self,
        max_turns: int = 10_000,
    ) -> SimulationResult:
        """Find and execute the fastest tested plan."""
        graph = Graph(self._drone_map)

        paths = PathFinder(graph).find_paths(
            max_paths=self._max_paths,
        )

        plan, turns = self._find_best_plan(
            graph=graph,
            paths=paths,
            max_turns=max_turns,
        )

        output = OutputFormatter().format_simulation(
            turns,
        )

        return SimulationResult(
            plan=plan,
            turns=turns,
            output=output,
        )

    def _create_drones(
        self,
        assignments: list[PathAssignment],
        graph: Graph,
    ) -> dict[int, Drone]:
        """Create drone objects from path assignments."""
        drones: dict[int, Drone] = {}

        for assignment in assignments:
            self._validate_assignment_path(
                assignment=assignment,
                graph=graph,
            )

            for drone_id in assignment.drone_ids:
                if drone_id in drones:
                    raise RuntimeError(
                        f"Drone D{drone_id} was assigned more than once."
                    )

                drones[drone_id] = Drone(
                    drone_id=drone_id,
                    path=assignment.path,
                    current_zone=graph.start_name,
                )

        expected_ids = set(
            range(1, self._drone_map.drone_count + 1)
        )
        actual_ids = set(drones)

        if actual_ids != expected_ids:
            missing_ids = sorted(expected_ids - actual_ids)
            unexpected_ids = sorted(actual_ids - expected_ids)

            raise RuntimeError(
                "Invalid path allocation. "
                f"Missing drone IDs: {missing_ids}; "
                f"unexpected drone IDs: {unexpected_ids}."
            )

        return drones

    @staticmethod
    def _validate_assignment_path(
        assignment: PathAssignment,
        graph: Graph,
    ) -> None:
        """Validate that a path connects start and destination."""
        zones = assignment.path.zones

        if not zones:
            raise RuntimeError(
                "An assigned path cannot be empty."
            )

        if zones[0] != graph.start_name:
            raise RuntimeError(
                "An assigned path must begin at the start zone."
            )

        if zones[-1] != graph.end_name:
            raise RuntimeError(
                "An assigned path must end at the destination zone."
            )

    def _build_plan(
        self,
        graph: Graph,
        paths: list[PathResult],
        assignments: list[PathAssignment],
         ) -> SimulationPlan:
        """Create a fresh simulation plan."""
        drones = self._create_drones(
            assignments=assignments,
            graph=graph,
        )

        state = SimulationState(
            graph=graph,
            drones=drones,
        )

        return SimulationPlan(
            graph=graph,
            paths=paths,
            assignments=assignments,
            state=state,
        )

    def _find_best_plan(
        self,
        graph: Graph,
        paths: list[PathResult],
        max_turns: int,
    ) -> tuple[SimulationPlan, list[TurnResult]]:
        """Find the fastest allocation among path prefixes."""
        if not paths:
            raise RuntimeError(
                "No path from start to destination was found."
            )

        best_plan: SimulationPlan | None = None
        best_turns: list[TurnResult] | None = None
        best_score: tuple[int, int, int] | None = None
        last_error: RuntimeError | None = None

        allocator = PathAllocator()

        maximum_path_count = min(
            len(paths),
            self._drone_map.drone_count,
        )

        for path_count in range(
            1,
            maximum_path_count + 1,
        ):
            selected_paths = paths[:path_count]

            assignments = allocator.allocate(
                drone_count=self._drone_map.drone_count,
                paths=selected_paths,
            )

            plan = self._build_plan(
                graph=graph,
                paths=selected_paths,
                assignments=assignments,
            )

            try:
                turns = Scheduler().run_until_complete(
                    state=plan.state,
                    max_turns=max_turns,
                )
            except RuntimeError as error:
                if "maximum number of turns" not in str(error):
                    raise

                last_error = error
                continue

            total_assignment_cost = sum(
                assignment.path.total_cost
                * assignment.drone_count
                for assignment in assignments
            )

            score = (
                len(turns),
                len(assignments),
                total_assignment_cost,
            )

            if best_score is None or score < best_score:
                best_score = score
                best_plan = plan
                best_turns = turns

        if best_plan is None or best_turns is None:
            if last_error is not None:
                raise last_error

            raise RuntimeError(
                "No valid path allocation completed the simulation."
            )

        return best_plan, best_turns
