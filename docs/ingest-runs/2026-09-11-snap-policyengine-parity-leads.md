# Federal SNAP: PolicyEngine parity leads (discovery input, no ingestion)

Date: 2026-09-11
Program: SNAP, federal (`gov/usda/snap` parameters and variables in policyengine-us)
Issue: https://github.com/TheAxiomFoundation/axiom-corpus/issues/680 seen from the other side:
documents PolicyEngine cites for federal SNAP that Axiom never catalogued.
Source of the list: `econ parity --program snap --emit-leads` in
TheAxiomFoundation/axiom-encode-economics, from policyengine-us `84253b6afa` (22,408 reference
URLs), the corpus navigation snapshot of 2026-09-09 (129,356 nodes) and rulespec-us `38d5c8c516`.
No corpus artifact was written; nothing was fetched from any publisher. This note records a
tracked discovery input, `sources/policyengine-us/snap_parity_gap_references.txt`, and how the
corpus's own classifier grades it.

## What a lead is

A PolicyEngine reference is a *registration gap* when all of the following hold:

1. its citation is derivable (Cornell, eCFR or uscode.house.gov path) or it joins no manifest
   `source_url` by canonical URL;
2. no corpus navigation node holds the citation **or any ancestor down to the section** the
   corpus ingests as one document (7 USC 2015 with 71 paragraph nodes registers 2015(o)(2)(C);
   7 CFR part 273 with section anchors registers 273.11(b)(3));
3. the host is graded primary official or secondary mirror by `classify_source_status`
   (screener sites, spreadsheets, data series and back-year FY tables are excluded upstream).

Encoding gaps (registered but no RuleSpec artifact, or a parent artifact that does not name the
cited paragraph) are axiom-encode work and are not in this list.

Two re-addressings, so the list names publishers the queue policy allows:

- **mirror to official.** A citation derived from a Cornell LII URL is written at eCFR
  (`https://www.ecfr.gov/current/title-7/section-273.11#p-273.11(b)(3)`) or uscode.house.gov
  (`…USC-prelim-title25-section1603…`). The cited URL is kept as a comment line.
- **enacting text to codified section.** A congress.gov public law or bill is enacting text; when
  the same PolicyEngine file also cites a US Code section, the reference takes that section's
  status and address (PL 119-21 pp. 11-12 → 25 USC 1603 and 1679; PL 119-21 p. 81, PL 118-5,
  PL 115-334, PL 105-33 → 7 USC 2015(o), which the corpus holds). Two have no codified sibling
  and stay as they are: FFCRA H.R. 6201 (emergency allotments, uncodified) and PL 113-79 p. 139
  (cited beside 7 CFR 273.9(d), a regulation, not a statute section).

USDA State Options Reports (six editions, nine references) are graded secondary and never
emitted: `manifests/state-snap-manual-agent-queue.yaml` names them under `forbidden_sources`.

## Federal SNAP parity at this snapshot

| bucket | references |
| --- | ---: |
| covered (artifact file for the citation) | 15 |
| covered by parent (parent artifact names the paragraph) | 22 |
| parent partial (parent artifact does not name it) | 23 |
| registered, not encoded | 32 |
| **not registered** | **35** |
| back-year FY tables | 59 |
| secondary (screeners, state options reports, unknown hosts) | 16 |
| data series | 5 |

Measurable current-law references 127, covered 37, **parity 29%**. Closing the measurable gap is
90 references to 83 distinct documents or paragraphs (33 regulation, 30 statute, 27 guidance);
35 of those references, **33 distinct documents**, are registration gaps and are the list here
(7 statute, 4 regulation, 24 guidance by the parity typing). With state SNAP parameters
(`--program all-snap`): 136 measurable, 27%, 43 leads to 41 documents.

Yesterday's figure on the same snapshot was 97 leads at 28%. The difference is not new coverage:
62 of the 97 were encoding gaps, now out of scope for discovery; nine paragraph citations into
7 USC 2014, 7 USC 2015, 8 USC 1612, 7 CFR 273.1 and 273.11 were mis-graded "not registered"
because only the exact paragraph node was tested; six public-law references resolved through
their codified sibling; seven State Options references dropped; one uscode.house.gov granule URL
is now parsed.

