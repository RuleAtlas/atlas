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



One folder per program family. Each check asks: does the corpus hold every source
document family a complete encoding of the program's rulebook needs, per jurisdiction
(federal plus the 50 states and DC), and where it does not, is the gap EXTRACTABLE
(publisher lists the carrying document, not taken or not selected), ABSENT (publisher
posts nothing), OUTREACH (publisher blocks) or REVIEW (cannot tell from the evidence)?

The bar is the law's own structure (statute, CFR, state rulebook), not PolicyEngine;
PolicyEngine is a cross-check that shows where Axiom goes beyond it.

Files per program:

- `<program>-schema.yaml`: the needs schema (federal statute elements, every CFR
  section, state-level elements with the facts an encoder reads, PolicyEngine cross-check).
- `<program>-matrix.csv`: one row per jurisdiction x element with
  `jurisdiction, element, level, family, status, scope_version, citation_path, pe_modeled, evidence_note`.
  Federal-only elements have one row at `us` and are inherited by the 51 jurisdictions.
- `<program>.md`: method, per-jurisdiction roll-up, top gaps, what closes each class,
  elements beyond PolicyEngine, timing and searches.

## Index

| Program | Files | Builder |
| --- | --- | --- |
| TANF | `tanf-schema.yaml`, `tanf-matrix.csv`, `tanf.md` | `build_tanf_ccdf_matrix.py` (read-only over `data/corpus`; `summary.json` is its roll-up) |
| CCDF | `ccdf-schema.yaml`, `ccdf-matrix.csv`, `ccdf.md` | `build_tanf_ccdf_matrix.py` |

Other agents append their programs to this index.
