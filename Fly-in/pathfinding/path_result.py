from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PathResult:

    zones: list[str]
    total_cost: int
