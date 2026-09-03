# google-sheets-roundtrip

What survives a write back to Google Sheets, and what quietly doesn't.

Reading a sheet is easy. Reading it, holding it in an app, and writing it back
without destroying something is not, and the failure is nearly always silent —
the values look right and the conditional formatting is gone, or the merged
cells are gone, or a column of live formulas has become text that looks like
formulas.

Three skills for Claude Code, plus the tested Python helper underneath them.

## The three layers

Nothing here makes sense until a spreadsheet stops being one object. It is
three systems wearing one costume, and the API returns them through different
fields at wildly different costs:

**Values** — `userEnteredValue`, `effectiveValue`, `formattedValue`. What the
cell holds, what it computed, what it shows.

**Formatting** — `userEnteredFormat`, `effectiveFormat`, `textFormatRuns`, plus
data validation. Per cell, and therefore expensive.

**Structure** — frozen panes, merges, conditional formatting rules, protected
ranges, banding, row and column groups, named ranges. Per sheet, and therefore
cheap.

Most fidelity bugs are a read that fetched one layer and a write that assumed
all three.

## The two expensive mistakes

**Fetching cell data without a bounded range.** `includeGridData` with no range
means the whole grid. On a real working sheet that response is hundreds of
megabytes and reads like a hang, not an error. Structure-only is safe to fetch
unconditionally; cell-level is not, which is why `read_formatting` demands a
range for the second half and refuses before the network call rather than after
it.

**Rewriting a whole sheet to change part of one.** A ranged update touches only
the range you name and leaves merges, validation, notes, banding and
conditional rules alone. Clearing and rewriting is what deletes the work
somebody spent an afternoon on.

## What is here

```
skills/
  google-sheets-roundtrip-reference/   what Sheets stores vs what the API returns
    scripts/sheets_fidelity.py         the same rules, executable
  sheets-fidelity-audit/               find the layer where a round trip is losing data
  sheets-structure-sync-design/        architecture for template-driven sheets
tests/                                 34 offline tests, no credentials needed
```

`google-sheets-roundtrip-reference` is the mental model, and loads whenever
you're reading, writing or auditing sheet behaviour. The other two are
manual-invoke: reach for the audit when a sheet imports correctly but writes
back wrong, and the design skill when building a sync system, template engine
or sheet editor that has to survive repeated blocks and evolving layouts.

## Install

```
/plugin marketplace add o-liverschwartz/google-sheets-roundtrip
/plugin install google-sheets-roundtrip@google-sheets-roundtrip
```

Or copy the three directories under `skills/` into `~/.claude/skills/`.

## The Python helper

`sheets_fidelity.py` is the executable half of the reference: the field masks,
the value-layer options, and the three pure helpers where the real bugs live.
It takes a `gspread` worksheet or spreadsheet you have already built —
authentication is deliberately not its business.

```python
from sheets_fidelity import read_formatting, read_values, write_values

# Structure only: frozen panes, conditional formats, merges, groups, banding.
# Cheap enough to call on any sheet, any size.
read_formatting(spreadsheet)

# Adds per-cell formatting for one bounded range. The range is required.
read_formatting(spreadsheet, "Q3 Plan!A1:H40")

# Prove a cell holds a live formula rather than text that looks like one.
read_values(worksheet, "C2:C40", render="UNFORMATTED_VALUE")

# Touches C2:C40 and nothing else.
write_values(worksheet, "C2:C40", rows)
```

Three things it gets right that are easy to get wrong:

`FORMULA` returns the same `"=SUM(A1:A9)"` string for a live formula and for a
cell containing that text, so it can never prove a formula is live. Only
`UNFORMATTED_VALUE` can — a live formula returns its computed value, and text
returns the literal string.

A tab named `Q3 Plan` or `Sales (EU)` is a 400 unless the sheet name is
single-quoted, and a tab with an apostrophe needs it doubled. `quote_a1` does
this centrally, because the apostrophe case looks fine in testing and breaks on
a real user's tab.

The `fields` mask on a `batchUpdate` request is what stops a partial format
update from blanking every property you didn't mention.

## Tests

```
python -m pytest
```

34 tests, entirely offline — no credentials, no network, no live spreadsheet.
The pure helpers are tested directly. The four API-touching functions run
against a fake that records what it was asked for, so the field masks and
options are asserted rather than assumed.

## Where it came from

An MCP server I built for retail operations, where a wrong write lands in a
spreadsheet somebody is using to run a store that afternoon. The generic core
is what's here; the business logic stayed behind.

## Licence

MIT. See [LICENSE](LICENSE).
