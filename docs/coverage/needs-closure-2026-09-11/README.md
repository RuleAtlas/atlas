# Needs-driven closure check, 2026-09-11

One folder per pass over the board Year 1 programs: does the corpus hold every source-document
family a complete encoding of each program's rulebook needs, per jurisdiction (federal plus the
50 states and DC), and where it does not, is the gap extractable, absent, outreach, or review?

The bar is the law's own structure (statute, every CFR section, the state rulebook), not
PolicyEngine; PolicyEngine and rulespec-us are recorded per element as a cross-check that shows
where Axiom goes beyond them. Read-only with respect to `data/corpus`. Selected scopes are those in
`docs/ingest-runs/2026-09-11-us-rulespec-program-ingestion-union.selector.json`; the SNAP check also
treats the twelve `2026-09-11-<st>-snap-manual-supersede` scopes on disk as replacing their released
versions.

Files per program (`<program>` in lower case):

| File | Content |
| --- | --- |
| `<program>-schema.yaml` | the needs schema: every rule element a complete encoding must read, derived from the program's legal structure; `pe_modeled` and `rulespec_scoped` per element as a cross-check only |
| `<program>-matrix.csv` | one row per (jurisdiction, element): `jurisdiction, element, level, family, status, scope_version, citation_path, pe_modeled, evidence_note` |
| `<program>.md` | method, per-jurisdiction roll-up, top gaps by how many states share them, what would close each class, elements beyond PolicyEngine, schema uncertainty, timing and searches |

Status vocabulary (all programs): `PRESENT` (a specific provision body in a selected scope carries
the element; cited), `EXTRACTABLE` (the publisher lists the carrying family; not taken), `ABSENT`
(the publisher posts nothing carrying it; what was checked is in the note), `OUTREACH` (the queue row
records a publisher block), `REVIEW` (cannot tell from the evidence), `INHERITED` (federal-level
element decided once at the `us` row; the state row's note names the federal status).

## Index

| Program | Elements | Schema | Matrix | Report | Builder |
| --- | ---: | --- | --- | --- | --- |
| SNAP | 393 | [snap-schema.yaml](snap-schema.yaml) | [snap-matrix.csv](snap-matrix.csv) | [snap.md](snap.md) | `check_snap_wic.py` (schema + matrix + `summary.json` + `snap-hits.jsonl`), `write_snap_wic_reports.py` (report); `cfr_structure.py` holds the eCFR section lists for 7 CFR 246 and 271-285 |
| WIC | 114 | [wic-schema.yaml](wic-schema.yaml) | [wic-matrix.csv](wic-matrix.csv) | [wic.md](wic.md) | same builders (`wic-hits.jsonl`) |

Other programs' checks (Medicaid, CHIP, SSI, LIHEAP, Medicare, TANF, CCDF, tax) are run by their
own agents on sibling `analysis/needs-closure-*` branches; append their rows here when they land.
