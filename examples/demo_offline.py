"""Runs with no credentials. Two canned structure snapshots stand in for the API:
the sheet before a whole-sheet rewrite, and what was left after it."""
from sheets_fidelity import diff_structure, find_dead_formulas


def tab(merges=0, rules=0, frozen=0):
    return {"sheets": [{
        "properties": {"title": "Q3 Plan", "gridProperties": {"frozenRowCount": frozen}},
        "merges": [{}] * merges,
        "conditionalFormats": [{}] * rules,
    }]}


before = tab(merges=3, rules=2, frozen=1)
after = tab(rules=2)      # the rewrite kept the values and the rules, and dropped the rest

print(diff_structure(before, after))


class Sheet:
    """Column C as the API returns it. C3 was written back with RAW."""
    title = "Q3 Plan"
    rows = {"FORMULA": [["=SUM(A2:B2)"], ["=SUM(A3:B3)"], []],
            "UNFORMATTED_VALUE": [[30], ["=SUM(A3:B3)"], []]}

    def get(self, cell_range, value_render_option=None):
        return self.rows[value_render_option]


print(find_dead_formulas(Sheet(), "C2:C4"))
