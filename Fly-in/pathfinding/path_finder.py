"""Alternative path search for the drone graph."""

import heapq

from models.graph import Graph
from pathfinding.path_result import PathResult


class PathFinder:
    """Find multiple valid paths ordered by total movement cost."""

    def __init__(self, graph: Graph) -> None:
        """Store the graph used for pathfinding."""
        self._graph = graph

    def find_paths(
        self,
        max_paths: int,
        start_name: str | None = None,
        end_name: str | None = None,
    ) -> list[PathResult]:
        """Find multiple simple paths ordered by total cost.

        Args:
            max_paths: Maximum number of paths to return.
            start_name: Optional custom start zone.
            end_name: Optional custom end zone.

        Returns:
            Valid paths sorted by total movement cost.

        Raises:
            ValueError: If max_paths is not positive or no path exists.
            KeyError: If start or end does not exist.
        """
        if max_paths <= 0:
            raise ValueError("max_paths must be positive.")

        start = start_name or self._graph.start_name
        end = end_name or self._graph.end_name

        self._validate_zone(start, "start")
        self._validate_zone(end, "end")

        queue: list[tuple[int, list[str]]] = [
            (0, [start]),
        ]
        results: list[PathResult] = []

        while queue and len(results) < max_paths:
            current_cost, current_path = heapq.heappop(queue)
            current_zone = current_path[-1]

            if current_zone == end:
                results.append(
                    PathResult(
                        zones=current_path,
                        total_cost=current_cost,
                    )
                )
                continue

            for neighbour in self._graph.neighbours(current_zone):
                if neighbour in current_path:
                    continue

                if self._graph.is_blocked(neighbour):
                    continue

                movement_cost = self._graph.movement_cost(neighbour)

                heapq.heappush(
                    queue,
                    (
                        current_cost + movement_cost,
                        current_path + [neighbour],
                    ),
                )

        if not results:
            raise ValueError(
                f"No valid path exists from '{start}' to '{end}'."
            )

        return results

    def _validate_zone(
        self,
        zone_name: str,
        role: str,
    ) -> None:
        """Validate a pathfinding endpoint."""
        if zone_name not in self._graph.zones:
            raise KeyError(
                f"Unknown {role} zone '{zone_name}'."
            )

        if self._graph.is_blocked(zone_name):
            raise ValueError(
                f"{role.capitalize()} zone '{zone_name}' is blocked."
            )
