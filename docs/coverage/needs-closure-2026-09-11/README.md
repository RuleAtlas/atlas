# Needs-driven closure check, 2026-09-11

One folder per pass over the board Year 1 programs: does the corpus hold every source-document
family an end-to-end encoding of each program needs, per jurisdiction (federal plus the 50
states and DC), and where it does not, is the gap extractable, absent, outreach, or review?

Read-only with respect to `data/corpus`. Selected scopes are those in
`docs/ingest-runs/2026-09-11-us-rulespec-program-ingestion-union.selector.json` plus
`us/regulation/2026-09-11-title-42-part-436` (the federal CFR follow-on branch).

Files per program (`<program>` in lower case):

| File | Content |
| --- | --- |
| `<program>-schema.yaml` | the needs schema: every rule element a complete encoding must have, derived from the program's legal structure (statute, every CFR section, the state rulebook structure); PolicyEngine and rulespec-us recorded per element as a cross-check only |
| `<program>-matrix.csv` | one row per (jurisdiction, element): `jurisdiction, element, level, family, status, scope_version, citation_path, pe_modeled, evidence_note` |
| `<program>.md` | method, per-jurisdiction roll-up, top gaps by how many states share them, and what would close each class |
| `tools/` | the schema and matrix builders that produced the files (reproducible from `data/corpus` and the queues); `*_pass1.py` are the superseded 2026-09-11 builders kept for the audit trail, `search-universe.json` lists the scopes searched per state |

Status vocabulary (all programs): `PRESENT` (a specific provision in a selected scope carries the
element; cited), `EXTRACTABLE` (the publisher lists the carrying family; not taken),
`ABSENT` (the publisher posts nothing carrying it), `OUTREACH` (the queue row records a
publisher block), `REVIEW` (cannot tell), `INHERITED` (federal-only element counted once at the
`us` row), `NOT_APPLICABLE` (the element does not apply at that level, for example 42 CFR 436
for the 50 states, or a state-only element at the federal row).

## Index

| Program | Elements | Schema | Matrix | Report |
| --- | ---: | --- | --- | --- |
| Medicaid | 302 | [medicaid-schema.yaml](medicaid-schema.yaml) | [medicaid-matrix.csv](medicaid-matrix.csv) | [medicaid.md](medicaid.md) |
| CHIP | 186 | [chip-schema.yaml](chip-schema.yaml) | [chip-matrix.csv](chip-matrix.csv) | [chip.md](chip.md) |

Other programs' checks (SNAP, WIC, SSI, LIHEAP, Medicare, TANF, CCDF, tax) are run by
their own agents on sibling `analysis/needs-closure-*` branches; append their rows here when
they land.

The Medicaid and CHIP files are pass 2 (2026-09-12). Pass 1 (2026-09-11) was audited by
reading a random sample of its PRESENT cells and found too optimistic (hits in SNAP, TANF and
CalFresh scopes, table-of-contents lines, single-word patterns); `medicaid.md` and `chip.md`
record what changed and the residual false-positive rate estimated from the pass-2 sample.
