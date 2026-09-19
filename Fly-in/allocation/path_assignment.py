from dataclasses import dataclass

from pathfinding.path_result import PathResult


@dataclass(frozen=True, slots=True)
class PathAssignment:

    path: PathResult
    drone_ids: list[int]

    @property
    def drone_count(self) -> int:
        return len(self.drone_ids)
