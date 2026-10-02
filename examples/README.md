# Examples

Short shapes. Each needs a `gspread` client you have authenticated yourself and a
spreadsheet you own. `demo_offline.py` runs with neither.

```python
import gspread
from sheets_fidelity import (
    read_formatting, read_values, write_values, batch_format,
)

gc = gspread.oauth()                       # or service_account(), or authorize()
sh = gc.open_by_key("your-spreadsheet-id")
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

Take it again after your write and compare:

```python
from sheets_fidelity import diff_structure

after = read_formatting(sh)["structure"]
print(diff_structure(before, after))        # {} when nothing was lost
```

## Prove a column really holds live formulas

The trap: `FORMULA` returns the same `"=SUM(A1:A9)"` string whether the cell is
a live formula or text that merely looks like one. Only `UNFORMATTED_VALUE` can
tell them apart. A live formula returns its computed value; text returns the
literal string starting with `=`.

```python
from sheets_fidelity import find_dead_formulas

print(find_dead_formulas(ws, "C2:C40"))     # ['C7', 'C8'] when C7 and C8 are dead text
```

It reads the range twice, once as `FORMULA` and once as `UNFORMATTED_VALUE`, and
returns the addresses where both come back starting with `=`. Blank cells come
back from the API as empty rows, which the function skips.

Dead text usually comes from a round trip: formulas read out as strings, stored
as strings, and written back with `RAW`. The sheet still looks right and
computes nothing.

## Read formulas as formulas before you write them back

A read under `UNFORMATTED_VALUE` or `FORMATTED_VALUE` returns what a formula
computed. Write that back and the formula is gone, replaced by a constant that
was right on the day you read it. Read the block you intend to write back under
`FORMULA`, and write it with `USER_ENTERED`:

```python
block = read_values(ws, "C2:C40", render="FORMULA")
# ... change the cells you meant to change ...
write_values(ws, "C2:C40", block)           # USER_ENTERED keeps "=..." live
```

## Write one range and nothing else

A ranged update leaves merges, validation, notes, banding and conditional rules
alone, because it never clears anything outside the range you name.

```python
write_values(ws, "C2:C4", [[10], [20], [30]])                        # USER_ENTERED
write_values(ws, "A2:A3", [["0012"], ["0013"]], value_input_option="RAW")  # keeps the zeros
```

`USER_ENTERED` parses like a person typing: a leading `=` becomes a live
formula, dates and percentages are interpreted. `RAW` is for values that must
survive coercion intact.

## Read per-cell formatting, bounded

Cell-level reads are the expensive kind, so the range is required rather than
optional. The response grows with every cell in the range, so an unbounded read
of a large sheet is slow and heavy.

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
