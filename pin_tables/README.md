# Datasheet pin tables (2026-11-19)

Run after every schematic or board change:

    python3 tools/extract_pin_tables.py     # only when a datasheet or part changes
    python3 tools/check_pin_tables.py       # exit 1 on any failure

The tables come from the datasheets in `~/.cache/haven_datasheets/`, never from our schematic. `parts.csv` records
the provenance for each one:
- **parsed:** the script read the PDF text.
- **manual:** a person typed it in from a drawing.
- **unverified:** the maker's drawing hasn't been seen.

The checker always prints what it did not check.

Test run on the pre-audit board (`v3_pod_before_audit_2026-11-19`): it flags the CAAB charger and the reversed LED.
Those rules were written after the bugs were known, so this shows the rules hold them, not that the script would have
found them first. The general checks (pin names, ground pins, tied power pins, NC pins, board vs schematic nets, passive
values) do not depend on knowing the answer.

Not covered:
- layout rules, such as Raytac's top-layer no-ground area
- land-pattern pad sizes
- voltage ratings
- firmware settings, such as the crystal capacitance (audit Finding 4)

When you add a part, give its family a row in `variants.csv` that says why the suffix matters.
