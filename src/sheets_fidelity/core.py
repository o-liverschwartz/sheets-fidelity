"""Reading and writing Google Sheets without losing what is already there.

A spreadsheet is several overlapping systems wearing one costume: cell values,
cell formatting, and sheet structure. The API returns them through different
fields, at wildly different costs, and a write that ignores the distinction
quietly destroys work nobody asked you to touch.

This module is the small, boring core of getting that right:

    read_values     the value layer, and how to prove what a cell really holds
    read_formatting the format and structure layers, at the right cost
    write_values    a write that touches only the range you named
    batch_format    the structural write counterpart

Plus the pure helpers those depend on, which is where the bugs actually live:
A1 quoting, bounded-range validation, and column letters.

Takes a gspread client or spreadsheet you already built. Auth is deliberately
not this module's business.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

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


class RangeError(ValueError):
    """A range that would cost more than the caller meant to spend, or that the
    API would reject."""


# ---------------------------------------------------------------------------
# Field masks
# ---------------------------------------------------------------------------
# The single most useful thing to know about spreadsheets.get: the cost of a
# call is decided entirely by the fields you ask for, and the two useful sets
# differ by orders of magnitude.
#
# Structure is per-sheet: a handful of objects however big the grid is. Safe to
# fetch unconditionally.
FIELDS_STRUCTURE = ",".join([
    "spreadsheetId",
    "properties.title",
    "namedRanges",
    "sheets.properties",          # includes gridProperties.frozenRow/ColumnCount, tabColor
    "sheets.conditionalFormats",
    "sheets.protectedRanges",
    "sheets.bandedRanges",
    "sheets.merges",
    "sheets.rowGroups",
    "sheets.columnGroups",
])

# Cells are per-cell. An unbounded grid fetch on a real working sheet returns
# hundreds of megabytes, so this set is only ever used with an explicit range.
FIELDS_CELLS = ",".join([
    "sheets.properties.sheetId",
    "sheets.properties.title",
    "sheets.data.startRow",
    "sheets.data.startColumn",
    "sheets.data.rowData.values.userEnteredFormat",
    "sheets.data.rowData.values.dataValidation",
    "sheets.data.rowMetadata.pixelSize",
    "sheets.data.columnMetadata.pixelSize",
])

RENDER_OPTIONS = ("FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA")
INPUT_OPTIONS = ("USER_ENTERED", "RAW")


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def col_letter(col_index: int) -> str:
    """1-based column index to letters. 1 -> A, 26 -> Z, 27 -> AA."""
    if col_index < 1:
        raise ValueError("column index is 1-based")
    out = ""
    while col_index > 0:
        col_index, rem = divmod(col_index - 1, 26)
        out = chr(65 + rem) + out
    return out


def quote_a1(cell_range: str) -> str:
    """Single-quote the sheet name in an A1 range, if it needs it.

    A tab called `Q3 Plan` or `Sales (EU)` is a 400 unless the name is quoted,
    and a tab with an apostrophe needs that apostrophe doubled. Almost every
    hand-made spreadsheet has tab names like this, so quote centrally rather
    than expecting each caller to remember.

        quote_a1("Q3 Plan!A1:H40")   -> "'Q3 Plan'!A1:H40"
        quote_a1("Bob's Tab!A1:B2")  -> "'Bob''s Tab'!A1:B2"
    """
    if "!" not in cell_range:
        return cell_range
    tab, _, span = cell_range.rpartition("!")
    if tab.startswith("'") and tab.endswith("'") and len(tab) >= 2:
        return cell_range
    return "'%s'!%s" % (tab.replace("'", "''"), span)


def validate_bounded_range(cell_range: str) -> str:
    """Require a range that names a tab and has an end. Returns it, quoted.

    Cell-level reads are the expensive kind. `Sheet1` or `Sheet1!A1` will happily
    be interpreted as "the whole grid", and on a real sheet that is a response
    large enough to look like a hang. Refuse it here, before the network call,
    where the error can say why.
    """
    if "!" not in cell_range or ":" not in cell_range:
        raise RangeError(
            "cell-level reads need a bounded A1 range including the tab, "
            'e.g. "Sheet1!A1:H40". Got: %r' % cell_range
        )
    return quote_a1(cell_range)


# ---------------------------------------------------------------------------
# The value layer
# ---------------------------------------------------------------------------

def read_values(worksheet, cell_range: str = "", render: str = "FORMATTED_VALUE"):
    """Read cell values as a 2D list.

    `render` picks which of the three value layers you get back, and the choice
    matters more than it looks:

    FORMATTED_VALUE
        What a person sees on screen. Dates as displayed, numbers with their
        thousands separators and currency symbols. A string, always.

    UNFORMATTED_VALUE
        The underlying value. This is the only way to prove what a cell really
        holds: a live formula returns its computed value, while text that merely
        looks like a formula returns the literal string starting with "=".

    FORMULA
        The formula source. Note the trap -- this returns the same "=SUM(A1:A9)"
        string for a live formula and for a cell containing that text, so it can
        never be used as evidence that a formula is live. Use UNFORMATTED_VALUE
        for that, and FORMULA only when you intend to copy the source somewhere.
    """
    if render not in RENDER_OPTIONS:
        raise ValueError("render must be one of %r, got %r" % (RENDER_OPTIONS, render))
    if cell_range:
        return worksheet.get(cell_range, value_render_option=render)
    return worksheet.get_all_values(value_render_option=render)


def write_values(
    worksheet,
    cell_range: str,
    values: Sequence[Sequence[Any]],
    value_input_option: str = "USER_ENTERED",
) -> int:
    """Write a 2D block into one range, and touch nothing else.

    A ranged update is the safe primitive. It leaves merged cells, conditional
    formatting, data validation, notes and banding alone, because it never
    clears anything outside the range you named. Prefer it to anything that
    rewrites a whole sheet.

    value_input_option:
        USER_ENTERED  parsed as if a person typed it. A string starting with "="
                      becomes a live formula; dates and percentages are
                      interpreted. Almost always what you want.
        RAW           stored exactly as given. For values that must survive
                      coercion, like an id "0012" that has to keep its zeros.
    """
    if value_input_option not in INPUT_OPTIONS:
        raise ValueError(
            "value_input_option must be one of %r, got %r" % (INPUT_OPTIONS, value_input_option)
        )
    worksheet.update(
        values=values,
        range_name=cell_range,
        value_input_option=value_input_option,
    )
    return len(values)


# ---------------------------------------------------------------------------
# The format and structure layers
# ---------------------------------------------------------------------------

def read_formatting(spreadsheet, cell_range: str = "") -> dict:
    """Read applied formatting: the counterpart to a formatting write.

    Without `cell_range`, returns structure only -- frozen panes, tab colours,
    conditional formatting rules, protected ranges, banding, merges, row and
    column groups, named ranges. Cheap, and safe on a sheet of any size.

    With `cell_range` (bounded, e.g. "Sheet1!A1:H40"), additionally returns
    per-cell userEnteredFormat, dataValidation, and row/column pixel sizes for
    that range. This half is expensive, which is why the range is required
    rather than optional-with-a-default.
    """
    out = {"structure": spreadsheet.fetch_sheet_metadata(params={"fields": FIELDS_STRUCTURE})}
    if cell_range:
        out["cells"] = spreadsheet.fetch_sheet_metadata(params={
            "fields": FIELDS_CELLS,
            "ranges": validate_bounded_range(cell_range),
            "includeGridData": "true",
        })
    return out


def batch_format(spreadsheet, requests: Iterable[dict]) -> int:
    """Send raw batchUpdate requests -- the structural write.

    Values go through write_values; everything else about a sheet is changed
    here. A few that come up constantly:

        freeze the header row
            {"updateSheetProperties": {
                "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount"}}

        bold a range
            {"repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold"}}

    The `fields` mask on each request is the part worth reading twice: it is
    what stops a partial format update from blanking every property you did not
    mention.
    """
    requests = list(requests)
    if not requests:
        return 0
    spreadsheet.batch_update({"requests": requests})
    return len(requests)
