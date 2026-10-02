# sheets-fidelity

Read a Google Sheet with `FORMULA` before you write it back, so formulas go back as formulas. Read it with `UNFORMATTED_VALUE` and write that back, and every formula in the range becomes the number it showed that day. This repo is Python helpers and Claude Code skills built around that, and around the other things a write-back can lose, such as merges, filters, frozen rows and conditional formatting. More of my work is at [oliverschwartz.me](https://oliverschwartz.me).

## One cell, before and after

C3 holds `=SUM(A3:B3)`. A3 is 10 and B3 is 20, so C3 shows 30. Read C3, write it back with `USER_ENTERED`, then change A3 to 15.

| Read C3 with | You get | C3 after the write-back | C3 after A3 becomes 15 |
|---|---|---|---|
| `UNFORMATTED_VALUE` | `30` | `30`, a plain number | `30` |
| `FORMULA` | `"=SUM(A3:B3)"` | `=SUM(A3:B3)` | `35` |

Nothing errors in the first row. The sheet looks right until someone changes an input.

```python
from sheets_fidelity import read_values, write_values

block = read_values(ws, "C2:C40", render="FORMULA")
# change the cells you meant to change
write_values(ws, "C2:C40", block)   # USER_ENTERED, so "=..." stays a formula
```

The table is what the Sheets API documents for these render options. I have not run it against a live sheet yet. [docs/LIVE-CHECK.md](docs/LIVE-CHECK.md) does that in about a minute on a scratch sheet.

## Install

```
pip install git+https://github.com/o-liverschwartz/sheets-fidelity
```

The skills, as a Claude Code plugin:

```
/plugin marketplace add o-liverschwartz/sheets-fidelity
/plugin install sheets-fidelity@sheets-fidelity
```

To run the tests and the offline demo from a clone:

```
pip install -e ".[dev]"
python -m pytest
python examples/demo_offline.py
```

You bring your own `gspread` client. `examples/README.md` has one snippet per function.

## Two checks

A rewrite kept the values and the two conditional rules, and dropped the merges and the frozen header. Nothing errored. Snapshot the structure before and after, and diff it:

```python
from sheets_fidelity import diff_structure

before = tab(merges=3, rules=2, frozen=1)
after = tab(rules=2)
print(diff_structure(before, after))
```

```
{'Q3 Plan': {'merges': (3, 0), 'frozenRows': (1, 0)}}
```

In real use `before` and `after` are `read_formatting(spreadsheet)["structure"]`, taken either side of your write. An empty dict means nothing was lost. `tab()` is the canned snapshot in `examples/demo_offline.py`.

The second check finds formulas that have turned into text. `FORMULA` returns `"=SUM(A3:B3)"` for a live formula and for a cell that only holds that text. `UNFORMATTED_VALUE` returns the computed number for the first and the text for the second, so the function reads both and compares:

```python
from sheets_fidelity import find_dead_formulas

print(find_dead_formulas(worksheet, "C2:C4"))
```

```
['C3']
```

`worksheet` here is the fake `Sheet` from the same file.

## What is in it

- `read_values`: one of three render modes, checked before the call.
- `write_values`: writes the range you name and nothing else.
- `read_formatting`: sheet structure at any size. Per-cell formatting only for a bounded range such as `Sheet1!A1:H40` or `Sheet1!$A$1:$H$40`. It refuses `Sheet1`, `Sheet1!A:A` and `Sheet1!A1:Z` before any request goes out.
- `batch_format`: raw `batchUpdate` requests, for everything that is not a value.
- `diff_structure`, `find_dead_formulas`: the two checks above.
- `quote_a1`: single-quotes tab names like `Q3 Plan` and doubles the apostrophe in `Bob's Tab`.

Three skills sit on top. `roundtrip-reference` is what Sheets stores and what survives a write, and it loads on its own. `fidelity-audit` makes you prove whether data is lost on read, in storage or on write before you patch anything. `structure-sync-design` separates a content engine from a layout engine for template-driven sheets. The last two run only when you invoke them.

## What it does not do

- It does not authenticate. Pass in a `gspread` worksheet or spreadsheet.
- The test suite has not touched a live sheet. The 61 tests run offline, against fakes and one real `gspread.Worksheet` with a stubbed HTTP client, so they prove what is requested and not what Google returns.
- It does not protect text that looks like a formula. A cell holding the text `=B2` reads back as `=B2` under `FORMULA`, and a `USER_ENTERED` write makes it live. Run `find_dead_formulas` on the range first.
- It does not cover charts, slicers or pivot tables.
- It does not retry on rate limits or repair a sheet after a bad write. It tells you what was lost.

## License

MIT. See [LICENSE](LICENSE).
