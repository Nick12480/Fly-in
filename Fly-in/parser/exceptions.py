"""Parser-specific exceptions."""


class MapParserError(Exception):
    """Base exception for invalid map input."""


class InvalidSyntaxError(MapParserError):
    """Raised when a line does not follow the required syntax."""


class DuplicateZoneError(MapParserError):
    """Raised when a zone name appears more than once."""


class DuplicateConnectionError(MapParserError):
    """Raised when a connection appears more than once."""


class UnknownZoneError(MapParserError):
    """Raised when a connection references an unknown zone."""


class InvalidMetadataError(MapParserError):
    """Raised when metadata is invalid."""


class UnreachableEndError(MapParserError):
    """Raised when no valid path exists from start to end."""