## How the corpus classifier grades the list

```
uv run --extra dev axiom-corpus-ingest source-discovery --base data/corpus \
  --input sources/policyengine-us/snap_parity_gap_references.txt \
  --source-name policyengine-us-parity \
  --release manifests/releases/us-rulespec-2026-08-23-canada-338-suspension-union.json
```

35 raw URLs, 33 canonical. `release_scope_present` is false for every row against the 275-scope
US selector, which agrees with the navigation-node test above.

| disposition | URLs | what they are |
| --- | ---: | --- |
| ready_for_manifest | 13 | 9 groups: `us/statute/statute` 2 (25 USC 1603, 1679), `us/regulation/regulation` 1 (7 CFR 271.2), `us/guidance/snap_guidance` 3 + `us/guidance/official_guidance` 1 (FNS COLA pages, emergency-allotment guidance, USDA OBBB time-limit waiver memo), `us-mi/manual/manuals` 2 (BEM 554, two hosts), `us-az/manual/manuals` 1 (FAA5, bot-walled per #681), `us-ca/guidance` 1 (ACL 26-15), `us-md/guidance` 1 (AT 26-08), `us-de/rulemaking` 1 (2005 proposed rule) |
| needs_review | 16 | `document_class: other` under `infer_document_class`: 7 FNS SNAP policy pages and PDFs (`fns.usda.gov/snap/work-requirements`, `…/obbb-alien-eligibility`, `…/provisions-fiscal-responsibility-act-2023`, `…/standard-utility-allowances`, `…/simplified-homeless-housing-cost-deduction-questions-and-answers`, `…/waiver-reinstatement`, the FNA 2008 as amended PDF), the two uncodified acts above, CBO 59710 and a Senate appropriations explanatory statement (analysis, not law), a Louisiana DCFS news page, an Alaska HR 1 impacts page, the LIHEAP Clearinghouse Heat-and-Eat PDF, and two Colorado SoS CCR rule PDFs (10 CCR 2506-1) |
| excluded_secondary | 4 | Cornell state regulations for Maine (10-144 CMR ch. 301 §555-5) and Mississippi (18 Miss. Code R. 14-20-4), oregon.public.law OAR 461-160-0430, and the 42 USC ch. 7 subch. IV part A directory (TANF, not a section) |

## Reviewer judgments (none taken; recorded for whoever runs the queue)

- The 7 FNS pages typed `other` are agency policy memoranda and Q&As on `fns.usda.gov/snap/…`
  and `fns-prod.azureedge.*/…/resource-files/…`. The corpus already registers such pages as
  `guidance` (two manifests) or `policy` (one). A host-scoped rule in `infer_document_class`
  would move them to `ready_for_manifest`; that is a corpus decision, not made here.
- The three state-regulation mirrors need the official publisher's URL (Maine SoS rules,
  Mississippi Administrative Code, Oregon SoS OAR); no crosswalk exists for state codes.
- CBO, the appropriations explanatory statement, the DCFS news page and the Alaska impacts page
  are not law; PolicyEngine cites them as evidence for parameter values. They should be marked
  reviewed-and-excluded rather than ingested.
- 25 USC 1603 and 1679 (Indian Health Care Improvement Act definitions, cited for the OBBBA
  ABAWD Indian exemption) and 7 CFR 271.2 (definitions) are the only statute/regulation
  registrations in the list; everything else is guidance.
- AZ FAA5 is `blocked_primary_source` in `manifests/snap-completion-agent-queue.yaml`; the
  lead does not change that.

## Regenerating

```
cd ~/axiom-encode-economics
uv run econ snapshot --name <snapshot> --skip corpus,ledger,oracle,git,prs,ci   # refresh pe only
uv run econ parity --program snap --emit-leads leads.jsonl                     # registration gaps
uv run econ parity --program snap --emit-leads leads.jsonl --leads-scope all   # + encoding gaps
```

The JSONL carries `reference_url` (official form), `cited_url`, `file_path`, `program`,
`jurisdiction`, `discovered_via: policyengine-us@<commit>`, `parity_bucket`, `citation_path`,
`document_kind`, `via` and `detail`, and is readable by `source-discovery --reference-input`
unchanged. The static list here is the same rows as URL lines with the provenance as comments.
