# Changelog

## 0.1.0

- `read_values`, `read_formatting`, `write_values`, `batch_format`, `quote_a1`, `validate_bounded_range`, `col_letter`.
- `diff_structure` and `find_dead_formulas`.
- `read_formatting` now checks the range before it makes any request, and refuses whole-column, whole-row and open-ended ranges. Absolute references like `$A$1:$B$2` pass.
- `read_values` and `write_values` accept a tab-qualified range and reduce it to the span.
- The field masks now request notes, hyperlinks, rich-text runs, hidden state, basic filters and filter views.
- Three Claude Code skills: `roundtrip-reference`, `fidelity-audit`, `structure-sync-design`.
