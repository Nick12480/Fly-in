"""Zone data model."""

from dataclasses import dataclass
from enum import Enum


class ZoneType(str, Enum):
    """Supported zone types."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class ZoneRole(str, Enum):
    """Role of a zone."""

    START = "start"
    END = "end"
    REGULAR = "regular"


@dataclass(frozen=True, slots=True)
class Zone:
    """Represent a zone in the network."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    role: ZoneRole = ZoneRole.REGULAR
