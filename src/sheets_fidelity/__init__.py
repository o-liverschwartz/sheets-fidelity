"""Read and write Google Sheets without silently destroying what is already there.

The public surface deliberately mirrors the three layers a spreadsheet actually
has, rather than hiding them behind one sync_sheet() that guesses.
"""
from .core import (
    FIELDS_CELLS,
    FIELDS_STRUCTURE,
    INPUT_OPTIONS,
    RENDER_OPTIONS,
    RangeError,
    batch_format,
    col_letter,
    quote_a1,
    read_formatting,
    read_values,
    validate_bounded_range,
    write_values,
)

__version__ = "0.1.0"

__all__ = [
    "FIELDS_STRUCTURE",
    "FIELDS_CELLS",
    "RENDER_OPTIONS",
    "INPUT_OPTIONS",
    "RangeError",
    "col_letter",
    "quote_a1",
    "validate_bounded_range",
    "read_values",
    "read_formatting",
    "write_values",
    "batch_format",
]
