"""Graph representation for the drone network."""

from collections import deque

from models.connection import Connection
from models.drone_map import DroneMap
from models.zone import Zone, ZoneType


class Graph:
    """Represent the drone network as an adjacency list."""

    def __init__(self, drone_map: DroneMap) -> None:
        """Build the graph from a parsed drone map."""
        self._drone_map = drone_map
        self._adjacency = self._build_adjacency_list()

    @property
    def zones(self) -> dict[str, Zone]:
        """Return all graph zones."""
        return self._drone_map.zones

    @property
    def connections(self) -> list[Connection]:
        """Return all graph connections."""
        return self._drone_map.connections

    @property
    def start_name(self) -> str:
        """Return the start zone name."""
        if self._drone_map.start_name is None:
            raise ValueError("Graph has no start zone.")

        return self._drone_map.start_name

    @property
    def end_name(self) -> str:
        """Return the end zone name."""
        if self._drone_map.end_name is None:
            raise ValueError("Graph has no end zone.")

        return self._drone_map.end_name

    def neighbours(self, zone_name: str) -> list[str]:
        """Return directly connected zone names."""
        if zone_name not in self._adjacency:
            raise KeyError(f"Unknown zone '{zone_name}'.")

        return list(self._adjacency[zone_name])

    def is_blocked(self, zone_name: str) -> bool:
        """Return whether a zone is blocked."""
        return self.zones[zone_name].zone_type is ZoneType.BLOCKED

    def is_reachable(
        self,
        start_name: str | None = None,
        end_name: str | None = None,
    ) -> bool:
        """Check whether one zone can reach another."""
        start = start_name or self.start_name
        end = end_name or self.end_name

        if start not in self.zones:
            raise KeyError(f"Unknown start zone '{start}'.")

        if end not in self.zones:
            raise KeyError(f"Unknown end zone '{end}'.")

        if self.is_blocked(start) or self.is_blocked(end):
            return False

        visited: set[str] = {start}
        queue: deque[str] = deque([start])

        while queue:
            current = queue.popleft()

            if current == end:
                return True

            for neighbour in self._adjacency[current]:
                if neighbour in visited:
                    continue

                if self.is_blocked(neighbour):
                    continue

                visited.add(neighbour)
                queue.append(neighbour)

        return False

    def get_connection(
        self,
        zone_a: str,
        zone_b: str,
    ) -> Connection:
        """Return the connection between two zones."""
        connection_key = frozenset((zone_a, zone_b))

        for connection in self.connections:
            if connection.key == connection_key:
                return connection

        raise KeyError(
            f"No connection exists between '{zone_a}' and '{zone_b}'."
        )

    def movement_cost(self, destination_name: str) -> int:
        """Return the turn cost of entering a zone."""
        if destination_name not in self.zones:
            raise KeyError(f"Unknown zone '{destination_name}'.")

        zone = self.zones[destination_name]

        if zone.zone_type is ZoneType.BLOCKED:
            raise ValueError(
                f"Blocked zone '{destination_name}' cannot be entered."
            )

        if zone.zone_type is ZoneType.RESTRICTED:
            return 2

        return 1

    def _build_adjacency_list(self) -> dict[str, list[str]]:
        """Build adjacency data from all connections."""
        adjacency: dict[str, list[str]] = {
            zone_name: []
            for zone_name in self.zones
        }

        for connection in self.connections:
            adjacency[connection.zone_a].append(connection.zone_b)
            adjacency[connection.zone_b].append(connection.zone_a)

        return adjacency
