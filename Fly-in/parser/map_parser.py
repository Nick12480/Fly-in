"""Parser for Fly-in filse."""

from pathlib import Path

from models.connection import Connection
from models.drone_map import DroneMap
from models.graph import Graph
from models.zone import Zone, ZoneRole, ZoneType
from parser.exceptions import (
    DuplicateConnectionError,
    DuplicateZoneError,
    InvalidMetadataError,
    InvalidSyntaxError,
    MapParserError,
    UnknownZoneError,
    UnreachableEndError
)


class MapParser:
    """Parse and validate a Fly-in map file."""
    def __init__(self):
        self._drone_map: DroneMap | None = None
        self._connection_keys: set[frozenset[str]] = set()

    def parse_file(self, file_path: str | Path) -> DroneMap:
        """Parse a map file.

        Args:
            file_path to the input map.
        Returns:
            Fully parsed and validated drone map.

        Raises:
            MapParserError: If the map is invalid.
            OSError: If the file cannot be read.
        """
        path = Path(file_path)

        with path.open("r", encoding="utf-8") as file:
            lines = file.readlines()

        return self.parse_lines(lines)

    def parse_lines(self, lines: list[str]) -> DroneMap:
        self._drone_map = None
        self._connection_keys.clear()

        relevant_linse = self._clean_lines(lines)

        if not relevant_linse:
            raise InvalidSyntaxError("Input file is empty.")

        first_line_number, first_line = relevant_linse[0]
        drone_count = self._parse_drone_count(
            first_line,
            first_line_number,
        )

        self._drone_map = DroneMap(drone_count=drone_count)

        for line_number, line in relevant_linse[1:]:
            self._parse_line(line, line_number)

        self._validate_complete_map()
        return self._drone_map

    @staticmethod
    def _clean_lines(lines: list[str]) -> list[tuple[int, str]]:
        """Remove comments and blank linse while perserwing line numbers."""
        cleaned: list[tuple[int, str]] = []

        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.split("#", maxsplit=1)[0].strip()

            if line:
                cleaned.append((line_number, line))

        return cleaned

    @staticmethod
    def _parse_drone_count(line: str, line_number: int) -> int:

        prefix = "nb_drones:"

        if not line.startswith(prefix):
            raise InvalidSyntaxError(
                f"Line {line_number}: first line must define nb_drones."
            )

        value = line[len(prefix):].strip()

        try:
            drone_count = int(value)
        except ValueError as e:
            raise InvalidSyntaxError(
                f"Line {line_number}: drone count must be an integer."
            ) from e

        if drone_count <= 0:
            raise InvalidSyntaxError(
                f"Line {line_number}: drone count must be positive."
            )

        return drone_count

    def _parse_line(self, line: str, line_number: int) -> None:
        if line.startswith("start_hub:"):
            self._parse_zone(line, line_number, ZoneRole.START)
        elif line.startswith("end_hub:"):
            self._parse_zone(line, line_number, ZoneRole.END)
        elif line.startswith("hub:"):
            self._parse_zone(line, line_number, ZoneRole.REGULAR)
        elif line.startswith("connection:"):
            self._parse_connection(line, line_number)
        else:
            raise InvalidSyntaxError(
                f"Line {line_number}: unknown declaration."
            )

    def _parse_zone(
            self,
            line: str,
            line_number: int,
            role: ZoneRole,
         ) -> None:
        """Parse and store a zone declaration."""
        drone_map = self._require_map()

        if role is ZoneRole.START:
            prefix = "start_hub:"
        elif role is ZoneRole.END:
            prefix = "end_hub:"
        else:
            prefix = "hub:"

        content = line[len(prefix):].strip()
        main_content, metadata = self._split_metadata(content, line_number)

        parts = main_content.split()

        if len(parts) != 3:
            raise InvalidSyntaxError(
                f"Line {line_number}: a zone requires a name, x and y."
            )

        name, x_value, y_value = parts

        self._validate_zone_name(name, line_number)

        if name in drone_map.zones:
            raise DuplicateZoneError(
                f"Line {line_number}: duplicate zone '{name}'."
            )

        try:
            x = int(x_value)
            y = int(y_value)
        except ValueError as error:
            raise InvalidSyntaxError(
                f"Line {line_number}: zone coordinates must be integers."
            ) from error

        if role is ZoneRole.START and drone_map.start_name is not None:
            raise InvalidSyntaxError(
                f"Line {line_number}: multiple start_hub declarations."
            )

        if role is ZoneRole.END and drone_map.end_name is not None:
            raise InvalidSyntaxError(
                f"Line {line_number}: multiple end_hub declarations."
            )

        zone_type = self._parse_zone_type(metadata, line_number)
        color = metadata.get("color")
        max_drones = self._parse_positive_integer(
            metadata.get("max_drones", "1"),
            "max_drones",
            line_number,
        )

        unknown_keys = set(metadata) - {
            "zone",
            "color",
            "max_drones",
        }

        if unknown_keys:
            unknown = ", ".join(sorted(unknown_keys))
            raise InvalidMetadataError(
                f"Line {line_number}: unknown zone metadata: {unknown}."
            )

        zone = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            role=role,
        )

        drone_map.zones[name] = zone

        if role is ZoneRole.START:
            drone_map.start_name = name
        elif role is ZoneRole.END:
            drone_map.end_name = name

    def _parse_connection(
        self,
        line: str,
        line_number: int,
    ) -> None:
        """Parse and store a bidirectional connection."""
        drone_map = self._require_map()

        prefix = "connection:"
        content = line[len(prefix):].strip()
        main_content, metadata = self._split_metadata(content, line_number)

        if main_content.count("-") != 1:
            raise InvalidSyntaxError(
                f"Line {line_number}: connection must use zone1-zone2."
            )

        zone_a, zone_b = main_content.split("-", maxsplit=1)

        if not zone_a or not zone_b:
            raise InvalidSyntaxError(
                f"Line {line_number}: connection contains an empty zone name."
            )

        if zone_a == zone_b:
            raise InvalidSyntaxError(
                f"Line {line_number}: a zone cannot connect to itself."
            )

        for zone_name in (zone_a, zone_b):
            if zone_name not in drone_map.zones:
                raise UnknownZoneError(
                    f"Line {line_number}: unknown zone '{zone_name}'."
                )

        unknown_keys = set(metadata) - {"max_link_capacity"}

        if unknown_keys:
            unknown = ", ".join(sorted(unknown_keys))
            raise InvalidMetadataError(
                f"Line {line_number}: unknown connection metadata: "
                f"{unknown}."
            )

        max_capacity = self._parse_positive_integer(
            metadata.get("max_link_capacity", "1"),
            "max_link_capacity",
            line_number,
        )

        connection_key = frozenset((zone_a, zone_b))

        if connection_key in self._connection_keys:
            raise DuplicateConnectionError(
                f"Line {line_number}: duplicate connection "
                f"'{zone_a}-{zone_b}'."
            )

        self._connection_keys.add(connection_key)
        drone_map.connections.append(
            Connection(
                zone_a=zone_a,
                zone_b=zone_b,
                max_capacity=max_capacity,
            )
        )

    @staticmethod
    def _split_metadata(
        content: str,
        line_number: int,
    ) -> tuple[str, dict[str, str]]:
        """Separate declaration content from optional metadata."""
        if "[" not in content:
            if "]" in content:
                raise InvalidSyntaxError(
                    f"Line {line_number}: unexpected closing bracket."
                )

            return content.strip(), {}

        if not content.endswith("]"):
            raise InvalidSyntaxError(
                f"Line {line_number}: metadata bracket is not closed."
            )

        main_content, metadata_content = content.split("[", maxsplit=1)
        metadata_content = metadata_content[:-1].strip()

        metadata: dict[str, str] = {}

        if not metadata_content:
            return main_content.strip(), metadata

        for item in metadata_content.split():
            if "=" not in item:
                raise InvalidMetadataError(
                    f"Line {line_number}: invalid metadata '{item}'."
                )

            key, value = item.split("=", maxsplit=1)

            if not key or not value:
                raise InvalidMetadataError(
                    f"Line {line_number}: invalid metadata '{item}'."
                )

            if key in metadata:
                raise InvalidMetadataError(
                    f"Line {line_number}: duplicate metadata key '{key}'."
                )

            metadata[key] = value

        return main_content.strip(), metadata

    @staticmethod
    def _validate_zone_name(name: str, line_number: int) -> None:
        """Validate a zone name."""
        if "-" in name:
            raise InvalidSyntaxError(
                f"Line {line_number}: zone names cannot contain dashes."
            )

        if any(character.isspace() for character in name):
            raise InvalidSyntaxError(
                f"Line {line_number}: zone names cannot contain spaces."
            )

        if not name:
            raise InvalidSyntaxError(
                f"Line {line_number}: zone name cannot be empty."
            )

    @staticmethod
    def _parse_zone_type(
        metadata: dict[str, str],
        line_number: int,
    ) -> ZoneType:
        """Parse the zone type metadata."""
        value = metadata.get("zone", ZoneType.NORMAL.value)

        try:
            return ZoneType(value)
        except ValueError as error:
            allowed = ", ".join(zone_type.value for zone_type in ZoneType)
            raise InvalidMetadataError(
                f"Line {line_number}: invalid zone type '{value}'. "
                f"Allowed values: {allowed}."
            ) from error

    @staticmethod
    def _parse_positive_integer(
        value: str,
        field_name: str,
        line_number: int,
    ) -> int:
        """Parse a positive integer metadata value."""
        try:
            number = int(value)
        except ValueError as error:
            raise InvalidMetadataError(
                f"Line {line_number}: {field_name} must be an integer."
            ) from error

        if number <= 0:
            raise InvalidMetadataError(
                f"Line {line_number}: {field_name} must be positive."
            )

        return number

    def _validate_complete_map(self) -> None:
        """Validate global map requirements."""
        drone_map = self._require_map()

        if drone_map.start_name is None:
            raise MapParserError(
                "Map does not contain a start_hub."
            )

        if drone_map.end_name is None:
            raise MapParserError(
                "Map does not contain an end_hub."
            )

        graph = Graph(drone_map)

        if not graph.is_reachable():
            raise UnreachableEndError(
                "No valid path exists from start_hub to end_hub."
            )

    def _require_map(self) -> DroneMap:

        if self._drone_map is None:
            raise RuntimeError("Parser has not been initialized.")

        return self._drone_map
