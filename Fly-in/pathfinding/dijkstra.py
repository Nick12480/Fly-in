"""Dijkstra pathfinding for the drone graph."""

import heapq

from models.graph import Graph
from pathfinding.path_result import PathResult


class DijkstraPathFinder:
    """Find the cheapest valid path through the graph."""

    def __init__(self, graph: Graph) -> None:
        """Store the graph used for pathfinding."""
        self._graph = graph

    def find_shortest_path(
        self,
        start_name: str | None = None,
        end_name: str | None = None,
    ) -> PathResult:
        """Find the cheapest path between two zones.

        Args:
            start_name: Optional custom start zone.
            end_name: Optional custom end zone.

        Returns:
            Cheapest path and its total movement cost.

        Raises:
            KeyError: If start or end does not exist.
            ValueError: If no valid path exists.
        """
        start = start_name or self._graph.start_name
        end = end_name or self._graph.end_name

        if start not in self._graph.zones:
            raise KeyError(f"Unknown start zone '{start}'.")

        if end not in self._graph.zones:
            raise KeyError(f"Unknown end zone '{end}'.")

        if self._graph.is_blocked(start):
            raise ValueError(
                f"Start zone '{start}' is blocked."
            )

        if self._graph.is_blocked(end):
            raise ValueError(
                f"End zone '{end}' is blocked."
            )

        distances: dict[str, float] = {
            zone_name: float("inf")
            for zone_name in self._graph.zones
        }

        previous: dict[str, str | None] = {
            zone_name: None
            for zone_name in self._graph.zones
        }

        distances[start] = 0.0

        queue: list[tuple[float, str]] = [(0.0, start)]

        while queue:
            current_cost, current_name = heapq.heappop(queue)

            if current_cost > distances[current_name]:
                continue

            if current_name == end:
                break

            for neighbour in self._graph.neighbours(current_name):
                if self._graph.is_blocked(neighbour):
                    continue

                movement_cost = self._graph.movement_cost(neighbour)
                new_cost = current_cost + movement_cost

                if new_cost >= distances[neighbour]:
                    continue

                distances[neighbour] = new_cost
                previous[neighbour] = current_name

                heapq.heappush(
                    queue,
                    (new_cost, neighbour),
                )

        if distances[end] == float("inf"):
            raise ValueError(
                f"No valid path exists from '{start}' to '{end}'."
            )

        path = self._reconstruct_path(
            previous=previous,
            start=start,
            end=end,
        )

        return PathResult(
            zones=path,
            total_cost=int(distances[end]),
        )

    @staticmethod
    def _reconstruct_path(
        previous: dict[str, str | None],
        start: str,
        end: str,
    ) -> list[str]:
        """Reconstruct a path from predecessor data."""
        path: list[str] = []
        current: str | None = end

        while current is not None:
            path.append(current)

            if current == start:
                break

            current = previous[current]

        path.reverse()

        if not path or path[0] != start:
            raise ValueError(
                f"Could not reconstruct path from '{start}' to '{end}'."
            )

        return path
