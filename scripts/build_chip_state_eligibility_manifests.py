"""Build one corpus manifest per jurisdiction for the state CHIP eligibility policy family
(state agency CHIP eligibility manual / handbook chapter / adopted eligibility rule), and
update the CHIP agent queue (manifests/chip-agent-queue.yaml).

Every source below was confirmed by the agent from the publisher's own index page on
2026-09-10 (see docs/ingest-runs/2026-09-10-chip-state-eligibility-manuals.md for the index
inventories). Blocked publishers and jurisdictions already covered by existing corpus scopes
are recorded on the queue rows only; no manifest is written for them.

    uv run python scripts/build_chip_state_eligibility_manifests.py
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "manifests" / "chip-agent-queue.yaml"
SOURCE_AS_OF = "2026-09-10"
VERSION = "2026-09-10-chip-state-eligibility-manual"
DISCOVERED_VIA = "manual-review:chip-agent-queue; publisher index confirmed by agent 2026-09-10"


def doc(
    jur: str,
    source_id: str,
    title: str,
    url: str,
    citation_path: str,
    fmt: str,
    expression_date: str,
    *,
    document_class: str = "manual",
    subtype: str,
    authority: str,
    extraction: dict | None = None,
    request: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    d: dict = {
        "source_id": source_id,
        "jurisdiction": jur,
        "document_class": document_class,
        "title": title,
        "source_url": url,
        "source_format": fmt,
        "source_as_of": SOURCE_AS_OF,
        "expression_date": expression_date,
        "citation_path": citation_path,
    }
    if request:
        d["request"] = request
    if extraction:
        d["extraction"] = extraction
    d["metadata"] = {
        "primary_source": True,
        "source_authority": authority,
        "document_subtype": subtype,
        "program": "CHIP",
        "source_discovery_group": f"{jur}/{document_class}/chip",
        "discovered_via": DISCOVERED_VIA,
        **(metadata or {}),
    }
    return d


IMPERSONATE = {"browser_impersonation": True}
PAGES = {"page_citation_prefix": "page"}

# --- confirmed jurisdictions -----------------------------------------------------------

CONFIRMED: dict[str, dict] = {
    "us-al": {
        "name": "Alabama",
        "document_class": "manual",
        "source_kind": "official_agency_eligibility_pages",
        "index_url": "https://www.alabamapublichealth.gov/allkids/index.html",
        "index_document_count": 17,
        "primary_source_url": "https://www.alabamapublichealth.gov/allkids/income.html",
        "notes": (
            "ADPH ALL Kids program index (17 program pages: home, income guidelines, pay premium, "
            "benefits booklet, standards of care, how to apply, apply, enrolled families, order "
            "materials, FAQ, Spanish, enrollment data, links, research, reports, other insurance, "
            "about). Taken: the agency's own eligibility policy pages (Income Guidelines effective "
            "2/1/2026; Premiums and Copays). ADPH publishes no ALL Kids eligibility manual; the "
            "Alabama Administrative Code chapter for ALL Kids could not be located on the LSA "
            "admincode site (chapter API 420-10-1 is newborn screening, 420-10-2 is WIC, "
            "420-10-3..7 return 404; no chapter-list API). Reviewer judgment: agency eligibility "
            "pages recorded under document_class manual with document_subtype "
            "agency_eligibility_policy_page."
        ),
        "documents": [
            doc(
                "us-al", "al-adph-allkids-income-guidelines",
                "ADPH ALL Kids: Income Guidelines (effective 2/1/2026)",
                "https://www.alabamapublichealth.gov/allkids/income.html",
                "us-al/manual/adph/chip/income-guidelines", "html", "2026-02-01",
                subtype="agency_eligibility_policy_page",
                authority="Alabama Department of Public Health, ALL Kids",
                request=IMPERSONATE,
                extraction={"html_content_selector": "div.col-sidebar-content"},
                metadata={"state_program": "ALL Kids"},
            ),
            doc(
                "us-al", "al-adph-allkids-premiums-and-copays",
                "ADPH ALL Kids: Premiums and Copays",
                "https://www.alabamapublichealth.gov/allkids/premiums-and-copays.html",
                "us-al/manual/adph/chip/premiums-and-copays", "html", "2026-01-01",
                subtype="agency_eligibility_policy_page",
                authority="Alabama Department of Public Health, ALL Kids",
                request=IMPERSONATE,
                extraction={"html_content_selector": "div.col-sidebar-content"},
                metadata={"state_program": "ALL Kids"},
            ),
        ],
    },
    "us-ct": {
        "name": "Connecticut",
        "document_class": "manual",
        "source_kind": "official_agency_eligibility_pages",
        "index_url": "https://portal.ct.gov/dss/find-benefits-and-support/healthcare-coverage",
        "index_document_count": 9,
        "primary_source_url": "https://portal.ct.gov/dss/knowledge-base/articles/healthcare-coverage/husky-b",
        "notes": (
            "DSS healthcare-coverage index: 9 HUSKY documents (prescreener, how to qualify, member "
            "info, provider info, benefits overview, advisory committee, HUSKY Health landing, "
            "non-citizen children coverage, H.R.1 changes). Taken: DSS knowledge-base article "
            "'HUSKY B' (the agency's CHIP eligibility statement) and the March 1, 2026 HUSKY Health "
            "monthly income chart PDF attached to the DSS 'HUSKY Health Income Charts' article "
            "(the article itself is a 161-character stub). The DSS Uniform Policy Manual "
            "(https://portal.ct.gov/dss/lists/uniform-policy-manual, 129 list pages of .doc/.docx "
            "sections) has no HUSKY B chapter in UPM0/UPM2/UPM8 listings; the linked "
            "huskymonthlyincomechart.pdf is dated March 2020 and was not taken. Reviewer judgment: "
            "agency pages recorded as document_class manual, subtype agency_eligibility_policy_page."
        ),
        "documents": [
            doc(
                "us-ct", "ct-dss-husky-b-article",
                "Connecticut DSS: What is HUSKY B? (Children's Health Insurance Program)",
                "https://portal.ct.gov/dss/knowledge-base/articles/healthcare-coverage/husky-b",
                "us-ct/manual/dss/chip/husky-b", "html", "2025-06-13",
                subtype="agency_eligibility_policy_page",
                authority="Connecticut Department of Social Services",
                request=IMPERSONATE,
                extraction={"html_content_selector": "div.article-body"},
                metadata={"state_program": "HUSKY B"},
            ),
            doc(
                "us-ct", "ct-dss-husky-monthly-income-chart-2026",
                "Connecticut DSS: HUSKY Health Monthly Income Chart, March 1, 2026",
                "https://portal.ct.gov/dss/-/media/departments-and-agencies/dss/fact-sheets-and-issue-briefs/fact-sheets/husky-income-charts/husky-health-monthly-income-chart-march-1-2026.pdf?rev=eafe894baf074727b4ace4651ae19df7&hash=630A05F5CEF1DF1D2C753B40745E36A1",
                "us-ct/manual/dss/chip/husky-monthly-income-chart-2026", "pdf", "2026-03-01",
                subtype="agency_income_standards_chart_pdf",
                authority="Connecticut Department of Social Services",
                request=IMPERSONATE,
                extraction=PAGES,
                metadata={"state_program": "HUSKY B",
                          "chart_article": "https://portal.ct.gov/dss/knowledge-base/articles/fact-sheets-and-brochures-articles/income-tables-articles/husky-income-charts"},
            ),
        ],
    },
    "us-de": {
        "name": "Delaware",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_pdf",
        "index_url": "https://regulations.delaware.gov/AdminCode/title16",
        "index_document_count": 1,
        "primary_source_url": "https://regulations.delaware.gov/api/AdminCode/title16/18000/b78ac36e-3af7-4d1a-9503-16927de57397",
        "notes": (
            "Delaware Administrative Code Title 16, DSS Division of Social Services Manual: the "
            "AdminCode title API lists one CHIP regulation, '18000 Delaware Healthy Children "
            "Program' (regulationId 1054, pdfId b78ac36e-...). Taken. Same publisher/API as the "
            "existing us-de-dssm-13000 manifest; dhss.delaware.gov itself presents a self-signed "
            "certificate in its chain and was not used."
        ),
        "documents": [
            doc(
                "us-de", "de-dhss-dssm-18000",
                "Delaware Administrative Code Title 16 DSSM 18000: Delaware Healthy Children Program",
                "https://regulations.delaware.gov/api/AdminCode/title16/18000/b78ac36e-3af7-4d1a-9503-16927de57397",
                "us-de/regulation/admin-code/title16/dssm/18000", "pdf", SOURCE_AS_OF,
                document_class="regulation",
                subtype="administrative_code_pdf",
                authority="Delaware Department of Health and Social Services, Division of Social Services",
                extraction=PAGES,
                metadata={"state_program": "Delaware Healthy Children Program", "title_number": "16", "chapter": "18000",
                          "regulation_page": "https://regulations.delaware.gov/AdminCode/title16/18000"},
            ),
        ],
    },
    "us-ga": {
        "name": "Georgia",
        "document_class": "manual",
        "source_kind": "official_html_manual_section",
        "index_url": "https://pamms.dhs.ga.gov/dfcs/medicaid/",
        "index_document_count": 241,
        "primary_source_url": "https://pamms.dhs.ga.gov/dfcs/medicaid/2194/",
        "notes": (
            "Georgia DFCS Medicaid Policy Manual (PAMMS): 241 numbered sections; the CHIP class of "
            "assistance is one section, '2194 PeachCare for Kids' (MT 79, effective May 2026). Taken. "
            "General Family Medicaid sections it cross-references (2160, 2182, 2215, 2610, 2650, "
            "Appendix A2) are Medicaid manual sections and were not taken. Reviewer judgment: "
            "citation path follows the work order (us-ga/manual/dfcs/chip/2194) rather than the "
            "existing us-ga/manual/dfcs/medicaid/NNNN convention used by us-ga-ssp-manual.yaml."
        ),
        "documents": [
            doc(
                "us-ga", "ga-dfcs-medicaid-2194-peachcare-for-kids",
                "Georgia Medicaid Policy Manual: 2194 PeachCare for Kids",
                "https://pamms.dhs.ga.gov/dfcs/medicaid/2194/",
                "us-ga/manual/dfcs/chip/2194", "html", "2026-05-01",
                subtype="policy_manual_section",
                authority="Georgia Department of Human Services, Division of Family and Children Services",
                request=IMPERSONATE,
                extraction={"html_content_selector": "article.doc"},
                metadata={"state_program": "PeachCare for Kids", "manual_transmittal": "MT 79",
                          "manual_landing_page": "https://pamms.dhs.ga.gov/dfcs/medicaid/"},
            ),
        ],
    },
    "us-ia": {
        "name": "Iowa",
        "document_class": "manual",
        "source_kind": "official_pdf_manual_chapter",
        "index_url": "https://hhs.iowa.gov/about/policy-manuals/income-maintenance",
        "index_document_count": 58,
        "primary_source_url": "https://hhs.iowa.gov/media/3983/download?inline",
        "notes": (
            "Iowa HHS Income Maintenance policy manuals index (58 Employees' Manual chapter/appendix "
            "PDFs across Titles 1, 4, 5, 6, 8, 13, 23, 24). The CHIP chapter is Title 5 Chapter E "
            "'Healthy and Well Kids in Iowa (hawk-i)' (93 pages, revised 2010-08-20 per its own TOC). "
            "Taken, page-level provisions. Title 8 Medicaid chapters were not taken. Reviewer "
            "judgment: the chapter's own revision date (2010) is old; Iowa's hawk-i rule 441 IAC "
            "chapter 86 (published by the Iowa Legislature) is a candidate follow-up."
        ),
        "documents": [
            doc(
                "us-ia", "ia-hhs-employees-manual-5-e-hawki",
                "Iowa HHS Employees' Manual Title 5 Chapter E: Healthy and Well Kids in Iowa (hawk-i)",
                "https://hhs.iowa.gov/media/3983/download?inline",
                "us-ia/manual/hhs/chip/employees-manual-5-e", "pdf", "2010-08-20",
                subtype="policy_manual_chapter_pdf",
                authority="Iowa Department of Health and Human Services",
                extraction=PAGES,
                metadata={"state_program": "hawk-i", "manual_title": "5", "manual_chapter": "E"},
            ),
        ],
    },
    "us-id": {
        "name": "Idaho",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_pdf",
        "index_url": "https://healthandwelfare.idaho.gov/services-programs/medicaid-health/childrens-health-insurance-program-chip",
        "index_document_count": 2,
        "primary_source_url": "https://adminrules.idaho.gov/rules/current/16/160301.pdf",
        "notes": (
            "IDHW CHIP program page links two policy documents: income guidelines (node/623) and "
            "'Notices and Proposed Rules'. The adopted eligibility rule is IDAPA 16.03.01 "
            "'Eligibility for Health Care Assistance for Families and Children' (Title XIX and XXI), "
            "served by the Office of the Administrative Rules Coordinator at "
            "adminrules.idaho.gov/rules/current/16/160301.pdf (redirects to files.dfm.idaho.gov; "
            "the Current Rules listing page itself is script-rendered). Taken, numbered sections, "
            "same shape as the existing us-id-aabd-rules.yaml (IDAPA 16.03.05)."
        ),
        "documents": [
            doc(
                "us-id", "id-dhw-idapa-16-03-01",
                "IDAPA 16.03.01 Eligibility for Health Care Assistance for Families and Children",
                "https://adminrules.idaho.gov/rules/current/16/160301.pdf",
                "us-id/regulation/idapa/16/03/01", "pdf", "2026-07-01",
                document_class="regulation",
                subtype="administrative_rules",
                authority="Idaho Department of Health and Welfare",
                extraction={
                    "segmentation": "numbered_sections",
                    "start_page": 5,
                    "sort_text": True,
                    "drop_lines": [
                        "IDAHO ADMINISTRATIVE CODE",
                        "Department of Health and Welfare",
                        "16.03.01 – ELIGIBILITY FOR HEALTH CARE ASSISTANCE FOR FAMILIES AND CHILDREN",
                    ],
                    "drop_line_patterns": [
                        r"^Section [0-9]+\s+Page [0-9]+.*$",
                        r"^Section [0-9]+$",
                        r"^Page [0-9]+$",
                        r"^IDAHO ADMINISTRATIVE CODE IDAPA 16\.03\.01.*$",
                        r"^Department of Health and Welfare Families (and|&) Children$",
                    ],
                },
                metadata={"idapa_chapter": "16.03.01", "state_program": "Idaho CHIP"},
            ),
        ],
    },
    "us-in": {
        "name": "Indiana",
        "document_class": "manual",
        "source_kind": "official_pdf_manual_chapter",
        "index_url": "https://www.in.gov/fssa/ompp/forms-documents-and-tools/medicaid-eligibility-policy-manual/",
        "index_document_count": 24,
        "primary_source_url": "https://www.in.gov/dA/4fd9875d6b/Medicaid_PM_1600.pdf?language_id=1",
        "notes": (
            "Indiana Health Coverage Program Policy Manual (IHCPPM) index: 24 chapter PDFs plus an "
            "all-chapters PDF and transmittals. Indiana runs a combined manual; CHIP is Hoosier "
            "Healthwise Package C / 'Children's Health Plan (MED 3)'. Taken: Chapter 1600 Categories "
            "of Assistance (defines the CHIP category, section 1620.72) and Chapter 3000 Eligibility "
            "Standards (income standards). Chapter 5000 is already in the corpus (us-in-ssp-sapn). "
            "Reviewer judgment: chapters 2800 Income and 3400 Budgeting also apply to CHIP but were "
            "not taken."
        ),
        "documents": [
            doc(
                "us-in", "in-fssa-ihcppm-chapter-1600",
                "Indiana Health Coverage Program Policy Manual Chapter 1600: Categories of Assistance",
                "https://www.in.gov/dA/4fd9875d6b/Medicaid_PM_1600.pdf?language_id=1",
                "us-in/manual/fssa/chip/ihcppm-chapter-1600", "pdf", "2026-06-19",
                subtype="medicaid_policy_manual",
                authority="Indiana Family and Social Services Administration, Office of Medicaid Policy and Planning",
                extraction={
                    "segmentation": "labeled_sections",
                    "section_heading_pattern": r"^(?P<label>[0-9]{4}\.[0-9]{2}\.[0-9]{2})(?:\s+(?P<heading>[A-Z][A-Z0-9 /()&',-]+))?\s*$",
                    "label_only_heading_pattern": r"^[A-Z][A-Z0-9 /()&',-]+\s*$",
                    "start_page": 3,
                    "drop_line_patterns": [
                        r"^\s*Indiana Health Coverage Program Policy Manual\s*$",
                        r"^\s*Chapter 1600\s*$",
                        r"^\s*[0-9]+\s*$",
                    ],
                },
                metadata={"state_program": "Hoosier Healthwise Package C", "manual_chapter": "1600"},
            ),
            doc(
                "us-in", "in-fssa-ihcppm-chapter-3000",
                "Indiana Health Coverage Program Policy Manual Chapter 3000: Eligibility Standards",
                "https://www.in.gov/dA/a7e1fb7d7d/Medicaid_PM_3000.pdf?language_id=1",
                "us-in/manual/fssa/chip/ihcppm-chapter-3000", "pdf", "2026-09-03",
                subtype="medicaid_policy_manual",
                authority="Indiana Family and Social Services Administration, Office of Medicaid Policy and Planning",
                extraction={
                    "segmentation": "labeled_sections",
                    "section_heading_pattern": r"^(?P<label>[0-9]{4}\.[0-9]{2}\.[0-9]{2})(?:\s+(?P<heading>[A-Z][A-Z0-9 /()&',-]+))?\s*$",
                    "label_only_heading_pattern": r"^[A-Z][A-Z0-9 /()&',-]+\s*$",
                    "start_page": 3,
                    "drop_line_patterns": [
                        r"^\s*Indiana Health Coverage Program Policy Manual\s*$",
                        r"^\s*Chapter 3000\s*$",
                        r"^\s*[0-9]+\s*$",
                    ],
                },
                metadata={"state_program": "Hoosier Healthwise Package C", "manual_chapter": "3000"},
            ),
        ],
    },
    "us-ma": {
        "name": "Massachusetts",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_pdf",
        "index_url": "https://www.mass.gov/law-library/130-cmr",
        "index_document_count": 2,
        "primary_source_url": "https://www.mass.gov/doc/130-cmr-505000-masshealth-coverage-types-5/download",
        "notes": (
            "MassHealth eligibility regulations on Mass.gov (130 CMR 501-522 member regulations). "
            "CHIP in Massachusetts is MassHealth Family Assistance / CommonHealth for children, "
            "governed by 130 CMR 505.000 Coverage Types (Trans. E.L. 254, rev. 2026-02-13) and "
            "130 CMR 506.000 Financial Requirements (E.L. 250, rev. 2026-01-30). Both taken from "
            "the regulation pages' official PDF downloads. The lead list's law.cornell.edu mirror "
            "of 130 CMR 506.011 was not used."
        ),
        "documents": [
            doc(
                "us-ma", "ma-eohhs-130-cmr-505",
                "130 CMR 505.000: MassHealth: Coverage Types",
                "https://www.mass.gov/doc/130-cmr-505000-masshealth-coverage-types-5/download",
                "us-ma/regulation/130-cmr/505", "pdf", "2026-02-13",
                document_class="regulation",
                subtype="administrative_regulation",
                authority="Massachusetts Executive Office of Health and Human Services, MassHealth",
                request=IMPERSONATE,
                extraction={
                    "segmentation": "labeled_sections",
                    "start_page": 2,
                    "section_heading_pattern": r"^505\.(?P<section>\d{3}):\s+(?P<heading>[^,]+|Medicare Savings Program \(MSP, also called Buy-in\))$",
                    "section_label_template": "{section}",
                    "drop_line_patterns": [
                        r"^130 CMR:\s+DIVISION OF MEDICAL ASSISTANCE$",
                        r"^Trans\. by E\.L\.",
                        r"^Rev\.",
                        r"^130 CMR 505\.000:",
                        r"^\d+$",
                    ],
                },
                metadata={"legal_identifier": "130 CMR 505.000",
                          "regulation_page": "https://www.mass.gov/regulations/130-CMR-505000-masshealth-coverage-types"},
            ),
            doc(
                "us-ma", "ma-eohhs-130-cmr-506",
                "130 CMR 506.000: MassHealth: Financial Requirements",
                "https://www.mass.gov/doc/130-cmr-506000-masshealth-financial-requirements-4/download",
                "us-ma/regulation/130-cmr/506", "pdf", "2026-01-30",
                document_class="regulation",
                subtype="administrative_regulation",
                authority="Massachusetts Executive Office of Health and Human Services, MassHealth",
                request=IMPERSONATE,
                extraction={
                    "segmentation": "labeled_sections",
                    "start_page": 2,
                    "section_heading_pattern": r"^506\.(?P<section>\d{3}):\s+(?P<heading>[^,]+)$",
                    "section_label_template": "{section}",
                    "drop_line_patterns": [
                        r"^130 CMR:\s+DIVISION OF MEDICAL ASSISTANCE$",
                        r"^Trans\. by E\.L\.",
                        r"^Rev\.",
                        r"^130 CMR 506\.000:",
                        r"^\d+$",
                    ],
                },
                metadata={"legal_identifier": "130 CMR 506.000",
                          "regulation_page": "https://www.mass.gov/regulations/130-CMR-506000-masshealth-financial-requirements"},
            ),
        ],
    },
    "us-mo": {
        "name": "Missouri",
        "document_class": "manual",
        "source_kind": "official_pdf_manual_appendix",
        "index_url": "https://dssmanuals.mo.gov/family-mo-healthnet-magi/",
        "index_document_count": 28,
        "primary_source_url": "https://dssmanuals.mo.gov/wp-content/uploads/2019/05/appendix-e.pdf",
        "notes": (
            "Missouri DSS Family MO HealthNet (MAGI) Manual index: 17 numbered sections "
            "(1800-1890) and 11 appendices. The CHIP section 1840.000.00 'MO HealthNet Children's "
            "Health Insurance Program (CHIP)' is password-protected on the publisher's site "
            "('This content is password-protected'), as are the other numbered sections. Taken: the "
            "two public CHIP appendices, Appendix A (MAGI income limits with 5% FPL and CHIP "
            "premium amounts, 7/1/2026-3/31/2027) and Appendix E (MO HealthNet for Kids CHIP "
            "Premium Chart effective 7/1/2026). Reviewer judgment: the manual section itself "
            "remains unavailable without publisher credentials; no workaround attempted."
        ),
        "documents": [
            doc(
                "us-mo", "mo-dss-magi-appendix-a",
                "Missouri Family MO HealthNet (MAGI) Manual Appendix A: MAGI Income With 5% of FPL Included and CHIP Premium Amounts",
                "https://dssmanuals.mo.gov/wp-content/uploads/2019/03/MAGIappendix-a.pdf",
                "us-mo/manual/dss/chip/magi-appendix-a", "pdf", "2026-07-01",
                subtype="policy_manual_appendix_pdf",
                authority="Missouri Department of Social Services, Family Support Division",
                request=IMPERSONATE,
                extraction=PAGES,
                metadata={"state_program": "MO HealthNet for Kids (CHIP)"},
            ),
            doc(
                "us-mo", "mo-dss-magi-appendix-e",
                "Missouri Family MO HealthNet (MAGI) Manual Appendix E: MO HealthNet for Kids CHIP Premium Chart",
                "https://dssmanuals.mo.gov/wp-content/uploads/2019/05/appendix-e.pdf",
                "us-mo/manual/dss/chip/magi-appendix-e", "pdf", "2026-07-01",
                subtype="policy_manual_appendix_pdf",
                authority="Missouri Department of Social Services, Family Support Division",
                request=IMPERSONATE,
                extraction=PAGES,
                metadata={"state_program": "MO HealthNet for Kids (CHIP)"},
            ),
        ],
    },
    "us-ny": {
        "name": "New York",
        "document_class": "manual",
        "source_kind": "official_agency_eligibility_pages",
        "index_url": "https://www.health.ny.gov/health_care/child_health_plus/",
        "index_document_count": 8,
        "primary_source_url": "https://www.health.ny.gov/health_care/child_health_plus/eligibility_and_cost.htm",
        "notes": (
            "NYSDOH Child Health Plus index: 8 program pages (eligibility and cost, benefits, where to "
            "go for care, health plans, how to apply, helpful links, contact, Spanish). Taken: "
            "'Eligibility and Cost' (the Department's published CHPlus eligibility and premium table, "
            "2026 FPL effective 2/17/2026). NYSDOH publishes no CHPlus eligibility manual and 10 NYCRR "
            "is vendor-hosted. Reviewer judgment: agency page recorded as document_class manual, "
            "subtype agency_eligibility_policy_page."
        ),
        "documents": [
            doc(
                "us-ny", "ny-doh-child-health-plus-eligibility-and-cost",
                "New York State Department of Health: Child Health Plus Eligibility and Cost",
                "https://www.health.ny.gov/health_care/child_health_plus/eligibility_and_cost.htm",
                "us-ny/manual/doh/chip/child-health-plus-eligibility-and-cost", "html", "2026-02-17",
                subtype="agency_eligibility_policy_page",
                authority="New York State Department of Health",
                request=IMPERSONATE,
                extraction={"html_content_selector": "#content"},
                metadata={"state_program": "Child Health Plus"},
            ),
        ],
    },
    "us-tx": {
        "name": "Texas",
        "document_class": "manual",
        "source_kind": "official_html_handbook_part",
        "index_url": "https://fhb.hhs.texas.gov/handbooks/texas-works-handbook/part-d-childrens-health-insurance-program",
        "index_document_count": 23,
        "primary_source_url": "https://fhb.hhs.texas.gov/book/export/html/75506",
        "notes": (
            "Texas Works Handbook (HHSC Forms and Handbooks site; www.hhs.texas.gov URLs now 301 to "
            "fhb.hhs.texas.gov). Part D Children's Health Insurance Program lists 23 top-level "
            "sections D-100 to D-2400 (each with subsections). Taken as the publisher's own "
            "printer-friendly export of Part D (one HTML document; sections are the export's "
            "comma-form page headings 'D-NNN, Title', one per handbook page, with the "
            "un-comma'd subsection headings such as D-121 or D—231.1 kept inside the page body "
            "because the export repeats some of them and the HTML extractor cannot merge repeats). The "
            "existing us-tx-manuals.yaml scope already holds D-1820 Enrollment Fees under "
            "us-tx/manual/hhs/texas-works-handbook/d-1820-enrollment-fees; it is superseded in "
            "content but not removed. Reviewer judgment: the D-210 heading is repeated in the export "
            "and is merged by drop_repeated_section_headings."
        ),
        "documents": [
            doc(
                "us-tx", "tx-hhsc-texas-works-handbook-part-d",
                "Texas Works Handbook Part D: Children's Health Insurance Program",
                "https://fhb.hhs.texas.gov/book/export/html/75506",
                "us-tx/manual/hhs/chip/texas-works-handbook-part-d", "html", SOURCE_AS_OF,
                subtype="policy_handbook_part",
                authority="Texas Health and Human Services Commission",
                request=IMPERSONATE,
                extraction={
                    "html_content_selector": "body",
                    "segmentation": "labeled_sections",
                    "section_heading_pattern": r"^D-(?P<num>\d{3,4}),\s+(?P<heading>\S.*)$",
                    "section_label_template": "d-{num}",
                },
                metadata={"state_program": "Texas CHIP and CHIP Perinatal",
                          "part_landing_page": "https://fhb.hhs.texas.gov/handbooks/texas-works-handbook/part-d-childrens-health-insurance-program"},
            ),
        ],
    },
}

# --- blocked publishers ---------------------------------------------------------------

BLOCKED: dict[str, dict] = {
    "us-fl": {
        "name": "Florida",
        "index_url": "https://www.floridakidcare.org/",
        "index_document_count": 14,
        "primary_source_url": "https://ahca.myflorida.com/medicaid/florida-kidcare",
        "notes": (
            "Blocked. The Title XXI agency page https://ahca.myflorida.com/medicaid/florida-kidcare "
            "returns HTTP 403 (Cloudflare 'Attention Required!') to a plain client, to a curl "
            "client and to the chrome120 browser-impersonation client. floridakidcare.org "
            "(Florida Healthy Kids Corporation; 14 consumer pages: about, benefits, cost, cost "
            "calculator, plan information, renew, requirements, FAQs, board, media, partner "
            "resources, notices, required reporting, contact) publishes no eligibility manual or "
            "adopted rule; the DCF ESS manual already in the corpus (us-fl/manual) has no KidCare "
            "chapter. Candidate follow-up: s. 409.814 F.S. from the Florida Legislature."
        ),
    },
    "us-ks": {
        "name": "Kansas",
        "index_url": "https://www.kancare.ks.gov/policies-and-reports/eligibility-policy",
        "index_document_count": None,
        "primary_source_url": "https://www.kancare.ks.gov/policies-and-reports/eligibility-policy",
        "notes": (
            "Blocked. The Kansas Family Medical Assistance Manual (KFMAM) publisher "
            "www.kancare.ks.gov returns HTTP 403 'Access Denied' for the eligibility-policy index, "
            "the KFMAM page and the site root, to plain, curl and chrome120-impersonated clients; "
            "www.kdhe.ks.gov also returns 403. The existing us-ks KEESM scope (DCF) is SNAP/TANF and "
            "has no CHIP chapter."
        ),
    },
    "us-la": {
        "name": "Louisiana",
        "index_url": "https://ldh.la.gov/page/medicaid-eligibility-manual",
        "index_document_count": None,
        "primary_source_url": "https://ldh.la.gov/page/medicaid-eligibility-manual",
        "notes": (
            "Blocked. ldh.la.gov (Louisiana Medicaid Eligibility Manual, LaCHIP) returns HTTP 403 "
            "(Cloudflare 'Attention Required!') for the manual page and the site root, to plain, "
            "curl and chrome120-impersonated clients. The existing us-la SNAP manual came from "
            "public.powerdms.com (DCFS), which does not host the LDH Medicaid manual."
        ),
    },
    "us-wi": {
        "name": "Wisconsin",
        "index_url": "https://www.emhandbooks.wisconsin.gov/bcplus/bcplus.htm",
        "index_document_count": None,
        "primary_source_url": "https://www.emhandbooks.wisconsin.gov/bcplus/bcplus.htm",
        "notes": (
            "Blocked. The BadgerCare Plus Eligibility Handbook host www.emhandbooks.wisconsin.gov "
            "(165.189.157.19) did not accept TCP connections on 443 or 80 during this run "
            "(curl: (28) connection timeout after 20-60 s on three attempts; WebFetch "
            "ECONNREFUSED); www.dhs.wisconsin.gov answered normally. The same host served the "
            "FoodShare handbook for us-wi-foodshare-manual.yaml in July 2026, so this may be "
            "transient; retry before treating as a durable block."
        ),
    },
}

# --- jurisdictions already covered by existing corpus scopes ------------------------------

DONE: dict[str, dict] = {
    "us": {
        "name": "Federal",
        "index_url": "https://www.medicaid.gov/chip",
        "index_document_count": 15,
        "target_manifest": "manifests/us-cms-chip-fcep-spa-official-documents.yaml; manifests/us-cms-chip-children-coverage-map-official-documents.yaml; manifests/us-medicaid-chip-eligibility-levels.yaml",
        "target_scope": {"jurisdiction": "us", "document_class": "regulation", "version": "2026-07-13-recovery-r2026-07-17-dedup"},
        "notes": (
            "Done; nothing re-ingested. CMS CHIP index (15 sections: state program information, CHIP "
            "SPAs, benefits, CCTAG, cost sharing, eligibility & enrollment with waiting periods / "
            "continuous eligibility / enrollment strategies / substitution strategies, financing, "
            "managed care, quality, reports & evaluations, guidance & regulations). Already in the "
            "corpus: CHIP SPAs and children coverage map (us/policy), the Medicaid/CHIP/BHP "
            "eligibility levels table (us/form), Title XXI (us/statute, docs/ingest-runs/"
            "2026-06-26-chip-title-xxi.md), and 42 CFR part 457 (171 provisions, subparts A-L, in "
            "us/regulation version 2026-07-13-recovery-r2026-07-17-dedup, coverage complete). The "
            "remaining CMS index sections are explanatory web pages or SHO/CIB guidance families, "
            "not a primary CHIP policy document; none taken."
        ),
    },
    "us-il": {
        "name": "Illinois",
        "index_url": "https://hfs.illinois.gov/medicalprograms/allkids.html",
        "index_document_count": 14,
        "target_manifest": "manifests/us-il-snap-manual.yaml",
        "target_scope": {"jurisdiction": "us-il", "document_class": "manual", "version": "2026-05-27-il-cash-snap-medical-manual-r2026-07-15-self-contained"},
        "notes": (
            "Done by pointer (reviewer judgment). HFS All Kids index (14 program pages) links no "
            "policy manual; All Kids (Medicaid and CHIP) eligibility is governed by the IDHS Cash, "
            "SNAP and Medical Manual, which is already ingested in full (12,450 provisions at "
            "us-il/manual/dhs/csmm/*, including PM 04-02 Family Health Plans cases, PM 15-06-01-d "
            "All Kids Assist Standard, PM 06-24-07 Premiums and Co-Pays, WAG 06-08-14 All Kids Forms). "
            "No separate CHIP manual exists to add."
        ),
    },
    "us-mi": {
        "name": "Michigan",
        "index_url": "https://mdhhs-pres-prod.michigan.gov/OLMWeb/ex/BP/Public/BEM/000.pdf",
        "index_document_count": 196,
        "target_manifest": "manifests/us-mi-bridges-manual.yaml",
        "target_scope": {"jurisdiction": "us-mi", "document_class": "manual", "version": "2026-07-17-mi-bridges-manual"},
        "notes": (
            "Done by pointer (reviewer judgment). MIChild (Michigan CHIP) eligibility is BEM 130 "
            "MICHILD (BPB 2024-001) and BEM 131 Healthy Kids of the Bridges Eligibility Manual, both "
            "already ingested in us-mi-bridges-manual.yaml (us-mi/manual/mdhhs/bridges/bem/130 with "
            "three page provisions; the document root record has an empty body, text is on the "
            "page children). Not duplicated."
        ),
    },
}



# --- batch 2 (2026-09-10): next ten states by population, plus pulls ----------------------
#
# Batch 2 took the ten most populous states not yet in the queue (CA, PA, OH, NC, NJ, VA, WA,
# AZ, TN, MD). NC, NJ and VA were already covered by the combined Medicaid eligibility manuals
# ingested by the parallel Medicaid run (same corpus root), so CO, MN and SC were pulled next.
# See docs/ingest-runs/2026-09-10-chip-state-eligibility-manuals-batch-2.md.

BATCH2_DISCOVERED_VIA = (
    "manual-review:chip-agent-queue batch 2; publisher index confirmed by agent 2026-09-10"
)
RETRIED_AT = "2026-09-10T18:39Z"
# Batch-1 blocked rows, retried once (one plain request, one chrome120 request, 25 s timeouts).
RETRY_NOTES: dict[str, str] = {
    "us-fl": f"retried {RETRIED_AT}, same failure (HTTP 403 Cloudflare 'Attention Required!' plain and chrome120).",
    "us-ks": f"retried {RETRIED_AT}, same failure (HTTP 403 'Access Denied' plain and chrome120).",
    "us-la": f"retried {RETRIED_AT}, same failure (HTTP 403 Cloudflare 'Attention Required!' plain and chrome120).",
    "us-wi": f"retried {RETRIED_AT}, same failure (TCP connect timeout after 25 s on 443, plain and chrome120).",
}

NEW_ROW_NAMES: dict[str, str] = {
    "us-az": "Arizona", "us-ca": "California", "us-co": "Colorado", "us-md": "Maryland",
    "us-mn": "Minnesota", "us-nc": "North Carolina", "us-nj": "New Jersey", "us-oh": "Ohio",
    "us-pa": "Pennsylvania", "us-sc": "South Carolina", "us-tn": "Tennessee", "us-va": "Virginia",
    "us-wa": "Washington",
}

NEVER_CONTINUE = "(?!)"  # heading_continuation_pattern that never matches: headings are one line

MD_COMAR_10_09_11_SECTIONS: dict[str, str] = {
    "01": "Purpose and Scope",
    "02": "Definitions",
    "03": "Coverage Groups",
    "04": "Application",
    "05": "Application: Additional Requirements",
    "06": "Nonfinancial Eligibility Requirements",
    "07": "Consideration of Household Income",
    "08": "Consideration of Family Income: Earned and Unearned Income (Repealed)",
    "09": "Consideration of Family Income: Income Disregards (Repealed)",
    "10": "Determining Financial Eligibility",
    "11": "Certification Periods",
    "12": "Covered Services",
    "13": "Post-Eligibility Requirements",
    "14": "Hearings",
    "15": "Fraud and Abuse",
    "16": "Adjustments and Recoveries",
    "17": "Interpretive Regulation",
}


def _md_comar_doc(num: str, title: str) -> dict:
    d = doc(
        "us-md", f"md-mdh-comar-10-09-11-{num}",
        f"COMAR 10.09.11.{num} {title}",
        f"https://regs.maryland.gov/us/md/exec/comar/10.09.11.{num}",
        f"us-md/regulation/title-10/subtitle-09/chapter-11/regulation-{num}", "html", "2026-04-13",
        document_class="regulation",
        subtype="administrative_regulation_section",
        authority="Maryland Department of Health (COMAR Title 10), published by the Maryland Division of State Documents",
        extraction={"html_content_selector": "article.content"},
        metadata={"legal_identifier": f"COMAR 10.09.11.{num}", "state_program": "Maryland Children's Health Program",
                  "chapter_page": "https://regs.maryland.gov/us/md/exec/comar/10.09.11",
                  "repealed": title.endswith("(Repealed)")},
    )
    d["metadata"]["discovered_via"] = BATCH2_DISCOVERED_VIA
    return d


CONFIRMED_BATCH2: dict[str, dict] = {
    "us-pa": {
        "name": "Pennsylvania",
        "document_class": "manual",
        "source_kind": "official_pdf_policy_handbook",
        "index_url": "https://www.pa.gov/agencies/dhs/resources/chip/chip-resources",
        "index_document_count": 16,
        "index_families": {"agency_policy_handbook_pdf": 2, "chip_state_plan_pdf": 1,
                           "privacy_notice_pdf": 1, "program_web_page": 12},
        "primary_source_url": "https://www.pa.gov/content/dam/copapwp-pagov/en/dhs/documents/chip/eligibility-and-benefits/documents/chip-enrollment-and-benefits-handbook.pdf",
        "notes": (
            "PA DHS CHIP Resources index: 16 documents (2 agency policy handbooks: CHIP Enrollment "
            "and Benefits Handbook released 2026-01-01, CHIP Procedures Handbook January 2026; the "
            "CHIP State Plan PDF (September 2026); the CHIP privacy notice; 12 CHIP program web pages). "
            "Taken 1: the Enrollment and Benefits Handbook (Part 1 eligibility, enrollment and cost "
            "sharing; Part 2 benefits), chapter-level sections. Not taken: the Procedures Handbook "
            "(148 pages of MCO operating procedures: COMPASS, quality management, marketing, "
            "administration), the state plan (state-plan family; CMS CHIP SPAs are already in the "
            "corpus), the privacy notice. The Medicaid run's MA Eligibility Handbook section 309.6 "
            "(us-pa/manual/dhs/medicaid/309-...) only refers applicants to CHIP. Reviewer judgments: "
            "sections are chapters because the publisher's subsection labels repeat (2.1 appears three "
            "times), and the glossary (page 5) precedes the first chapter and is not captured."
        ),
        "documents": [
            doc(
                "us-pa", "pa-dhs-chip-enrollment-and-benefits-handbook",
                "Pennsylvania DHS Children's Health Insurance Program (CHIP) Enrollment and Benefits Handbook",
                "https://www.pa.gov/content/dam/copapwp-pagov/en/dhs/documents/chip/eligibility-and-benefits/documents/chip-enrollment-and-benefits-handbook.pdf",
                "us-pa/manual/dhs/chip/enrollment-and-benefits-handbook", "pdf", "2026-01-01",
                subtype="policy_handbook_pdf",
                authority="Pennsylvania Department of Human Services",
                extraction={
                    "segmentation": "labeled_sections",
                    "start_page": 6,
                    "section_heading_pattern": r"^CHAPTER (?P<num>\d+):\s+(?P<heading>[A-Z].*?)\s*$",
                    "section_label_template": "chapter-{num}",
                    "heading_continuation_pattern": NEVER_CONTINUE,
                    "drop_line_patterns": [r"^\s*Released January 1, 2026\s*$", r"^\s*\d{1,2}\s*$"],
                },
                metadata={"state_program": "Pennsylvania CHIP", "released": "2026-01-01"},
            ),
        ],
    },
    "us-wa": {
        "name": "Washington",
        "document_class": "manual",
        "source_kind": "official_html_manual_chapter",
        "index_url": "https://www.hca.wa.gov/free-or-low-cost-health-care/i-help-others-apply-and-access-apple-health/modified-adjusted-gross-income-magi-based-programs-manual",
        "index_document_count": 16,
        "index_families": {"magi_program_chapter": 9, "magi_financial_eligibility_chapter": 3,
                           "magi_client_notice_chapter": 4},
        "primary_source_url": "https://www.hca.wa.gov/free-or-low-cost-health-care/i-help-others-apply-and-access-apple-health/apple-health-kids-and-without-premiums",
        "notes": (
            "Washington HCA Apple Health Eligibility Manual, MAGI-based programs manual index: 16 "
            "chapters (9 program chapters, 3 financial-eligibility chapters, 4 client-notice chapters). "
            "CHIP in Washington is premium-based Apple Health for Kids; taken 1: 'Apple Health for "
            "Kids, with and without premiums' (revised 2026-04-01), which carries WAC 182-505-0210, "
            "182-505-0215 and 182-505-0225 with HCA clarifying information, sectioned by WAC. The "
            "accordion title copies of each WAC heading are dropped (dl.ckeditor-accordion > dt) so "
            "each WAC appears once. Not taken: Household composition, Income (parts 1-2) and the "
            "other program chapters (Medicaid)."
        ),
        "documents": [
            doc(
                "us-wa", "wa-hca-apple-health-for-kids",
                "Washington Apple Health Eligibility Manual: Apple Health for Kids, with and without premiums",
                "https://www.hca.wa.gov/free-or-low-cost-health-care/i-help-others-apply-and-access-apple-health/apple-health-kids-and-without-premiums",
                "us-wa/manual/hca/chip/apple-health-for-kids", "html", "2026-04-01",
                subtype="eligibility_manual_chapter",
                authority="Washington State Health Care Authority",
                extraction={
                    "html_content_selector": "div.region-content",
                    "html_drop_selectors": ["dl.ckeditor-accordion > dt"],
                    "segmentation": "labeled_sections",
                    "section_heading_pattern": r"^(?P<heading>WAC (?P<num>182-505-\d{4})\s+\S.*)$",
                    "section_label_template": "wac-{num}",
                },
                metadata={"state_program": "Apple Health for Kids with premiums (CHIP)",
                          "wac_sections": ["182-505-0210", "182-505-0215", "182-505-0225"]},
            ),
        ],
    },
    "us-tn": {
        "name": "Tennessee",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_pdf",
        "index_url": "https://publications.tnsosfiles.com/rules/1200/1200-13/1200-13.htm",
        "index_document_count": 22,
        "index_families": {"tenncare_rule_chapter_pdf": 22},
        "primary_source_url": "https://publications.tnsosfiles.com/rules/1200/1200-13/1200-13-21.20250202.pdf",
        "notes": (
            "Tennessee Secretary of State, Division of Publications, effective rules index for "
            "Chapter 1200-13 (Division of TennCare): 22 rule chapters 1200-13-01 through 1200-13-22. "
            "Taken 1: 1200-13-21 CoverKids (Tennessee's separate CHIP), February 2025 revision, rules "
            ".01-.10. Not taken: 1200-13-20 TennCare Eligibility (Medicaid) and the other chapters. "
            "tn.gov (TennCare eligibility policy page) returns HTTP 403 to plain and chrome120 clients; "
            "publications.tnsosfiles.com returns 403 to a plain client and 200 with browser "
            "impersonation. Citation path follows the existing us-tn/regulation/1240-01/02/01 "
            "convention (chapter 1200-13 / rule chapter 21 / rule NN)."
        ),
        "documents": [
            doc(
                "us-tn", "tn-tenncare-rules-1200-13-21-coverkids",
                "Rules of the Tennessee Department of Finance and Administration, Division of TennCare, Chapter 1200-13-21 CoverKids",
                "https://publications.tnsosfiles.com/rules/1200/1200-13/1200-13-21.20250202.pdf",
                "us-tn/regulation/1200-13/21", "pdf", "2025-02-02",
                document_class="regulation",
                subtype="administrative_rules_chapter",
                authority="Tennessee Department of Finance and Administration, Division of TennCare",
                request=IMPERSONATE,
                extraction={
                    "segmentation": "labeled_sections",
                    "section_heading_pattern": r"^1200-13-21-\.(?P<num>\d{2})\s+(?P<heading>[A-Z][A-Z0-9 ,'&/()-]*?)\.(?:\s+(?P<body>\S.*))?\s*$",
                    "section_label_template": "{num}",
                    "heading_continuation_pattern": NEVER_CONTINUE,
                    "drop_lines": ["COVERKIDS", "CHAPTER 1200-13-21"],
                    "drop_line_patterns": [
                        r"^\(Rule 1200-13-21-\.\d{2}, continued\)\s*$",
                        r"^[A-Z][a-z]+, \d{4}(?: \(Revised\))?\s*$",
                        r"^\d{1,2}\s*$",
                    ],
                },
                metadata={"state_program": "CoverKids", "rule_chapter": "1200-13-21",
                          "sos_revision": "February, 2025 (Revised)"},
            ),
        ],
    },
    "us-md": {
        "name": "Maryland",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_html",
        "index_url": "https://regs.maryland.gov/us/md/exec/comar/10.09.11",
        "index_document_count": 17,
        "index_families": {"comar_regulation_section_html_in_force": 15,
                           "comar_regulation_section_html_repealed": 2},
        "primary_source_url": "https://regs.maryland.gov/us/md/exec/comar/10.09.11",
        "notes": (
            "COMAR 10.09.11 Maryland Children's Health Program (MCHP, Maryland's CHIP), chapter page "
            "on the Division of State Documents' COMAR site regs.maryland.gov (dsd.maryland.gov "
            "redirects there with HTTP 301; the site is operated for DSD by Open Law Library and "
            "states State of Maryland copyright). 17 regulation sections .01-.17, two repealed (.08, "
            ".09); all 17 taken as one HTML document each, citation paths following the existing "
            "us-md/regulation/title-07/subtitle-03/chapter-03/regulation-NN convention. Chapter "
            "revised 2014-01-06; latest amendment .11D effective 2026-04-13 (used as expression_date "
            "for all sections). Reviewer judgments: the site asks visitors to use its bulk HTML/XML "
            "downloads (GitHub maryland-dsd) instead of scraping; 17 page fetches were made directly. "
            "The Maryland Medical Assistance eligibility manual was not located on mdh.maryland.gov."
        ),
        "documents": [_md_comar_doc(num, title) for num, title in MD_COMAR_10_09_11_SECTIONS.items()],
    },
    "us-co": {
        "name": "Colorado",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_pdf",
        "index_url": "https://www.sos.state.co.us/CCR/NumericalCCRDocList.do?deptID=7&agencyID=69",
        "index_document_count": 22,
        "index_families": {"ccr_rule_document_chp_plus": 1, "ccr_rule_document_medical_assistance": 21},
        "primary_source_url": "https://www.sos.state.co.us/CCR/GenerateRulePdf.do?ruleVersionId=12479&fileName=10%20CCR%202505-3",
        "notes": (
            "Colorado Secretary of State, Code of Colorado Regulations, HCPF Medical Services Board "
            "rule list: 22 CCR documents (10 CCR 2505-3 and 21 parts of 10 CCR 2505-10 Medical "
            "Assistance). Taken 1: 10 CCR 2505-3, the Children's Basic Health Plan (Child Health Plan "
            "Plus) rule, current version effective 2026-04-14 (ruleVersionId 12479; rule info page "
            "DisplayRule.do?action=ruleinfo&ruleId=2816), sectioned by the rule's numbered sections "
            "50-610 (the SOS listing titles it 'Financial Management of the Children's Basic Health "
            "Plan'; the text covers eligibility, benefits, cost sharing, enrollment, financial "
            "management and appeals). Sections 210 and 510 have no title line; their first sentence "
            "serves as heading. hcpf.colorado.gov returns HTTP 403 (CloudFront) and was not used. "
            "Citation path follows the existing us-co/regulation/10-ccr-2506-1 convention."
        ),
        "documents": [
            doc(
                "us-co", "co-hcpf-10-ccr-2505-3",
                "10 CCR 2505-3 Financial Management of the Children's Basic Health Plan (Child Health Plan Plus rules)",
                "https://www.sos.state.co.us/CCR/GenerateRulePdf.do?ruleVersionId=12479&fileName=10%20CCR%202505-3",
                "us-co/regulation/10-ccr-2505-3", "pdf", "2026-04-14",
                document_class="regulation",
                subtype="code_of_colorado_regulations_rule",
                authority="Colorado Department of Health Care Policy and Financing, Medical Services Board",
                extraction={
                    "segmentation": "labeled_sections",
                    "section_label_pattern": r"^(?P<label>50|[1-6][0-9]0)\s*$",
                    "label_only_heading_pattern": r"^\S.*$",
                    "heading_continuation_pattern": NEVER_CONTINUE,
                    "drop_lines": [
                        "CODE OF COLORADO REGULATIONS",
                        "10 CCR 2505-3",
                        "Medical Services Board",
                        "DEPARTMENT OF HEALTH CARE POLICY AND FINANCING",
                    ],
                    "drop_line_patterns": [r"^(?:[1-9]|[1-4][0-9])\s*$"],
                },
                metadata={"state_program": "Child Health Plan Plus (CHP+)", "ccr_series": "10 CCR 2505-3",
                          "rule_version_id": "12479", "effective_date": "2026-04-14",
                          "rule_info_url": "https://www.sos.state.co.us/CCR/DisplayRule.do?action=ruleinfo&ruleId=2816&deptID=7&agencyID=69"},
            ),
        ],
    },
    "us-mn": {
        "name": "Minnesota",
        "document_class": "manual",
        "source_kind": "official_html_manual_section",
        "index_url": "https://hcopub.dhs.state.mn.us/epm/2_2.htm",
        "index_document_count": 23,
        "index_families": {"epm_ma_fca_topic": 23},
        "primary_source_url": "https://hcopub.dhs.state.mn.us/epm/2_2_3_3.htm",
        "notes": (
            "Minnesota DHS Health Care Programs Eligibility Policy Manual (EPM), chapter 2.2 Medical "
            "Assistance for Families with Children and Adults (MA-FCA) index: 23 topic pages (general "
            "requirements, non-financial eligibility, financial eligibility, post-eligibility). "
            "Minnesota's CHIP is Medicaid-expansion CHIP (Title XXI-funded MA for infants 275-283% "
            "FPG and pregnant people; MinnesotaCare is a Basic Health Program, not CHIP), so there is "
            "no separate CHIP manual. Taken 2: 2.2.2.1 MA-FCA Bases of Eligibility (published "
            "2026-06-03) and 2.2.3.3 MA-FCA Income Limit (published 2018-12-01; names the CHIP-funded "
            "infant band). The RoboHelp topic body (#rh-topic) is taken as blocks. Reviewer judgment: "
            "the remaining MA-FCA topics (household composition, income methodology) also apply."
        ),
        "documents": [
            doc(
                "us-mn", "mn-dhs-epm-2-2-2-1",
                "Minnesota EPM 2.2.2.1 MA-FCA Bases of Eligibility",
                "https://hcopub.dhs.state.mn.us/epm/2_2_2_1.htm",
                "us-mn/manual/dhs/chip/epm-2-2-2-1", "html", "2026-06-03",
                subtype="eligibility_policy_manual_topic",
                authority="Minnesota Department of Human Services",
                extraction={"html_content_selector": "#rh-topic"},
                metadata={"state_program": "Medical Assistance for Families with Children and Adults (CHIP-funded infants and pregnant people)",
                          "epm_section": "2.2.2.1"},
            ),
            doc(
                "us-mn", "mn-dhs-epm-2-2-3-3",
                "Minnesota EPM 2.2.3.3 MA-FCA Income Limit",
                "https://hcopub.dhs.state.mn.us/epm/2_2_3_3.htm",
                "us-mn/manual/dhs/chip/epm-2-2-3-3", "html", "2018-12-01",
                subtype="eligibility_policy_manual_topic",
                authority="Minnesota Department of Human Services",
                extraction={"html_content_selector": "#rh-topic"},
                metadata={"state_program": "Medical Assistance for Families with Children and Adults (CHIP-funded infants and pregnant people)",
                          "epm_section": "2.2.3.3"},
            ),
        ],
    },
}
for _spec in CONFIRMED_BATCH2.values():
    for _d in _spec["documents"]:
        _d["metadata"]["discovered_via"] = BATCH2_DISCOVERED_VIA

BLOCKED_BATCH2: dict[str, dict] = {
    "us-ca": {
        "name": "California",
        "index_url": "https://www.dhcs.ca.gov/services/medi-cal/eligibility/Pages/MEPM.aspx",
        "index_document_count": None,
        "primary_source_url": "https://www.dhcs.ca.gov/services/medi-cal/eligibility/Pages/MEPM.aspx",
        "notes": (
            "Blocked. California's CHIP is Title XXI-funded Medi-Cal for children (Optional Targeted "
            "Low-Income Children) plus MCAP and county CCHIP; the eligibility manual is the DHCS "
            "Medi-Cal Eligibility Procedures Manual. www.dhcs.ca.gov returns HTTP 403 with an empty "
            "772-byte body for the MEPM index and for the site root, to a plain client, the WebFetch "
            "client and the chrome120 browser-impersonation client. 22 CCR is vendor-hosted (Westlaw) "
            "and was not used. No existing us-ca scope carries Medi-Cal or CHIP eligibility text. 0 taken."
        ),
    },
    "us-oh": {
        "name": "Ohio",
        "index_url": "https://codes.ohio.gov/ohio-administrative-code/chapter-5160:1-4",
        "index_document_count": None,
        "primary_source_url": "https://codes.ohio.gov/ohio-administrative-code/chapter-5160:1-4",
        "notes": (
            "Blocked. Ohio's CHIP is Medicaid-expansion CHIP whose eligibility rules are the adopted "
            "rules in OAC Chapter 5160:1-4 (MAGI-based Medicaid: children, families and adults) "
            "published by the Legislative Service Commission at codes.ohio.gov. codes.ohio.gov did "
            "not accept TCP connections on 443 during this run (requests ConnectTimeout after 25 s "
            "plain; curl (28) connection timed out after 25 s with chrome120 impersonation; WebFetch "
            "ECONNREFUSED 198.234.74.32:443), and emanuals.jfs.ohio.gov timed out the same way. "
            "medicaid.ohio.gov answered (HTTP 200) but publishes no eligibility manual, only consumer "
            "coverage pages and managed-care policy. codes.ohio.gov served us-oh-snap-rules.yaml "
            "(OAC 5101:4) in July 2026, so this is probably transient; retry before treating the "
            "block as durable. 0 taken."
        ),
    },
    "us-az": {
        "name": "Arizona",
        "index_url": "https://epm.azahcccs.gov/",
        "index_document_count": None,
        "primary_source_url": "https://epm.azahcccs.gov/",
        "notes": (
            "Blocked. AHCCCS publishes the Medical Assistance Eligibility Policy Manual (KidsCare is "
            "its chapter 408) at epm.azahcccs.gov; that host, www.azahcccs.gov (AMPM index, program "
            "pages) and the site root all return HTTP 403 Forbidden to plain, WebFetch and chrome120 "
            "clients. The adopted KidsCare rule A.A.C. Title 9 Chapter 31 at the Arizona Secretary of "
            "State (apps.azsos.gov/public_services/Title_09/9-31.pdf) returns a Cloudflare JavaScript "
            "challenge ('Just a moment...', HTTP 403). 0 taken."
        ),
    },
    "us-sc": {
        "name": "South Carolina",
        "index_url": "https://img1.scdhhs.gov/mppm/",
        "index_document_count": None,
        "primary_source_url": "https://img1.scdhhs.gov/mppm/",
        "notes": (
            "Blocked. South Carolina's CHIP (Partners for Healthy Children) is Medicaid-expansion CHIP "
            "governed by the SCDHHS Medicaid Policy and Procedures Manual (MPPM; Chapter 204 Healthy "
            "Connections Plans for Children), published at img1.scdhhs.gov/mppm/ and "
            "www1.scdhhs.gov/mppm/. Both hosts present their leaf certificate without the issuing "
            "intermediate (Go Daddy Secure Certificate Authority - G2); the chain was repaired with the "
            "publisher's public intermediate fetched from the leaf's AIA URL "
            "(data/certs/godaddy-secure-certificate-authority-g2.pem) via REQUESTS_CA_BUNDLE, TLS "
            "verification never disabled. With the chain verified, both hosts return HTTP 403 'Error "
            "Page' to plain and chrome120 clients, and www.scdhhs.gov (CloudFront) returns HTTP 403 "
            "'The request could not be satisfied' for its policy index pages. 0 taken."
        ),
    },
}

MEDICAID_RUN_VERSION = "2026-09-10-medicaid-state-eligibility-manual"
MEDICAID_RUN_NOTE = (
    "Manifest lives on the parallel Medicaid branch (discovery/ingest-medicaid); artifacts share "
    "data/corpus in the main checkout."
)

DONE_BATCH2: dict[str, dict] = {
    "us-nc": {
        "name": "North Carolina",
        "index_url": "https://policies.ncdhhs.gov/divisional/health-benefits-nc-medicaid/family-and-childrens-medicaid/",
        "index_document_count": 64,
        "target_manifest": f"discovery/ingest-medicaid: us-nc/manual {MEDICAID_RUN_VERSION}",
        "target_scope": {"jurisdiction": "us-nc", "document_class": "manual", "version": MEDICAID_RUN_VERSION},
        "pointer": "us-nc/manual/dhb/medicaid/ma-3xxx (Family and Children's Medicaid manual, 64 documents incl. fcm table of contents)",
        "notes": (
            "Done by pointer (reviewer judgment). NC Health Choice, the separate CHIP, was folded into "
            "NC Medicaid on 2023-04-01; CHIP-funded children are determined under the Family and "
            "Children's Medicaid manual (MA-3xxx), which the parallel Medicaid run ingested in full on "
            "2026-09-10 (64 F&C documents at us-nc/manual/dhb/medicaid/ma-3100 ... ma-3570 plus the "
            "fcm table of contents, version " + MEDICAID_RUN_VERSION + "). " + MEDICAID_RUN_NOTE +
            " policies.ncdhhs.gov returns HTTP 403 to the WebFetch client; the index count is the "
            "Medicaid run's inventory. Nothing separate to add."
        ),
    },
    "us-nj": {
        "name": "New Jersey",
        "index_url": "https://www.nj.gov/humanservices/notices/documents/rules-and-regulations/",
        "index_document_count": 6,
        "target_manifest": f"discovery/ingest-medicaid: us-nj/manual {MEDICAID_RUN_VERSION}",
        "target_scope": {"jurisdiction": "us-nj", "document_class": "manual", "version": MEDICAID_RUN_VERSION},
        "pointer": "us-nj/manual/dhs/medicaid/njac-10-79 (N.J.A.C. 10:79 NJ FamilyCare-Children's Program, 115 page provisions)",
        "notes": (
            "Done by pointer (reviewer judgment). New Jersey's CHIP eligibility rule is N.J.A.C. 10:79 "
            "NJ FamilyCare-Children's Program (DHS/DMAHS rules-and-regulations PDF set: 10:69, 10:70, "
            "10:71, 10:72, 10:78, 10:79), already ingested by the parallel Medicaid run on 2026-09-10 "
            "at us-nj/manual/dhs/medicaid/njac-10-79 (115 page provisions, version "
            + MEDICAID_RUN_VERSION + "). " + MEDICAID_RUN_NOTE + " The HTML index page for that PDF "
            "folder was not re-located in this run (three candidate DHS URLs returned 404); the "
            "folder listing count is the Medicaid run's inventory. Nothing separate to add."
        ),
    },
    "us-va": {
        "name": "Virginia",
        "index_url": "https://www.dmas.virginia.gov/for-providers/eligibility-manual/",
        "index_document_count": 21,
        "target_manifest": f"discovery/ingest-medicaid: us-va/manual {MEDICAID_RUN_VERSION}",
        "target_scope": {"jurisdiction": "us-va", "document_class": "manual", "version": MEDICAID_RUN_VERSION},
        "pointer": "us-va/manual/dmas/medicaid/m21 (Chapter M21 FAMIS, 22 provisions; also m22 FAMIS MOMS, m23 FAMIS Prenatal)",
        "notes": (
            "Done by pointer (reviewer judgment). Virginia's CHIP (FAMIS) eligibility is Chapter M21 "
            "FAMIS of the DMAS Virginia Medical Assistance Eligibility Manual, with M22 FAMIS MOMS and "
            "M23 FAMIS Prenatal Coverage; all three were ingested by the parallel Medicaid run on "
            "2026-09-10 (21 manual chapters, us-va/manual/dmas/medicaid/m21 has 22 provisions, version "
            + MEDICAID_RUN_VERSION + "). " + MEDICAID_RUN_NOTE + " Nothing separate to add."
        ),
    },
}


# --- batch 3 (docs/ingest-runs/2026-09-10-chip-state-eligibility-manuals-batch-3.md) -----------
# Next ten states by population not in the queue (KY, OR, OK, UT, NV, AR, MS, NM, NE, WV) with
# replacements HI, NH, ME, MT, RI, SD. AR and WV are already covered by combined manuals in the
# corpus; OR, NE, HI, NH, UT and MT publishers blocked on the first probe (see BLOCKED_BATCH3).

BATCH3_DISCOVERED_VIA = (
    "manual-review:chip-agent-queue batch 3; publisher index confirmed by agent 2026-09-10"
)

NEW_ROW_NAMES_BATCH3: dict[str, str] = {
    "us-ar": "Arkansas", "us-hi": "Hawaii", "us-ky": "Kentucky", "us-me": "Maine",
    "us-ms": "Mississippi", "us-mt": "Montana", "us-ne": "Nebraska", "us-nh": "New Hampshire",
    "us-nm": "New Mexico", "us-nv": "Nevada", "us-ok": "Oklahoma", "us-or": "Oregon",
    "us-ri": "Rhode Island", "us-sd": "South Dakota", "us-ut": "Utah", "us-wv": "West Virginia",
}

OK_OHCA_SUBCHAPTER_6_INDEX = (
    "https://oklahoma.gov/ohca/policies-and-rules/xpolicy/"
    "medical-assistance-for-adults-and-children-eligibility/"
    "soonercare-for-pregnant-women-and-families-with-children.html"
)
OK_RULES_API_317_35 = (
    "https://prod-ok-rules-api.tecuity.com/GetSegmentsByChapterNum?titleNum=317&chapterNum=35"
)
OK_RECORD_METADATA_FIELDS = [
    "id", "parentId", "name", "titleNum", "chapterNum", "subChapterNum", "partNum", "sectionNum",
    "appendixNum", "description", "statusName", "segmentStatusId", "segmentTypeId", "recordStatus",
    "effectiveDate", "filingId", "hasEmergency", "segmentNotes",
]


MS_EPM_HEADING = r"^\s*(?P<num>{ch}\.\d{{2}}(?:\.\d{{2}}[A-Z]?)?)\s+(?P<heading>[A-Z][A-Z0-9 ,\-–’'()/&:.]+?)\s*$"
MS_EPM_LABEL = r"^\s*(?P<num>{ch}\.\d{{2}}(?:\.\d{{2}}[A-Z]?)?)\s*$"
MS_EPM_LABEL_HEADING = r"^\s*[A-Z][A-Z0-9 ,\-–’'()/&:.]+\s*$"
MS_EPM_DROP = [
    r"^\s*MISSISSIPPI DIVISION OF MEDICAID\s*$",
    r"^\s*Eligibility Policy and Procedures Manual\s*$",
    r"^\s*CHAPTER \d{3} – .*$",
    r"^\s*P\s?a\s?g\s?e\s*\|\s*\d+\s*$",
    r"^\s*Effective Month:.*$",
]


def _ms_chapter_extraction(chapter: str, start_page: int) -> dict:
    return {
        "segmentation": "labeled_sections",
        "start_page": start_page,
        "section_heading_pattern": MS_EPM_HEADING.format(ch=chapter),
        "section_label_pattern": MS_EPM_LABEL.format(ch=chapter),
        "label_only_heading_pattern": MS_EPM_LABEL_HEADING,
        "label_only_requires_heading": True,
        "section_label_template": "{num}",
        "heading_continuation_pattern": NEVER_CONTINUE,
        "drop_line_patterns": MS_EPM_DROP,
    }


NM_8_291_HEADING = (
    r"^(?P<label>8\s*\.\s*291\s*\.\s*{part}\s*\.\s*(?P<num>\d+(?:\s*-\s*\d+)?))\s+(?P<heading>[A-Z][^:]{{0,180}}:|\[RESERVED\]|"
    r"[A-Z][A-Z0-9 /()\[\]\-–—,'&]{{0,180}})(?:\s+(?P<body>.*))?$"
)


def _nm_part_doc(part: str, title: str, expression_date: str) -> dict:
    d = doc(
        "us-nm", f"nm-srca-nmac-8-291-{part}",
        f"8.291.{part} NMAC {title}",
        f"https://www.srca.nm.gov/parts/title08/08.291.0{part}.html",
        f"us-nm/regulation/nmac/8/291/{part}", "html", expression_date,
        document_class="regulation",
        subtype="administrative_code",
        authority="New Mexico State Records Center and Archives",
        extraction={
            "html_content_selector": ".WordSection1, .Section1",
            "segmentation": "labeled_sections",
            "section_heading_pattern": NM_8_291_HEADING.format(part=part),
            "section_label_template": f"8.291.{part}.{{num}}",
            "normalize_label_internal_whitespace": True,
        },
        metadata={
            "issuing_agency": "New Mexico Health Care Authority",
            "legal_identifier": f"8.291.{part} NMAC",
            "nmac_title": "8", "nmac_chapter": "291", "nmac_part": part,
            "nmac_title_index_url": "https://www.srca.nm.gov/nmac-home/nmac-titles/title-8-social-services/",
            "state_program": "Medicaid eligibility - affordable care (MAGI children incl. Title XXI-funded)",
        },
    )
    d["metadata"]["discovered_via"] = BATCH3_DISCOVERED_VIA
    return d


def _sd_chapter_doc(chapter: str, title: str, expression_date: str) -> dict:
    d = doc(
        "us-sd", f"sd-lrc-arsd-67-46-{chapter}",
        f"ARSD Chapter 67:46:{chapter} {title}",
        f"https://sdlegislature.gov/api/Rules/67:46:{chapter}",
        f"us-sd/regulation/arsd/67/46/{chapter}", "json", expression_date,
        document_class="regulation",
        subtype="administrative_rule_chapter",
        authority="South Dakota Department of Social Services (ARSD Article 67:46), published by the South Dakota Legislative Research Council",
        extraction={
            "json_html_field": "Html",
            "segmentation": "labeled_sections",
            "section_heading_pattern": rf"^67:46:{chapter}:(?P<num>\d{{2}})\s*\.\s+(?P<heading>[^.]+\.)\s*(?P<body>.*)$",
            "section_label_template": "{num}",
        },
        metadata={
            "legal_identifier": f"ARSD 67:46:{chapter}",
            "landing_page": f"https://sdlegislature.gov/Rules/Administrative/67:46:{chapter}",
            "article_index": "https://sdlegislature.gov/api/Rules/67:46",
        },
    )
    d["metadata"]["discovered_via"] = BATCH3_DISCOVERED_VIA
    return d


CONFIRMED_BATCH3: dict[str, dict] = {
    "us-ky": {
        "name": "Kentucky",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_html",
        "index_url": "https://apps.legislature.ky.gov/law/kar/titles/907/004/",
        "index_document_count": 2,
        "index_families": {"kar_regulation_html": 2},
        "primary_source_url": "https://apps.legislature.ky.gov/law/kar/titles/907/004/020/",
        "notes": (
            "Kentucky Legislative Research Commission index for 907 KAR Chapter 4 (Kentucky Children's "
            "Health Insurance Program): 2 regulations, 907 KAR 4:020 KCHIP Medicaid Expansion and 907 KAR "
            "4:030 KCHIP Phase III (separate CHIP), both last amended effective 2023-01-12 per their "
            "HISTORY lines. Taken 2, one HTML document each (div.regulation-content), whole regulation "
            "as one provision because the LRC page marks each section and paragraph as an h2 with the "
            "text in spans. The DCBS Operations Manual Volume IVA (Medicaid) at chfs.ky.gov was not "
            "located on a public index in this run."
        ),
        "documents": [
            doc(
                "us-ky", f"ky-lrc-907-kar-4-{num}",
                f"907 KAR 4:{num}. {title}",
                f"https://apps.legislature.ky.gov/law/kar/titles/907/004/{num}/",
                f"us-ky/regulation/kar/907/004/{num}", "html", "2023-01-12",
                document_class="regulation",
                subtype="administrative_regulation",
                authority="Kentucky Cabinet for Health and Family Services, Department for Medicaid Services (907 KAR), published by the Legislative Research Commission",
                extraction={"html_content_selector": "div.regulation-content"},
                metadata={"legal_identifier": f"907 KAR 4:{num}", "state_program": "KCHIP",
                          "history_effective": "2023-01-12"},
            )
            for num, title in (
                ("020", "Kentucky Children's Health Insurance Program Medicaid Expansion Title XXI of the Social Security Act"),
                ("030", "Kentucky Children's Health Insurance Program Phase III Title XXI of the Social Security Act"),
            )
        ],
    },
    "us-ok": {
        "name": "Oklahoma",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_json_records",
        "index_url": OK_RULES_API_317_35,
        "index_document_count": 397,
        "index_families": {"oac_section": 350, "oac_part": 29, "oac_subchapter": 17, "oac_chapter": 1},
        "primary_source_url": "https://rules.ok.gov/home",
        "notes": (
            "Oklahoma Secretary of State Office of Administrative Rules (rules.ok.gov, the official OAC "
            "publisher; same segments API as us-ok-snap-rules.yaml) chapter listing for OAC 317:35 "
            "Medical Assistance for Adults and Children - Eligibility: 397 segments (350 sections, 29 "
            "parts, 17 subchapters, the chapter; statuses 292 in force, 82 Revoked, 17 Terminated, 4 "
            "Reserved, 2 AmendedAndRenumbered). Oklahoma's CHIP is Medicaid-expansion SoonerCare for "
            "children, governed by Subchapter 6 SoonerCare for Pregnant Women and Families with Children. "
            "Taken 1 document, the chapter JSON filtered to the 29 Subchapter 6 sections (label prefix "
            "317:35-6-; Revoked and Reserved excluded; 62 and 62.1, AmendedAndRenumbered, carry no text in "
            "the API and yield no provision, so 27 section provisions result). The OHCA "
            "policy site lists the same 29 sections but states its copies are unofficial, so it is "
            "recorded only as the agency index. The API returns HTTP 403 to the plain client and is read "
            "through the manifest browser_impersonation fallback. Not taken: subchapters 5, 10, 22."
        ),
        "documents": [
            doc(
                "us-ok", "ok-oac-317-35-6-soonercare-children-families",
                "Oklahoma Administrative Code Title 317 Chapter 35 Subchapter 6 SoonerCare for Pregnant Women and Families with Children",
                "https://rules.ok.gov/home",
                "us-ok/regulation/oac/317/35", "json", SOURCE_AS_OF,
                document_class="regulation",
                subtype="administrative_code_subchapter",
                authority="Oklahoma Health Care Authority (OAC Title 317), published by the Oklahoma Secretary of State Office of Administrative Rules",
                request=IMPERSONATE,
                extraction={
                    "segmentation": "records",
                    "json_record_text_field": "text",
                    "json_record_text_is_html": True,
                    "json_record_label_field": "sectionNum",
                    "json_record_heading_field": "description",
                    "json_record_kind_field": "name",
                    "json_record_status_field": "statusName",
                    "json_record_exclude_statuses": ["Revoked", "Reserved"],
                    "json_record_include_label_prefixes": ["317:35-6-"],
                    "json_record_metadata_fields": OK_RECORD_METADATA_FIELDS,
                },
                metadata={
                    "official_publisher": "Oklahoma Secretary of State Office of Administrative Rules",
                    "rules_landing_page": "https://rules.ok.gov/home",
                    "rules_api_url": OK_RULES_API_317_35,
                    "agency_policy_site_index": OK_OHCA_SUBCHAPTER_6_INDEX,
                    "legal_identifier": "OAC 317:35-6",
                    "state_program": "SoonerCare (Medicaid-expansion CHIP for children)",
                    "expression_date_note": "chapter compilation as served on source_as_of; per-section effectiveDate kept in record metadata",
                },
            ),
        ],
    },
    "us-nv": {
        "name": "Nevada",
        "document_class": "manual",
        "source_kind": "official_pdf_manual_chapter",
        "index_url": "https://dwss.nv.gov/programs/medical/medical-assistance-manual/",
        "index_document_count": 93,
        "index_families": {"mam_chapter_pdf": 23, "mam_appendix_pdf": 9, "mam_full_manual_pdf": 1,
                           "mam_table_of_contents_pdf": 1, "manual_transmittal_letter_pdf": 59},
        "primary_source_url": "https://dwss.nv.gov/uploadedFiles/dwssnvgov/content/Medical/B-100%20MAGI%20Medical%20Categories%20Mar%2017.pdf",
        "notes": (
            "Nevada DWSS Medical Assistance Manual index: 93 documents (23 chapter PDFs A-100 to H-200, "
            "9 appendices, the full manual, the table of contents, 59 manual transmittal letters). "
            "Nevada Check Up (the separate CHIP) is determined under the MAM: section B-120.2 Nevada "
            "Check Up in chapter B-100 MAGI Medical Categories (March 2017) and Appendix A MAGI Income "
            "Charts (November 2024). Taken 2, page-level (the running page header repeats the section "
            "label, so labeled sections would collide). Not taken: E-100 MAGI Budget Methodology, the "
            "2014 'Nevada Check Up Manual revised sections' PDF linked from the Nevada Check Up page."
        ),
        "documents": [
            doc(
                "us-nv", "nv-dwss-mam-b-100",
                "Nevada DWSS Medical Assistance Manual B-100 Modified Adjusted Gross Income (MAGI) Medical Categories",
                "https://dwss.nv.gov/uploadedFiles/dwssnvgov/content/Medical/B-100%20MAGI%20Medical%20Categories%20Mar%2017.pdf",
                "us-nv/manual/dwss/chip/mam-b-100", "pdf", "2017-03-01",
                subtype="eligibility_manual_chapter_pdf",
                authority="Nevada Division of Welfare and Supportive Services",
                extraction=PAGES,
                metadata={"state_program": "Nevada Check Up", "manual_section": "B-100",
                          "chip_section": "B-120.2"},
            ),
            doc(
                "us-nv", "nv-dwss-mam-appendix-a",
                "Nevada DWSS Medical Assistance Manual Appendix A MAGI Income Charts",
                "https://dwss.nv.gov/uploadedFiles/dwssnvgov/content/Medical/Appendix%20A%20MAGI%20Income%20Charts%20ADA%20Nov%20-%2024.pdf",
                "us-nv/manual/dwss/chip/mam-appendix-a", "pdf", "2024-11-01",
                subtype="income_standards_chart_pdf",
                authority="Nevada Division of Welfare and Supportive Services",
                extraction=PAGES,
                metadata={"state_program": "Nevada Check Up", "manual_section": "Appendix A"},
            ),
        ],
    },
    "us-ms": {
        "name": "Mississippi",
        "document_class": "manual",
        "source_kind": "official_pdf_manual_chapter",
        "index_url": "https://medicaid.ms.gov/medicaid-coverage/eligibility-policy/",
        "index_document_count": 27,
        "index_families": {"eligibility_manual_chapter_pdf": 7, "eligibility_manual_appendix_pdf": 20},
        "primary_source_url": "https://medicaid.ms.gov/wp-content/uploads/2025/09/Chapter-101-Coverage-Groups-and-Processing-Applications-and-Reviews-revised-September2025.pdf",
        "notes": (
            "Mississippi Division of Medicaid Eligibility Policy and Procedures Manual index: 7 chapter "
            "PDFs (100, 101, 102, 200, 300, 400, 500) and 20 appendices. Mississippi's separate CHIP "
            "(COE-099) is determined under this manual. Taken 3: Chapter 101 Coverage Groups and "
            "Processing Applications and Reviews (revised September 2025; CHIP coverage group, 101.10.02 "
            "beginning dates of CHIP eligibility), Chapter 400 ABD and MAGI Eligibility Criteria and "
            "Budgeting (revised July 2025; 400.18-400.19 children and CHIP), labeled sections from the "
            "chapter's own numbering after the table of contents; Appendix A-3 MAGI Income Limits chart "
            "(uploaded March 2026), page-level. Not taken: chapters 100, 102, 200, 300, 500 and the "
            "other appendices."
        ),
        "documents": [
            doc(
                "us-ms", "ms-dom-epm-chapter-101",
                "Mississippi Division of Medicaid Eligibility Policy and Procedures Manual Chapter 101 Coverage Groups and Processing Applications and Reviews",
                "https://medicaid.ms.gov/wp-content/uploads/2025/09/Chapter-101-Coverage-Groups-and-Processing-Applications-and-Reviews-revised-September2025.pdf",
                "us-ms/manual/dom/chip/epm-chapter-101", "pdf", "2025-09-01",
                subtype="eligibility_manual_chapter_pdf",
                authority="Mississippi Division of Medicaid",
                extraction=_ms_chapter_extraction("101", 6),
                metadata={"state_program": "Mississippi CHIP (COE-099)", "manual_chapter": "101",
                          "revised": "September 2025"},
            ),
            doc(
                "us-ms", "ms-dom-epm-chapter-400",
                "Mississippi Division of Medicaid Eligibility Policy and Procedures Manual Chapter 400 ABD and MAGI Eligibility Criteria and Budgeting",
                "https://medicaid.ms.gov/wp-content/uploads/2025/07/Chapter-400-ABD-and-MAGI-Eligibility-Criteria-and-Budgeting.-Revised-July-2025v2.pdf",
                "us-ms/manual/dom/chip/epm-chapter-400", "pdf", "2025-07-01",
                subtype="eligibility_manual_chapter_pdf",
                authority="Mississippi Division of Medicaid",
                extraction=_ms_chapter_extraction("400", 4),
                metadata={"state_program": "Mississippi CHIP (COE-099)", "manual_chapter": "400",
                          "revised": "July 2025"},
            ),
            doc(
                "us-ms", "ms-dom-epm-appendix-a-3",
                "Mississippi Division of Medicaid Eligibility Policy and Procedures Manual Appendix A-3 Modified Adjusted Gross Income (MAGI) Limits Chart",
                "https://medicaid.ms.gov/wp-content/uploads/2026/03/Appendix-A-3-MAGI-Income-Limits.-2014-to-present.pdf",
                "us-ms/manual/dom/chip/epm-appendix-a-3", "pdf", "2026-03-01",
                subtype="income_standards_chart_pdf",
                authority="Mississippi Division of Medicaid",
                extraction=PAGES,
                metadata={"state_program": "Mississippi CHIP (COE-099)", "manual_appendix": "A-3",
                          "expression_date_note": "publisher upload month (2026/03); the chart carries no cover date"},
            ),
        ],
    },
    "us-nm": {
        "name": "New Mexico",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_html",
        "index_url": "https://www.srca.nm.gov/nmac-home/nmac-titles/title-8-social-services/",
        "index_document_count": 4,
        "index_families": {"nmac_part_html_in_force": 4},
        "primary_source_url": "https://www.srca.nm.gov/parts/title08/08.291.0400.html",
        "notes": (
            "New Mexico State Records Center and Archives NMAC Title 8 index, Chapter 291 Medicaid "
            "Eligibility - Affordable Care (the chapter link redirects to the title page, whose chapter "
            "291 entry lists only reserved ranges; parts 400, 410, 420, 430 were confirmed by fetching, "
            "440+ return 404). New Mexico's CHIP is Medicaid-expansion coverage determined under these "
            "MAGI rules. Taken 4: 8.291.400 Eligibility Requirements (amended through 2024-09-01), "
            "8.291.410 General Recipient Requirements (2024-07-01), 8.291.420 Recipient Rights and "
            "Responsibilities (2024-07-01), 8.291.430 Financial Responsibility Requirements (2025-04-01), "
            "labeled sections with the same pattern as us-nm-snap-regulations.yaml; expression_date is "
            "the latest history date in each part."
        ),
        "documents": [
            _nm_part_doc("400", "Eligibility Requirements", "2024-09-01"),
            _nm_part_doc("410", "General Recipient Requirements", "2024-07-01"),
            _nm_part_doc("420", "Recipient Rights and Responsibilities", "2024-07-01"),
            _nm_part_doc("430", "Financial Responsibility Requirements", "2025-04-01"),
        ],
    },
    "us-me": {
        "name": "Maine",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_docx",
        "index_url": "https://www.maine.gov/sos/cec/rules/10/ch332.htm",
        "index_document_count": 6,
        "index_families": {"rule_chapter_docx": 2, "rule_chapter_doc": 3, "rule_appendices_docx": 1},
        "primary_source_url": "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/144c332-2025-101%20NSC.docx",
        "notes": (
            "Maine Secretary of State APA Office page for 10-144 C.M.R. Chapter 332 MaineCare Eligibility "
            "Manual: 6 documents (Chapter 332 Word, its appendices and charts, Chapters 333-336). Part 5 "
            "Children's Health Insurance Program (CHIP, formerly CubCare) of Chapter 332 is Maine's CHIP "
            "eligibility rule; last updated (effective) 2025-04-29, filing 2025-101. Taken 1 document, "
            "Part 5 only (start after the body 'PART 5' heading, stop at 'PART 6'; 10 sections). Not "
            "taken: the other 11 parts of Chapter 332, the appendices, Chapters 333-336."
        ),
        "documents": [
            doc(
                "us-me", "me-ofi-mainecare-eligibility-manual-chapter-332-part-5",
                "Maine 10-144 C.M.R. Chapter 332 MaineCare Eligibility Manual, Part 5: Children's Health Insurance Program (CHIP)",
                "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/144c332-2025-101%20NSC.docx",
                "us-me/regulation/dhhs/ofi/chapter-332/part-5", "docx", "2025-04-29",
                document_class="regulation",
                subtype="administrative_rules_part",
                authority="Maine Department of Health and Human Services Office for Family Independence",
                extraction={
                    "segmentation": "labeled_sections",
                    "start_after_pattern": r"^PART 5$",
                    "stop_text_pattern": r"^PART 6$",
                    "section_heading_pattern": r"^SECTION (?P<num>\d+):\s*(?P<heading>.+)$",
                    "section_label_template": "section-{num}",
                },
                metadata={"publication_authority": "Maine Secretary of State Administrative Procedure Act Office",
                          "rule_chapter": "10-144 C.M.R. Chapter 332", "rule_part": "5",
                          "rule_filing": "2025-101", "state_program": "Maine CHIP (formerly CubCare)"},
            ),
        ],
    },
    "us-ri": {
        "name": "Rhode Island",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_pdf",
        "index_url": "https://rules.sos.ri.gov/Organizations/SubChapter/210-30-00",
        "index_document_count": 4,
        "index_families": {"ricr_part_active": 4},
        "primary_source_url": "https://rules.sos.ri.gov/regulations/Part/210-30-00-1",
        "notes": (
            "Rhode Island Code of Regulations (Department of State) Title 210 EOHHS, Chapter 30 Medicaid "
            "for Children, Families and ACA Adults (4 subchapters: 00 Affordable Coverage Groups, 05, 10, "
            "15); Subchapter 00 lists 4 active parts (1, 3, 4, 5). RIte Care children including the "
            "CHIP-funded group are determined under these parts. Taken 2: 210-RICR-30-00-1 Medicaid "
            "Affordable Care Coverage Groups Overview and Eligibility Pathways (effective 2025-08-17) and "
            "210-RICR-30-00-5 Medicaid MAGI Financial Eligibility Determinations and Verification "
            "(effective 2025-08-28), the 'Download Regulation' PDFs, page-level like us-ri-snap-rules.yaml. "
            "Not taken: parts 3 (application and renewal) and 4 (hospital presumptive eligibility)."
        ),
        "documents": [
            doc(
                "us-ri", "ri-eohhs-210-ricr-30-00-1",
                "210-RICR-30-00-1 Medicaid Affordable Care Coverage Groups Overview and Eligibility Pathways",
                "https://rules.sos.ri.gov/regulations/Part/210-30-00-1",
                "us-ri/regulation/210-ricr/30/00/1", "pdf", "2025-08-17",
                document_class="regulation",
                subtype="administrative_regulation",
                authority="Rhode Island Executive Office of Health and Human Services",
                extraction=PAGES,
                metadata={"official_publisher": "Rhode Island Department of State",
                          "legal_identifier": "210-RICR-30-00-1", "regulation_effective_date": "2025-08-17",
                          "download_url_note": "Download Regulation PDF REG_13314_20250728104245127.pdf"},
            ),
            doc(
                "us-ri", "ri-eohhs-210-ricr-30-00-5",
                "210-RICR-30-00-5 Medicaid MAGI Financial Eligibility Determinations and Verification",
                "https://rules.sos.ri.gov/regulations/Part/210-30-00-5",
                "us-ri/regulation/210-ricr/30/00/5", "pdf", "2025-08-28",
                document_class="regulation",
                subtype="administrative_regulation",
                authority="Rhode Island Executive Office of Health and Human Services",
                extraction=PAGES,
                metadata={"official_publisher": "Rhode Island Department of State",
                          "legal_identifier": "210-RICR-30-00-5", "regulation_effective_date": "2025-08-28",
                          "download_url_note": "Download Regulation PDF REG_13331_20250808145837454.pdf"},
            ),
        ],
    },
    "us-sd": {
        "name": "South Dakota",
        "document_class": "regulation",
        "source_kind": "official_adopted_rule_json_html",
        "index_url": "https://sdlegislature.gov/api/Rules/67:46",
        "index_document_count": 13,
        "index_families": {"arsd_chapter": 13},
        "primary_source_url": "https://sdlegislature.gov/api/Rules/67:46:14",
        "notes": (
            "South Dakota Legislature ARSD Article 67:46 Eligibility for Medical Services (13 chapters, "
            "read from the Legislative Research Council's rules API because sdlegislature.gov/Rules/"
            "Administrative/67:46 is script-rendered). Taken 2: Chapter 67:46:14 Nonmedicaid Children's "
            "Health Insurance Program (the separate CHIP rule; latest effective 2024-11-11) and Chapter "
            "67:46:12 MAGI Medicaid Eligibility Standards (Medicaid-expansion children; 2023-07-03), one "
            "JSON document each (Html field), sections split on the body headings '67:46:14:NN.'; the "
            "chapter's table-of-contents lines have no period after the number and are not sections."
        ),
        "documents": [
            _sd_chapter_doc("14", "Nonmedicaid Children's Health Insurance Program", "2024-11-11"),
            _sd_chapter_doc("12", "Modified Adjusted Gross Income (MAGI) Medicaid Eligibility Standards", "2023-07-03"),
        ],
    },
}
for _spec in CONFIRMED_BATCH3.values():
    for _d in _spec["documents"]:
        _d["metadata"]["discovered_via"] = BATCH3_DISCOVERED_VIA
CONFIRMED_BATCH3["us-ok"]["documents"][0]["download_url"] = OK_RULES_API_317_35
CONFIRMED_BATCH3["us-ri"]["documents"][0]["download_url"] = (
    "https://risos-apa-production-public.s3.amazonaws.com/EOHHS/REG_13314_20250728104245127.pdf"
)
CONFIRMED_BATCH3["us-ri"]["documents"][1]["download_url"] = (
    "https://risos-apa-production-public.s3.amazonaws.com/EOHHS/REG_13331_20250808145837454.pdf"
)

BLOCKED_BATCH3: dict[str, dict] = {
    "us-or": {
        "name": "Oregon",
        "index_url": "https://secure.sos.state.or.us/oard/displayChapterRules.action?selectedChapter=94",
        "index_document_count": None,
        "primary_source_url": "https://secure.sos.state.or.us/oard/displayChapterRules.action?selectedChapter=94",
        "notes": (
            "Blocked. Oregon's CHIP is Medicaid-expansion Oregon Health Plan coverage governed by OAR "
            "chapter 410 division 200 (OHA Health Systems Division, published by the Secretary of State's "
            "OARD). On 2026-09-10 the oregon.gov DNS zone did not resolve: secure.sos.state.or.us and "
            "www.oregon.gov returned SERVFAIL from the authoritative servers (dig @1.1.1.1 and @8.8.8.8, "
            "NS lookup for oregon.gov SERVFAIL), so both the plain and chrome120 probes failed with name "
            "resolution errors after 20 s. Probably transient; retry before treating as durable. 0 taken."
        ),
    },
    "us-ne": {
        "name": "Nebraska",
        "index_url": "https://rules.nebraska.gov/rules?agencyId=41",
        "index_document_count": None,
        "primary_source_url": "https://dhhs.ne.gov/Pages/Medicaid-Regulations.aspx",
        "notes": (
            "Blocked. Nebraska's CHIP is Medicaid-expansion coverage under 477 NAC (DHHS Medicaid "
            "eligibility regulations). dhhs.ne.gov did not accept TCP connections on 443 (ConnectTimeout "
            "20 s plain; curl (28) 20 s chrome120). The Secretary of State's Nebraska Administrative "
            "Code site rules.nebraska.gov serves its leaf certificate without the DigiCert Global G2 TLS "
            "RSA SHA256 2020 CA1 intermediate; with the already-committed data/certs/"
            "digicert-global-g2-tls-rsa-sha256-2020-ca1.pem in REQUESTS_CA_BUNDLE the chain verifies, "
            "after which the site root and the agency listing return HTTP 403 to plain and chrome120 "
            "clients. TLS verification was never disabled. 0 taken."
        ),
    },
    "us-hi": {
        "name": "Hawaii",
        "index_url": "https://medquest.hawaii.gov/en/plans-providers/har.html",
        "index_document_count": None,
        "primary_source_url": "https://medquest.hawaii.gov/en/plans-providers/har.html",
        "notes": (
            "Blocked. Hawaii's CHIP is Medicaid-expansion QUEST coverage governed by Med-QUEST Division "
            "administrative rules (HAR Title 17); medquest.hawaii.gov returned HTTP 522 (Cloudflare origin "
            "timeout, empty body, ~20 s) to plain and chrome120 clients. 0 taken."
        ),
    },
    "us-nh": {
        "name": "New Hampshire",
        "index_url": "https://www.gencourt.state.nh.us/rules/state_agencies/he-w800.html",
        "index_document_count": None,
        "primary_source_url": "https://www.gencourt.state.nh.us/rules/state_agencies/he-w800.html",
        "notes": (
            "Blocked. New Hampshire's CHIP eligibility rules are DHHS He-W 800 (medical assistance) "
            "published by the Office of Legislative Services at gencourt.state.nh.us: HTTP 403 'Error 403' "
            "to the plain client; the chrome120 request was closed abruptly (curl 56). 0 taken."
        ),
    },
    "us-ut": {
        "name": "Utah",
        "index_url": "https://oepmanuals-chip.dhhs.utah.gov/Welcome_page.htm",
        "index_document_count": None,
        "primary_source_url": "https://oepmanuals-chip.dhhs.utah.gov/Welcome_page.htm",
        "notes": (
            "Blocked. Utah DHHS Office of Eligibility Policy publishes a separate CHIP eligibility policy "
            "manual at oepmanuals-chip.dhhs.utah.gov (effective 2024-05-01); the host returns HTTP 403 "
            "AccessDenied (111-byte XML) to plain and chrome120 clients for the welcome page and the site "
            "root. The former Medicaid eligibility manual hosts medicaidpolicy.utah.gov and "
            "bepmanuals.health.utah.gov are NXDOMAIN. The adopted rule R382-10 lives only in the Office of "
            "Administrative Rules eRules single-page app (adminrules.utah.gov; plain client 404, no public "
            "rule endpoint found in its bundle), and medicaid.utah.gov publishes no eligibility manual. "
            "The existing us-ut/manual DWS Eligibility Manual scope has no CHIP chapter. 0 taken."
        ),
    },
    "us-mt": {
        "name": "Montana",
        "index_url": "https://rules.mt.gov/gateway/ChapterHome.asp?Chapter=37%2E79",
        "index_document_count": None,
        "primary_source_url": "https://rules.mt.gov/gateway/ChapterHome.asp?Chapter=37%2E79",
        "notes": (
            "Blocked. Montana's CHIP (Healthy Montana Kids) eligibility rule is ARM 37.79, published by "
            "the Secretary of State at rules.mt.gov. The site (plain client HTTP 200) is now the Esper "
            "'policy-library-public' single-page application: the HTML shell carries no rule text, its "
            "search API returns HTTP 403 AccessDenied to the plain client and the HTML shell to the "
            "chrome120 client, and no document endpoint is discoverable. dphhs.mt.gov/hmk answers (HTTP "
            "200) but publishes only the member guide and evidence of coverage, not an eligibility "
            "manual or rule. 0 taken."
        ),
    },
}

DONE_BATCH3: dict[str, dict] = {
    "us-ar": {
        "name": "Arkansas",
        "index_url": "https://humanservices.arkansas.gov/divisions-shared-services/county-operations/policy/",
        "index_document_count": 1,
        "target_manifest": f"discovery/ingest-medicaid: us-ar/manual {MEDICAID_RUN_VERSION}",
        "target_scope": {"jurisdiction": "us-ar", "document_class": "manual", "version": MEDICAID_RUN_VERSION},
        "pointer": "us-ar/manual/dco/medicaid/policy-manual (DCO Medical Services Policy Manual, 563 page provisions; ARKids First-B is determined under it)",
        "notes": (
            "Done by pointer (reviewer judgment). Arkansas's separate CHIP, ARKids First-B, is determined "
            "under the DHS Division of County Operations Medical Services Policy Manual (MS-Policy-9.26-"
            "New.pdf), which the parallel Medicaid run ingested in full on 2026-09-10 (563 page provisions "
            "at us-ar/manual/dco/medicaid/policy-manual, version " + MEDICAID_RUN_VERSION + "); the text "
            "names ARKids A and ARKids B throughout. " + MEDICAID_RUN_NOTE + " Nothing separate to add."
        ),
    },
    "us-wv": {
        "name": "West Virginia",
        "index_url": "https://bfa.wv.gov/income-maintenance-manual",
        "index_document_count": 1,
        "target_manifest": "manifests/us-wv-manuals.yaml",
        "target_scope": {"jurisdiction": "us-wv", "document_class": "manual", "version": "2026-07-21-wv-income-maintenance-manual"},
        "pointer": "us-wv/manual/bfa/income-maintenance-manual (Income Maintenance Manual effective 2026-07-01, 2276 page provisions; WVCHIP eligibility chapters included)",
        "notes": (
            "Done by pointer (reviewer judgment). West Virginia CHIP (WVCHIP) eligibility is determined "
            "under the Bureau for Family Assistance Income Maintenance Manual, already in the corpus as "
            "us-wv-manuals.yaml (single combined PDF effective 2026-07-01, 2276 page-level provisions, "
            "version 2026-07-21-wv-income-maintenance-manual); the WVCHIP provisions (MAGI Medicaid/WVCHIP "
            "chapters) are inside it. The former dhhr.wv.gov manual index returns 404; the current landing "
            "page is bfa.wv.gov/income-maintenance-manual. Nothing separate to add."
        ),
    },
}


def main() -> int:
    queue = yaml.safe_load(QUEUE.read_text())
    rows = {s["jurisdiction"]: s for s in queue["states"]}
    for jur, name in {**NEW_ROW_NAMES, **NEW_ROW_NAMES_BATCH3}.items():
        rows.setdefault(jur, {"jurisdiction": jur, "name": name, "lead_counts": {},
                              "candidate_sources": []})
    written: list[str] = []
    for jur, spec in {**CONFIRMED, **CONFIRMED_BATCH2, **CONFIRMED_BATCH3}.items():
        stem = f"{jur}-chip-state-eligibility-manual"
        manifest = {"version": VERSION, "documents": spec["documents"]}
        (ROOT / "manifests" / f"{stem}.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=120)
        )
        written.append(stem)
        row = rows[jur]
        row.update({
            "queue_status": "agent_ready",
            "source_kind": spec["source_kind"],
            "primary_source_url": spec["primary_source_url"],
            "target_manifest": f"manifests/{stem}.yaml",
            "target_scope": {"jurisdiction": jur, "document_class": spec["document_class"], "version": VERSION},
            "index_url": spec["index_url"],
            "index_document_count": spec["index_document_count"],
            "taken_count": len(spec["documents"]),
            "notes": spec["notes"],
        })
        if "index_families" in spec:
            row["index_families"] = spec["index_families"]
    for jur, spec in {**BLOCKED, **BLOCKED_BATCH2, **BLOCKED_BATCH3}.items():
        row = rows[jur]
        row.update({
            "queue_status": "blocked_primary_source",
            "source_kind": "official_publisher_blocked",
            "primary_source_url": spec["primary_source_url"],
            "target_manifest": None,
            "target_scope": {"jurisdiction": jur, "document_class": "manual", "version": None},
            "index_url": spec["index_url"],
            "index_document_count": spec["index_document_count"],
            "taken_count": 0,
            "notes": spec["notes"] + (f" {RETRY_NOTES[jur]}" if jur in RETRY_NOTES else ""),
        })
    for jur, spec in {**DONE, **DONE_BATCH2, **DONE_BATCH3}.items():
        row = rows[jur]
        row.update({
            "queue_status": "done",
            "source_kind": "already_in_corpus",
            "primary_source_url": spec["index_url"],
            "target_manifest": spec["target_manifest"],
            "target_scope": spec["target_scope"],
            "index_url": spec["index_url"],
            "index_document_count": spec["index_document_count"],
            "taken_count": 0,
            "notes": spec["notes"],
        })
        if "pointer" in spec:
            row["pointer"] = spec["pointer"]
    queue["states"] = [rows[j] for j in sorted(rows, key=lambda j: (j != "us", j))]
    queue["status_counts"] = {}
    for s in queue["states"]:
        queue["status_counts"][s["queue_status"]] = queue["status_counts"].get(s["queue_status"], 0) + 1
    queue["queue_status"] = "in_progress"
    QUEUE.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(f"wrote {len(written)} manifests: {', '.join(written)}; queue {queue['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
