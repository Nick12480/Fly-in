"""Movement model for one drone action."""

from dataclasses import dataclass
from enum import Enum, auto


class MovementStatus(Enum):
    """Possible states of a movement."""

    PLANNED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass(slots=True)
class Movement:
    """Represent one drone movement between two zones."""

    drone_id: int
    source: str
    destination: str
    duration: int
    remaining_turns: int
    status: MovementStatus = MovementStatus.PLANNED

    def __post_init__(self) -> None:
        """Validate movement data."""
        if self.drone_id <= 0:
            raise ValueError("drone_id must be positive.")

        if not self.source:
            raise ValueError("source cannot be empty.")

        if not self.destination:
            raise ValueError("destination cannot be empty.")

        if self.source == self.destination:
            raise ValueError(
                "source and destination must be different."
            )

        if self.duration <= 0:
            raise ValueError("duration must be positive.")

        if self.remaining_turns <= 0:
            raise ValueError(
                "remaining_turns must be positive."
            )

        if self.remaining_turns > self.duration:
            raise ValueError(
                "remaining_turns cannot exceed duration."
            )

    @property
    def identifier(self) -> str:
        """Return the formatted drone identifier."""
        return f"D{self.drone_id}"

    @property
    def connection_key(self) -> frozenset[str]:
        """Return an order-independent connection key."""
        return frozenset((self.source, self.destination))

    @property
    def is_multi_turn(self) -> bool:
        """Return whether the movement spans multiple turns."""
        return self.duration > 1

    @property
    def is_finished(self) -> bool:
        """Return whether the movement is complete."""
        return self.status is MovementStatus.COMPLETED

    def start(self) -> None:
        """Start the movement."""
        if self.status is not MovementStatus.PLANNED:
            raise RuntimeError(
                "Only a planned movement can be started."
            )

        self.status = MovementStatus.IN_PROGRESS

    def advance(self) -> bool:
        """Advance the movement by one turn.

        Returns:
            True when the movement has completed.
        """
        if self.status is not MovementStatus.IN_PROGRESS:
            raise RuntimeError(
                "Only an in-progress movement can advance."
            )

        if self.remaining_turns <= 0:
            raise RuntimeError(
                "Movement has an invalid remaining turn count."
            )

        self.remaining_turns -= 1

        if self.remaining_turns == 0:
            self.status = MovementStatus.COMPLETED
            return True

        return False

    def cancel(self) -> None:
        """Cancel a movement that has not completed."""
        if self.status is MovementStatus.COMPLETED:
            raise RuntimeError(
                "A completed movement cannot be cancelled."
            )

        self.status = MovementStatus.CANCELLED
