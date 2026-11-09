"""Stage 0: ingest and validate."""

from .loader import IngestError, IngestResult, Line, ingest

__all__ = ["IngestError", "IngestResult", "Line", "ingest"]
