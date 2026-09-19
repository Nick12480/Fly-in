"""Parsed drone map model."""

from dataclasses import dataclass, field

from models.zone import Zone
from models.connection import Connection


@dataclass(slots=True)
class DroneMap:
    """Contain the complete parsed drone network."""
    drone_count: int
    zones: dict[str, Zone] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
    start_name: str | None = None
    end_name: str | None = None

    @property
    def start_zone(self) -> Zone:
        """Return the unique start zone"""
        if self.start_name is None:
            raise ValueError("Start zone is not defined.")

        return self.zones[self.start_name]

    @property
    def end_zone(self) -> Zone:
        """Return the unique end zone"""
        if self.end_name is None:
            raise ValueError("End zone is nit defined.")

        return self.zones[self.end_name]
