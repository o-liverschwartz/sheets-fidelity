# sheets-fidelity

A small set of tools and agent skills for editing Google Sheets without silently
destroying things that matter.

Reading a sheet is easy. Reading it, holding it in an app, and writing it back
without losing something is not. The failure is almost always silent: the values
look right, and the conditional formatting is gone. Or the merges are gone. Or a
column of live formulas is now text that looks exactly like formulas and
computes nothing.

Three skills for Claude Code, and the tested Python underneath them.

## The layers

None of this makes sense until a spreadsheet stops being one object. It is
several systems wearing one costume, and the API returns them through different
fields at wildly different costs.

| Layer | Fields | Cost |
| --- | --- | --- |
| Values | `userEnteredValue`, `effectiveValue`, `formattedValue` | cheap |
| Formatting | `userEnteredFormat`, `effectiveFormat`, `textFormatRuns`, data validation | per cell, expensive |
| Dimension metadata | row and column pixel sizes, hidden state | per cell range |
| Sheet structure | frozen panes, merges, conditional formats, protected ranges, banding, row and column groups, named ranges | per sheet, cheap |

Nearly every fidelity bug is a read that fetched one layer and a write that
assumed all four.

## Reference, diagnose, design

The three skills do different jobs, in that order.

`roundtrip-reference` is the knowledge layer: what Sheets actually stores, what
the API actually returns, and what survives a write back. Everything else stands
on it, and it is the only one that loads automatically, because it applies
whenever you are reading, writing, or reasoning about sheet behaviour.

`fidelity-audit` is the diagnostic workflow. When a sheet imports correctly but
writes back wrong, it refuses to let you patch first. It makes you prove whether
fidelity dies during read, during storage, or during write, then build a loss map
before you change a line. Manual invoke.

`structure-sync-design` is the architecture workflow, for systems that need more
than raw cell writes: template engines, sheet editors, repeated per-section
blocks. It separates a content engine from a layout engine, and introduces stable
row identities, ownership boundaries, and blast-radius previews. Manual invoke.

## The Python

`sheets_fidelity` is the reference made executable. The API mirrors the
conceptual model instead of hiding it behind one magical `sync_sheet()`:

```python
read_values(worksheet, "C2:C40", render="UNFORMATTED_VALUE")
read_formatting(spreadsheet)                      # structure only, safe at any size
read_formatting(spreadsheet, "Q3 Plan!A1:H40")    # adds per-cell detail, bounded
write_values(worksheet, "C2:C40", rows)           # touches C2:C40 and nothing else
batch_format(spreadsheet, requests)               # everything that is not a value
```

Four functions, one per thing you can actually do. If you want values you read
values; if you want structure you read structure. You cannot accidentally pull a
hundred megabytes because you wanted to know whether row 1 was frozen.

It takes a `gspread` worksheet or spreadsheet you have already built.
Authentication is not its business.

### Three things that are easy to get wrong

`validate_bounded_range` refuses before the network call. An unbounded
cell-metadata fetch on a real working sheet returns hundreds of megabytes and
reads like a hang rather than an error. `read_formatting` requires a bounded
range for its expensive half and rejects `"Sheet1"` or `"Sheet1!A1"` locally, so
the mistake costs nothing.

`FORMULA` can never prove a formula is live. It returns the same `"=SUM(A1:A9)"`
string for a live formula and for a cell containing that text. Only
`UNFORMATTED_VALUE` tells them apart, because a live formula returns its computed
value. This is the most common silent round-trip failure there is.

`quote_a1` doubles the apostrophe. A tab named `Q3 Plan` or `Sales (EU)` is a 400
unless the sheet name is single-quoted, and `Bob's Tab` needs the apostrophe
doubled. Handled centrally, because the apostrophe case looks fine in testing and
breaks on a real user's tab.

## Tests

```
python -m pytest
```

34 tests, entirely offline. No credentials, no network, no live spreadsheet. The
pure helpers are tested directly. The four API-touching functions run against a
fake that records what it was asked for, so the tests assert the behaviour that
actually matters:

- unbounded metadata reads never reach the network
- a structure read does not accidentally request grid data
- the structure field mask includes the easy-to-lose pieces: conditional formats,
  protected ranges, banding, merges, groups, named ranges
- quoted, unquoted and apostrophe-bearing tab names all resolve correctly
- an invalid render or input option fails before a request is made

## Layout

```
skills/
  roundtrip-reference/     knowledge layer, loads automatically
  fidelity-audit/          diagnostic workflow, manual invoke
  structure-sync-design/   architecture workflow, manual invoke
src/sheets_fidelity/       the library
tests/                     34 offline tests
examples/                  runnable shapes
```

## Install

The skills, as a Claude Code plugin:

```
/plugin marketplace add o-liverschwartz/sheets-fidelity
/plugin install sheets-fidelity@sheets-fidelity
```

Or copy the directories under `skills/` into `~/.claude/skills/`.

The library:

```
pip install git+https://github.com/o-liverschwartz/sheets-fidelity
```

## Where it came from

An MCP server I built for retail operations, where a wrong write lands in a
spreadsheet somebody is using to run a store that afternoon. The generic core is
what's here; the business logic stayed behind.

## Licence

MIT. See [LICENSE](LICENSE).
