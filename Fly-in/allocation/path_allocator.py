import heapq

from allocation.path_assignment import PathAssignment
from pathfinding.path_result import PathResult


class PathAllocator:
    """Assign drones to paths.

        Each next drone is assigned to the path with the currently lowest
        estimated completion score.

        Args:
            drone_count: Number of drones to distribute.
            paths: Valid paths ordered by pathfinding cost.

        Returns:
            One assignment per used path.

        Raises:
            ValueError: If drone_count is invalid or no paths are available.
        """

    def allocate(self, drone_count: int,
                 paths: list[PathResult],
                 ) -> list[PathAssignment]:

        if drone_count <= 0:
            raise ValueError("drone_count must be positive.")
        if not paths:
            raise ValueError("At least one path is required.")

        self._vallidate_paths(paths)

        assignments: list[list[int]] = [
            []
            for _ in paths
        ]

        queue: list[tuple[int, int]] = []

        for path_index, path in enumerate(paths):
            initial_score = self._calculate_score(
                path=path,
                assigned_count=0.
            )
            heapq.heappush(
                queue,
                (initial_score, path_index),
            )

        for drone_id in range(1, drone_count + 1):
            _, path_index = heapq.heappop(queue)

            assignments[path_index].append(drone_id)

            new_score = self._calculate_score(
                path=paths[path_index],
                assigned_count=len(assignments[path_index]),
            )

            heapq.heappush(
                queue,
                (new_score, path_index),
            )
        result: list[PathAssignment] = []

        for path, drone_ids in zip(paths, assignments):
            if not drone_ids:
                continue

            result.append(
                PathAssignment(
                    path=path,
                    drone_ids=drone_ids,
                )
            )
        return result

    @staticmethod
    def _calculate_score(path: PathResult, assigned_count: int,) -> int:
        """Estimate when the next drone would complete this path.

        The first drone completes after total_cost turns. Each additional
        drone adds one estimated turn of pipeline delay.
        """
        return path.total_cost + assigned_count

    @staticmethod
    def _vallidate_paths(paths: list[PathResult]) -> None:
        """Validate path data befor allocation."""
        for path in paths:
            if not path.zones:
                raise ValueError("Paths cannot be empty.")
            if path.total_cost < 0:
                raise ValueError("Path cost cannot be negative.")
