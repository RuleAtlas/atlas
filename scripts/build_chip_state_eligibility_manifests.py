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


def main() -> int:
    queue = yaml.safe_load(QUEUE.read_text())
    rows = {s["jurisdiction"]: s for s in queue["states"]}
    written: list[str] = []
    for jur, spec in CONFIRMED.items():
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
    for jur, spec in BLOCKED.items():
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
            "notes": spec["notes"],
        })
    for jur, spec in DONE.items():
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
