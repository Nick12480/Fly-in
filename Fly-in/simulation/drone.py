"""Drone state model."""

from dataclasses import dataclass
from enum import Enum, auto

from pathfinding.path_result import PathResult


class DroneStatus(Enum):
    """Possible simulation states of a drone."""

    WAITING = auto()
    IN_ZONE = auto()
    IN_TRANSIT = auto()
    DELIVERED = auto()


@dataclass(slots=True)
class Drone:
    """Represent one drone during the simulation."""

    drone_id: int
    path: PathResult
    current_zone: str
    path_index: int = 0
    status: DroneStatus = DroneStatus.WAITING
    transit_destination: str | None = None
    remaining_transit_turns: int = 0
    waiting_turns: int = 0

    @property
    def identifier(self) -> str:
        """Return the formatted drone identifier."""
        return f"D{self.drone_id}"

    @property
    def next_zone(self) -> str | None:
        """Return the next zone on the assigned path."""
        next_index = self.path_index + 1

        if next_index >= len(self.path.zones):
            return None

        return self.path.zones[next_index]

    @property
    def is_delivered(self) -> bool:
        """Return whether the drone reached the end."""
        return self.status is DroneStatus.DELIVERED

    @property
    def is_in_transit(self) -> bool:
        """Return whether the drone is currently on a connection."""
        return self.status is DroneStatus.IN_TRANSIT

    def begin_turn(self) -> None:
        """Count one additional waiting turn."""
        if self.status is DroneStatus.WAITING:
            self.waiting_turns += 1

    def enter_zone(self, zone_name: str) -> None:
        """Move the drone into the next zone on its path."""
        expected_zone = self.next_zone

        if expected_zone != zone_name:
            raise ValueError(
                f"{self.identifier} cannot enter '{zone_name}'; "
                f"expected '{expected_zone}'."
            )

        self.path_index += 1
        self.current_zone = zone_name
        self.transit_destination = None
        self.remaining_transit_turns = 0
        self.waiting_turns = 0

        if self.path_index == len(self.path.zones) - 1:
            self.status = DroneStatus.DELIVERED
        else:
            self.status = DroneStatus.IN_ZONE

    def start_transit(
        self,
        destination: str,
        duration: int,
    ) -> None:
        """Start a multi-turn movement toward a zone."""
        if duration <= 1:
            raise ValueError(
                "Transit duration must be greater than one turn."
            )

        if self.next_zone != destination:
            raise ValueError(
                f"{self.identifier} cannot fly toward '{destination}'; "
                f"expected '{self.next_zone}'."
            )

        self.status = DroneStatus.IN_TRANSIT
        self.transit_destination = destination
        self.remaining_transit_turns = duration
        self.waiting_turns = 0

    def advance_transit(self) -> bool:
        """Advance transit by one turn.

        Returns:
            True when the drone must arrive now.
        """
        if self.status is not DroneStatus.IN_TRANSIT:
            raise RuntimeError(
                f"{self.identifier} is not in transit."
            )

        if self.remaining_transit_turns <= 0:
            raise RuntimeError(
                f"{self.identifier} has invalid transit state."
            )

        self.remaining_transit_turns -= 1
        return self.remaining_transit_turns == 0

    def wait(self) -> None:
        """Mark the drone as waiting."""
        if self.status is DroneStatus.DELIVERED:
            raise RuntimeError(
                f"{self.identifier} is already delivered."
            )

        if self.status is DroneStatus.IN_TRANSIT:
            raise RuntimeError(
                f"{self.identifier} cannot wait while in transit."
            )

        self.status = DroneStatus.WAITING
