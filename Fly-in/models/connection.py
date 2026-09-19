"""Connection data model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Connection:
    """Represent a bidirectional connection between two zones."""

    zone_a: str
    zone_b: str
    max_capacity: int = 1

    @property
    def key(self) -> frozenset[str]:
        """Return an order-independent connection identifier."""
        return frozenset((self.zone_a, self.zone_b))
