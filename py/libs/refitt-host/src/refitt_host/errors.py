"""Domain-specific errors with actionable messages."""

class RefittHostError(RuntimeError):
    """Base error for host association."""

class CatalogQueryError(RefittHostError):
    """The required host-catalog query could not be completed."""

class CatalogSchemaError(RefittHostError):
    """The catalog lacks a required, non-sentinel morphology field."""
