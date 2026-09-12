# Needs-driven closure checks, 2026-09-11

One folder per program family. Each check derives its needs schema from the law's own
structure (not from PolicyEngine), then asks, per jurisdiction and per element, whether a
provision body in a scope selected by
`docs/ingest-runs/2026-09-11-us-rulespec-program-ingestion-union.selector.json` carries the
fact, and if not whether the gap is EXTRACTABLE, ABSENT, OUTREACH or REVIEW (plus N/A where
the jurisdiction's law has no such rule). Every jurisdiction x element pair has exactly one
row in the program's matrix CSV. Corpus artifacts are read only.

| program | schema | matrix | report | generator |
|---|---|---|---|---|
| Income tax (federal + 50 states + DC, incl. EITC/CTC and state counterparts) | `tax-schema.yaml` | `tax-matrix.csv` | `tax.md` | `tax-check.py` (writes `tax-stats.json`) |

Other program families (SNAP/WIC, Medicaid/CHIP, TANF/CCDF, SSI/LIHEAP/Medicare) are checked
on sibling branches `analysis/needs-closure-*`; append their rows here when they land.

Matrix columns: `jurisdiction, element, level, family, status, scope_version, citation_path,
pe_modeled, evidence_note` plus `element_label` and `rulespec_encoded`.
