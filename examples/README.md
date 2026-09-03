# Examples

Short, runnable shapes. Each needs a `gspread` client you have authenticated
yourself. This library does not own authentication.

```python
import gspread
from sheets_fidelity import (
    read_formatting, read_values, write_values, batch_format,
)

gc = gspread.oauth()                       # or service_account(), or authorize()
sh = gc.open_by_key(SPREADSHEET_ID)
ws = sh.worksheet("Q3 Plan")
```

## Take a structure snapshot before you touch anything

The cheapest useful thing in this repo. Structure is per-sheet, not per-cell, so
this is safe on a spreadsheet of any size, and it is the layer that vanishes
silently.

```python
before = read_formatting(sh)["structure"]

sheet = before["sheets"][0]
print("frozen rows:", sheet["properties"]["gridProperties"].get("frozenRowCount", 0))
print("conditional rules:", len(sheet.get("conditionalFormats", [])))
print("merges:", len(sheet.get("merges", [])))
print("protected ranges:", len(sheet.get("protectedRanges", [])))
```

Run it again after your write and diff the counts. If a number dropped, the
write destroyed something.

## Prove a column really holds live formulas

The trap: `FORMULA` returns the same `"=SUM(A1:A9)"` string whether the cell is
a live formula or text that merely looks like one. Only `UNFORMATTED_VALUE` can
tell them apart. A live formula returns its computed value; text returns the
literal string starting with `=`.

```python
source = read_values(ws, "C2:C40", render="FORMULA")
actual = read_values(ws, "C2:C40", render="UNFORMATTED_VALUE")

for row, (src, val) in enumerate(zip(source, actual), start=2):
    looks_like_formula = str(src[0]).startswith("=")
    is_dead_text = looks_like_formula and str(val[0]).startswith("=")
    if is_dead_text:
        print(f"C{row} is text pretending to be a formula")
```

This is the single most common way a round trip fails quietly: formulas read out
as strings, get stored as strings, and get written back with `RAW`. At that point
the sheet still looks right and computes nothing.

## Write one range and nothing else

A ranged update leaves merges, validation, notes, banding and conditional rules
alone, because it never clears anything outside the range you name.

```python
write_values(ws, "C2:C40", [[v] for v in values])          # USER_ENTERED
write_values(ws, "A2:A40", ids, value_input_option="RAW")  # keeps "0012" as "0012"
```

`USER_ENTERED` parses like a person typing: a leading `=` becomes a live
formula, dates and percentages are interpreted. `RAW` is for values that must
survive coercion intact.

## Read per-cell formatting, bounded

Cell-level reads are the expensive kind, so the range is required rather than
optional. An unbounded grid fetch on a real working sheet returns hundreds of
megabytes and reads like a hang.

```python
detail = read_formatting(sh, "Q3 Plan!A1:H40")["cells"]
```

The tab name is quoted for you. A tab called `Q3 Plan` or `Sales (EU)` is a 400
without quoting, and one with an apostrophe needs it doubled.

## Change structure, not values

Everything that is not a cell value goes through `batch_format`. The `fields`
mask on each request is the important part: it is what stops a partial update
from blanking every property you did not mention.

```python
batch_format(sh, [
    {"updateSheetProperties": {
        "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount"}},
    {"repeatCell": {
        "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
        "fields": "userEnteredFormat.textFormat.bold"}},
])
```

Note what that second request does *not* say. Because `fields` names only
`textFormat.bold`, the background colour, borders and number format of those
cells survive. Widen the mask to `userEnteredFormat` and they would not.
