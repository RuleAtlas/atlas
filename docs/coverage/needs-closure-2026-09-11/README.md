# Needs-driven closure checks, 2026-09-11

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
