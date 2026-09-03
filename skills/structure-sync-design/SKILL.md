---
name: structure-sync-design
description: Designs a safe Google Sheets content-sync and layout-sync architecture, especially for repeated blocks, formulas, formatting, groups, hidden rows, and frozen panes. Use when building or refactoring a sheet editor, template engine, or sync system.
disable-model-invocation: true
---

Design a Google Sheets sync architecture that separates content editing from layout editing and makes repeated-block sheets safe to evolve.

This skill is for systems that need more than raw cell writes:
- template-driven sheets
- repeated row blocks
- per-store or per-location sections
- canonical structure replicated many times
- formulas and formatting that must survive sync
- grouping / frozen panes / hidden rows / rules that matter to users

## First principle

Treat a spreadsheet as multiple overlapping systems:

1. **Content**
   - labels
   - literals
   - formulas
   - notes
   - links

2. **Cell presentation**
   - text formatting
   - colors
   - borders
   - alignment
   - wraps
   - padding / indent

3. **Dimension structure**
   - row and column count
   - row height / column width
   - hidden state

4. **Sheet layout / rules**
   - frozen panes
   - groups
   - merges
   - filters
   - protected ranges
   - banding
   - conditional formatting

5. **Template semantics**
   - row identity
   - row type
   - grouping semantics
   - repeated block boundaries
   - inheritance rules for new rows

Never design a sync engine that only understands one of these layers while writing into all of them.

## Architecture goal

Separate the system into two engines:

### Phase 1: Content engine
Safe operations on existing structure only:
- edit existing labels or formulas
- update mapped fields
- push values only to owned cells
- diff and dry-run all changes
- no row insertion/deletion/move
- no casual layout rewrites

### Phase 2: Layout engine
Explicit structural sync:
- insert row across all repeated blocks
- delete row across all repeated blocks
- reorder rows
- rebuild or preserve groups
- copy/inherit formatting for new rows
- preview structural blast radius before apply

Do not merge these phases into one vague "push."

## Required data model

Recommend a model that can survive reorder and re-import.

Minimum structure:
- `row_uid` — stable logical row ID
- `row_fingerprint` — deterministic matching helper
- `block_type` — header_block / repeated_block / footer_block / etc.
- `row_kind` — metric / header / section_header / spacer / formula / note / etc.
- `group_key`
- `group_depth`
- `is_hidden_default`
- `sort_key`
- `source_row_index`
- `style_json`
- `content_json` or equivalent if formulas/notes/links are part of template semantics

For repeated sheets, also define:
- block anchor row
- repeated block size
- store/location/entity identifier
- validation rules for block uniformity

## Row identity rules

Never use row number alone as identity.

Matching precedence should be:
1. explicit stored stable ID if source mapping is known
2. strong fingerprint
3. contextual fingerprint with neighbors
4. create a new ID only when no safe match exists

On ambiguous match:
- do not silently reassign ownership
- flag for review

## Required ownership model

Every design must declare:

### App owns
What the sync engine is allowed to create, move, or rewrite.

### Sheet owns
What should remain whatever it already is unless a special restore flow runs.

### Read-only
What may be read for context but not changed during ordinary sync.

### Explicit no-touch surfaces
What must never be touched by normal content sync.

If the sheet has formulas or formatting in columns the app does not understand, put them in no-touch surfaces.

## Repeated-block design rules

If a structure repeats across multiple stores/locations/entities:

- import one canonical block plus validation against the other blocks
- compute diffs at the canonical block level
- apply layout changes consistently to every block
- abort if blocks are inconsistent in ways the engine cannot safely reconcile

Do not implement ad hoc per-block edits without a canonical model.

## Formatting strategy choices

For layout sync, require an explicit choice:

### A. Exact fidelity
Store enough metadata to restore real formatting.
Use when the sheet itself is the design source of truth.

### B. App-owned standardized formatting
The app defines the look.
Use when consistency matters more than preserving manual styling.

### C. Hybrid ownership
The app owns only certain surfaces, such as label columns or template-managed rows.
Use when formulas/data/reporting columns should remain untouched.

Do not let a project drift between these modes without naming it.

## Insertion and deletion rules

When a new row is inserted, always define:
- where it goes in canonical order
- how it maps across repeated blocks
- how formulas are created or copied
- how formatting is inherited
- whether grouping boundaries must expand
- whether frozen panes or filters are affected
- how dry-run output will show the blast radius

When deleting a row:
- show all affected blocks
- show formulas/ranges that will shift
- show group changes
- show what is cleared vs removed

## Required dry-run output

Any structure-sync proposal must show:
- rows added / removed / moved
- all affected sheet row ranges
- all affected repeated blocks
- formulas copied/shifted
- formatting inheritance strategy
- grouping/rule changes
- request types that will be sent
- explicit no-touch surfaces
- safe_to_apply true/false with reasons

## Minimum test strategy

Design tests for:
1. idempotent import + dry-run
2. content edit on existing row
3. formula preservation
4. no-touch column protection
5. repeated-block insert across all blocks
6. repeated-block delete across all blocks
7. grouping preservation/rebuild
8. hidden row preservation
9. frozen pane preservation
10. ambiguous fingerprint detection
11. structural mismatch blocks live apply
12. copy/test-sheet mode before live apply

## Output format

When invoked, respond with:

1. **Current problem framing**
2. **Ownership model**
3. **Proposed Phase 1 content engine**
4. **Proposed Phase 2 layout engine**
5. **Required schema**
6. **Read/store/write boundaries**
7. **Diff and dry-run design**
8. **Failure modes**
9. **Test plan**
10. **Recommended implementation order**

## Tone and behavior

- Be concrete, not theoretical.
- Prefer safe two-phase rollouts over big-bang rewrites.
- Preserve UX concepts even when live writes must be narrower at first.
- If the current system is pretending to support layout sync without enough metadata, say so directly.
