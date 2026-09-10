"""Build the tax-year-2025 individual income tax form/instruction manifests (federal
IRS core plus the batch-1 states) and the 2026 IRS inflation-adjustment guidance
manifest, then update ``manifests/tax-agent-queue.yaml``.

Every URL below was confirmed by the agent on 2026-09-10 from the publisher's own
forms index (recorded per jurisdiction as ``index_url``); the PolicyEngine lead
list in the queue was discovery only and is never a source. The tables are static
on purpose: state forms indexes differ in shape (JS data tables, node pages,
media downloads) and a reviewer should be able to read the exact confirmed set.

    uv run python scripts/build_tax_forms_manifests.py [--verify]

``--verify`` issues a HEAD/GET probe for every download URL with the corpus
user agent and reports non-PDF/HTML responses without changing any file.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CORPUS_BASE = Path(os.environ.get("AXIOM_CORPUS_BASE", str(ROOT / "data" / "corpus")))
SOURCE_AS_OF = "2026-09-10"
TAX_YEAR = "2025"
TY_EXPRESSION_DATE = "2025-01-01"  # tax-year-2025 returns cover calendar year 2025
USER_AGENT = (
    "Axiom/1.0 (Legal Archive; contact@axiom-foundation.org) "
    "https://github.com/TheAxiomFoundation/axiom-corpus"
)

FEDERAL_FORMS_VERSION = "2026-09-10-tax-irs-forms-ty2025"
FEDERAL_GUIDANCE_VERSION = "2026-09-10-tax-irs-guidance"
STATE_FORMS_VERSION = "2026-09-10-tax-state-forms-ty2025"

IRS_FORMS_INDEX = "https://www.irs.gov/forms-instructions"
IRS_1040_INDEX = "https://www.irs.gov/forms-pubs/about-form-1040"
IRS_SCHEDULES_INDEX = "https://www.irs.gov/forms-pubs/schedules-for-form-1040"
IRS_IRB_INDEX = "https://www.irs.gov/internal-revenue-bulletins"

SINGLE_BLOCK = {"segmentation": "single_block"}
# irs.gov instruction/publication HTML: the `.book` container holds the headed
# body; the default HTML extractor emits one block per heading.
IRS_HTML = {"html_content_selector": ".book"}


def _irs_pdf(form_id: str, title: str, about_url: str, subtype: str) -> dict[str, Any]:
    return {
        "source_id": f"irs-{form_id}-ty{TAX_YEAR}",
        "jurisdiction": "us",
        "document_class": "form",
        "title": title,
        "source_url": about_url,
        "download_url": f"https://www.irs.gov/pub/irs-pdf/{form_id}.pdf",
        "source_format": "pdf",
        "source_as_of": SOURCE_AS_OF,
        "expression_date": TY_EXPRESSION_DATE,
        "citation_path": f"us/form/irs/ty{TAX_YEAR}/{form_id}",
        "extraction": SINGLE_BLOCK,
        "metadata": {
            "primary_source": True,
            "source_authority": "Internal Revenue Service",
            "document_subtype": subtype,
            "irs_product_id": form_id,
            "tax_year": TAX_YEAR,
            "source_discovery_group": "us/form/irs-individual-income-tax-forms",
            "source_family": "irs-individual-income-tax-forms-ty2025",
            "index_url": IRS_FORMS_INDEX,
            "discovered_via": "manual-review:tax-agent-queue; index https://www.irs.gov/forms-instructions and https://www.irs.gov/forms-pubs/schedules-for-form-1040",
        },
    }


def _irs_html(product_id: str, title: str, html_url: str, subtype: str) -> dict[str, Any]:
    return {
        "source_id": f"irs-{product_id}-ty{TAX_YEAR}",
        "jurisdiction": "us",
        "document_class": "form",
        "title": title,
        "source_url": html_url,
        "source_format": "html",
        "source_as_of": SOURCE_AS_OF,
        "expression_date": TY_EXPRESSION_DATE,
        "citation_path": f"us/form/irs/ty{TAX_YEAR}/{product_id}",
        "extraction": IRS_HTML,
        "metadata": {
            "primary_source": True,
            "source_authority": "Internal Revenue Service",
            "document_subtype": subtype,
            "irs_product_id": product_id,
            "tax_year": TAX_YEAR,
            "print_version_pdf": f"https://www.irs.gov/pub/irs-pdf/{product_id}.pdf",
            "source_discovery_group": "us/form/irs-individual-income-tax-forms",
            "source_family": "irs-individual-income-tax-forms-ty2025",
            "index_url": IRS_FORMS_INDEX,
            "discovered_via": "manual-review:tax-agent-queue; index https://www.irs.gov/forms-instructions and https://www.irs.gov/forms-pubs/schedules-for-form-1040",
        },
    }


FEDERAL_FORMS = [
    _irs_pdf("f1040", "Form 1040, U.S. Individual Income Tax Return (2025)", IRS_1040_INDEX, "form"),
    _irs_html("i1040gi", "Instructions for Form 1040 and Form 1040-SR (2025)", "https://www.irs.gov/instructions/i1040gi", "instructions"),
    _irs_pdf("f1040s1", "Schedule 1 (Form 1040), Additional Income and Adjustments to Income (2025)", IRS_SCHEDULES_INDEX, "schedule"),
    _irs_pdf("f1040s2", "Schedule 2 (Form 1040), Additional Taxes (2025)", IRS_SCHEDULES_INDEX, "schedule"),
    _irs_pdf("f1040s3", "Schedule 3 (Form 1040), Additional Credits and Payments (2025)", IRS_SCHEDULES_INDEX, "schedule"),
    _irs_pdf("f1040sa", "Schedule A (Form 1040), Itemized Deductions (2025)", "https://www.irs.gov/forms-pubs/about-schedule-a-form-1040", "schedule"),
    _irs_html("i1040sca", "Instructions for Schedule A (Form 1040), Itemized Deductions (2025)", "https://www.irs.gov/instructions/i1040sca", "instructions"),
    _irs_pdf("f1040sb", "Schedule B (Form 1040), Interest and Ordinary Dividends (2025)", "https://www.irs.gov/forms-pubs/about-schedule-b-form-1040", "schedule"),
    _irs_html("i1040sb", "Instructions for Schedule B (Form 1040), Interest and Ordinary Dividends (2025)", "https://www.irs.gov/instructions/i1040sb", "instructions"),
    _irs_pdf("f1040sd", "Schedule D (Form 1040), Capital Gains and Losses (2025)", "https://www.irs.gov/forms-pubs/about-schedule-d-form-1040", "schedule"),
    _irs_html("i1040sd", "Instructions for Schedule D (Form 1040), Capital Gains and Losses (2025)", "https://www.irs.gov/instructions/i1040sd", "instructions"),
    _irs_pdf("f1040sei", "Schedule EIC (Form 1040), Earned Income Credit (2025)", "https://www.irs.gov/forms-pubs/about-schedule-eic-form-1040", "schedule"),
    _irs_pdf("f1040s8", "Schedule 8812 (Form 1040), Credits for Qualifying Children and Other Dependents (2025)", "https://www.irs.gov/forms-pubs/about-schedule-8812-form-1040", "schedule"),
    _irs_html("i1040s8", "Instructions for Schedule 8812 (Form 1040), Credits for Qualifying Children and Other Dependents (2025)", "https://www.irs.gov/instructions/i1040s8", "instructions"),
    _irs_pdf("f8962", "Form 8962, Premium Tax Credit (PTC) (2025)", "https://www.irs.gov/forms-pubs/about-form-8962", "form"),
    _irs_html("i8962", "Instructions for Form 8962, Premium Tax Credit (PTC) (2025)", "https://www.irs.gov/instructions/i8962", "instructions"),
    _irs_pdf("f1040sse", "Schedule SE (Form 1040), Self-Employment Tax (2025)", "https://www.irs.gov/forms-pubs/about-schedule-se-form-1040", "schedule"),
    _irs_html("i1040sse", "Instructions for Schedule SE (Form 1040), Self-Employment Tax (2025)", "https://www.irs.gov/instructions/i1040sse", "instructions"),
    _irs_html("p17", "Publication 17 (2025), Your Federal Income Tax (For Individuals)", "https://www.irs.gov/publications/p17", "publication"),
]


def _irs_guidance(
    doc_id: str,
    number: str,
    title: str,
    irb: str,
    issue_date: str,
    pdf: str,
    subtype: str,
    expression_date: str,
    year: str,
) -> dict[str, Any]:
    return {
        "source_id": f"irs-{doc_id}",
        "jurisdiction": "us",
        "document_class": "guidance",
        "citation_path": f"us/guidance/irs/{doc_id}",
        "title": title,
        "source_url": f"https://www.irs.gov/irb/{irb}_IRB",
        "download_url": f"https://www.irs.gov/pub/irs-drop/{pdf}.pdf",
        "source_format": "pdf",
        "source_as_of": issue_date,
        "expression_date": expression_date,
        "metadata": {
            "primary_source": True,
            "source_authority": "Internal Revenue Service",
            "document_subtype": subtype,
            "document_number": number,
            "irb_citation": f"{irb.replace('_', ' ')} IRB",
            "irb_issue_date": issue_date,
            "tax_year": year,
            "source_discovery_group": "us/guidance/irs",
            "index_url": IRS_IRB_INDEX,
            "discovered_via": "manual-review:tax-agent-queue; index https://www.irs.gov/internal-revenue-bulletins (2026 issues scanned for inflation-adjustment items)",
        },
    }


FEDERAL_GUIDANCE = [
    _irs_guidance("notice-2026-10", "Notice 2026-10", "Notice 2026-10, 2026 Standard Mileage Rates", "2026-04", "2026-01-20", "n-26-10", "notice", "2026-01-01", "2026"),
    _irs_guidance("rev-proc-2026-24", "Rev. Proc. 2026-24", "Rev. Proc. 2026-24, 2027 inflation adjusted amounts for Health Savings Accounts", "2026-25", "2026-06-15", "rp-26-24", "revenue_procedure", "2027-01-01", "2027"),
    _irs_guidance("rev-proc-2026-26", "Rev. Proc. 2026-26", "Rev. Proc. 2026-26, Section 36B applicable percentage table and required contribution percentage for 2027", "2026-31", "2026-07-27", "rp-26-26", "revenue_procedure", "2027-01-01", "2027"),
]

# Already in manifests/us-irs-guidance.yaml; listed so the run note can say what
# the IRB scan skipped.
EXISTING_IRS_GUIDANCE = ("rev-proc-2025-25", "rev-proc-2025-32", "notice-2025-67")


# ---------------------------------------------------------------------------
# States, batch 1
# ---------------------------------------------------------------------------
# Each state: agency slug used in the citation path, publisher name, forms index
# URL, index inventory (families seen with counts, agent-recorded), and the
# confirmed documents. ``blocked`` records the exact publisher failure instead.

STATES: dict[str, dict[str, Any]] = {
    "us-al": {
        "name": "Alabama",
        "agency": "ador",
        "authority": "Alabama Department of Revenue",
        "index_url": "https://www.revenue.alabama.gov/forms/?jsf=jet-data-table:form-table&tax=individual-income-tax",
        "index_document_count": 26,
        "inventory": (
            "JetEngine data table filtered to Individual Income Tax; server renders 25 rows per view, "
            "all years, no server-side pagination. Search '40' view: 26 rows = 15 TY2025 + 10 TY2024 "
            "(Form 40 print form + instructions booklet, Form 40 tax table, 40A/40NR tax tables, 40V, "
            "Schedule OC + instructions, Schedules A/B/DC, D/E, ATP, standard deduction charts 40/40A/40NR, "
            "qualified vehicle loan interest worksheets). Nonresident (40NR) and 40A families not taken."
        ),
        "documents": [
            ("form-40", "Form 40, Alabama Individual Income Tax Return (2025)", "https://www.revenue.alabama.gov/wp-content/uploads/2026/01/25f40blk.pdf", "form"),
            ("form-40-instructions", "Form 40 Booklet, Alabama Individual Income Tax Return Instructions (2025)", "https://www.revenue.alabama.gov/wp-content/uploads/2026/01/25f40bk.pdf", "instructions"),
            ("form-40-tax-table", "Form 40 Tax Table (2025)", "https://www.revenue.alabama.gov/wp-content/uploads/2026/01/25f40taxtable.pdf", "tax_table"),
            ("form-40-standard-deduction-chart", "Standard Deduction Chart, Form 40 (2025)", "https://www.revenue.alabama.gov/wp-content/uploads/2026/01/25stddeduction40.pdf", "worksheet"),
        ],
    },
    "us-ar": {
        "name": "Arkansas",
        "agency": "dfa",
        "authority": "Arkansas Department of Finance and Administration",
        "index_url": "https://www.dfa.arkansas.gov/office/taxes/income-tax-administration/individual-income-tax/forms/2025-tax-forms/",
        "index_document_count": 49,
        "inventory": (
            "2025 Tax Forms page: 49 PDF links (AR1000F resident return, AR1000NR nonresident return, "
            "joint AR1000F/NR instructions, AR1000ES vouchers, schedules AR3/AR4/AR1000ADJ/AR1000D/AR1000TC/"
            "AR1000NOL/AR1000-CO/AR1000TD/AR-OI with instructions, credit forms AR1000CE/DC/DD/AR1075/AR1113/"
            "AR2441, AR2106/AR2210/AR2210A/AR3903/AR4684, AR1000V, AR1055-IT, AR-MS, AR-NRMILITARY, "
            "additional tax credit worksheet, penalty waiver form, Tax Brackets 2025, Tax Tables). "
            "Taken: resident return, instructions, tax brackets."
        ),
        "documents": [
            ("ar1000f", "Form AR1000F, Arkansas Full Year Resident Individual Income Tax Return (2025)", "https://www.dfa.arkansas.gov/wp-content/uploads/2025_AR1000F_FullYearResidentIndividualIncomeTaxReturn_1.pdf", "form"),
            ("ar1000f-instructions", "AR1000F and AR1000NR Instructions, Arkansas Individual Income Tax (2025)", "https://www.dfa.arkansas.gov/wp-content/uploads/2025_AR1000F_and_AR1000NR_Instructions.pdf", "instructions"),
            ("tax-brackets", "Arkansas Individual Income Tax Brackets (2025)", "https://www.dfa.arkansas.gov/wp-content/uploads/2025_TaxBrackets.pdf", "rate_schedule"),
        ],
    },
    "us-co": {
        "name": "Colorado",
        "agency": "cdor",
        "authority": "Colorado Department of Revenue",
        "index_url": "https://tax.colorado.gov/individual-income-tax-forms",
        "blocked": (
            "tax.colorado.gov returns HTTP 403 'ERROR: The request could not be satisfied ... The Amazon "
            "CloudFront distribution is configured to block access from your country' for the site root, "
            "the individual income tax forms index, and the DR 0104 Book PDF path, with the corpus user "
            "agent, a browser user agent, and curl_cffi chrome120 impersonation (2026-09-10). No "
            "workaround attempted; retry from a US network or request the publisher's bulk export."
        ),
    },
    "us-dc": {
        "name": "District of Columbia",
        "agency": "otr",
        "authority": "District of Columbia Office of Tax and Revenue",
        "index_url": "https://otr.cfo.dc.gov/page/individual-income-tax-forms-0",
        "index_document_count": 230,
        "inventory": (
            "Individual Income Tax Forms page: 230 node links across tax years 2018-2025; per year the "
            "families are D-40 Booklet, D-40 form (fill-in), D-40P payment voucher, D-40B nonresident "
            "request for refund, D-40ES estimated tax booklet, and LIHTC allocation instructions. TY2025 "
            "row: 6 documents. Taken: 2025 D-40 Booklet and 2025 D-40 form. The 2026 D-40ES booklet "
            "(estimated tax) is a TY2026 product and was left for the TY2026 cut. Note: the page and PDFs "
            "serve to the corpus user agent; a Chrome user agent / chrome120 impersonation is answered "
            "with a Cloudflare 'Access denied' page, so no browser_impersonation is configured."
        ),
        "documents": [
            ("d-40-booklet", "2025 D-40 Booklet, District of Columbia Individual Income Tax Forms and Instructions", "https://otr.cfo.dc.gov/sites/default/files/dc/sites/otr/publication/attachments/2025_D40_Book_082026_v1.pdf", "instructions", "https://otr.cfo.dc.gov/node/1817386"),
            ("d-40", "2025 D-40, District of Columbia Individual Income Tax Return", "https://otr.cfo.dc.gov/sites/default/files/dc/sites/otr/publication/attachments/2025_D40_Form_030526.pdf", "form", "https://otr.cfo.dc.gov/node/1817391"),
        ],
    },
    "us-de": {
        "name": "Delaware",
        "agency": "dor",
        "authority": "Delaware Division of Revenue",
        "index_url": "https://revenue.delaware.gov/personal-income-tax-forms/",
        "index_document_count": 63,
        "inventory": (
            "Personal Income Tax Forms Current Year (2025-2026) page: 63 PDF links. Families: resident "
            "PIT-RES form/schedule/Schedule A/worksheet/instructions, non-resident PIT-NON family, 2025 "
            "income tax table, PIT-VCH/PIT-EXT/PIT-EST 2026/PIT-REQ/PIT-UND/PIT-STC/PIT-SCW/PIT-CRS/"
            "PIT-BIN/PIT-CFR, fiduciary FID-*, composite CMP-*, partnership PRT-*, real estate REW-*, "
            "PUT-EXM and RTT-* business forms. Taken: PIT-RES form, PIT-RES instructions, 2025 tax table."
        ),
        "documents": [
            ("pit-res", "Form PIT-RES, Delaware Individual Resident and Amended Income Tax Return (2025)", "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/PIT-RES_2025-01_PaperInteractiveIPM.pdf", "form"),
            ("pit-res-instructions", "Form PIT-RES Instructions, Delaware Individual Resident Income Tax Return (2025)", "https://revenuefiles.delaware.gov/2025/PITForms_Instructions/Instructions/PIT-RES_Instructions_2025-01.pdf", "instructions"),
            ("income-tax-table", "Delaware 2025 Income Tax Table", "https://revenuefiles.delaware.gov/2025/TY25_taxtable.pdf", "tax_table"),
        ],
    },
    "us-ia": {
        "name": "Iowa",
        "agency": "idr",
        "authority": "Iowa Department of Revenue",
        "index_url": "https://revenue.iowa.gov/forms/common-forms/individual-income-tax",
        "index_document_count": 15,
        "inventory": (
            "Forms - Individual Income Tax page: 15 media links (2025 IA 1040 return, IA 1040ES 2026 "
            "voucher instructions, IA 148, IA 100/100A-G capital gain deduction forms, IA 4136, IA 176, "
            "alternate tax worksheet, composite agreement) plus a link to the online 2025 IA 1040 Expanded "
            "Instructions (47 line/intro HTML pages at .../1040-expanded-instructions and a printable PDF "
            "on its past-instructions page). Iowa publishes no separate rate schedule for TY2025 (flat "
            "rate stated in the instructions). Taken: 2025 IA 1040 return and the 2025 Expanded "
            "Instructions PDF (the department's own printable compilation of the HTML instructions)."
        ),
        "documents": [
            ("ia-1040", "2025 IA 1040 Iowa Individual Income Tax Return (41-001)", "https://revenue.iowa.gov/media/4402/download?inline", "form"),
            ("ia-1040-expanded-instructions", "2025 IA 1040 Expanded Instructions (printable)", "https://revenue.iowa.gov/media/4435/download?inline", "instructions", "https://revenue.iowa.gov/taxes/tax-guidance/individual-income-tax/1040-expanded-instructions/past-instructions"),
        ],
    },
    "us-id": {
        "name": "Idaho",
        "agency": "istc",
        "authority": "Idaho State Tax Commission",
        "index_url": "https://tax.idaho.gov/forms/",
        "index_document_count": 200,
        "inventory": (
            "Forms page: 589 links, 200 PDF form links across sales/use, property, tobacco, fuels, "
            "business income, individual income (Form 40 return 2025, Form 43 part-year/nonresident, "
            "Form 39R resident supplemental schedule, Form 39NR, individual income tax instructions "
            "EIN00046 rev. 2026-03-02, Form 51 estimated payment, food tax credit Form 24, capital "
            "gains deduction, itemized deduction worksheet), fiduciary, withholding and beer/wine "
            "families. Taken: Form 40, EIN00046 instructions, Form 39R. manifests/us-id-tax-forms.yaml "
            "(source-discovery seed, older EIN00046 revisions, never extracted) is left untouched."
        ),
        "documents": [
            ("form-40", "Form 40, Idaho Individual Income Tax Return (2025)", "https://tax.idaho.gov/wp-content/uploads/forms/EFO00089/EFO00089_03-02-2026.pdf", "form"),
            ("individual-income-tax-instructions", "Idaho Individual Income Tax Instructions, Forms 40, 43, 39R, 39NR (2025, EIN00046 rev. 2026-03-02)", "https://tax.idaho.gov/wp-content/uploads/forms/EIN00046/EIN00046_03-02-2026.pdf", "instructions"),
            ("form-39r", "Form 39R, Idaho Resident Supplemental Schedule (2025)", "https://tax.idaho.gov/wp-content/uploads/forms/EFO00088/EFO00088_03-02-2026.pdf", "schedule"),
        ],
    },
    "us-in": {
        "name": "Indiana",
        "agency": "dor",
        "authority": "Indiana Department of Revenue",
        "index_url": "https://www.in.gov/dor/tax-forms/individual/current/",
        "index_document_count": 62,
        "blocked": (
            "The DOR Current Year Individual Tax Forms index (62 form links: IT-40 booklet, IT-40 form, "
            "Schedules 1-7, IN-DEP, IN-W, CT-40, IT-40PNR family, credit schedules, ES-40, IT-2210) "
            "renders, but every download is served by forms.in.gov/Download.aspx?id=..., which answers "
            "HTTP 403 with a Cloudflare 'Sorry, you have been blocked ... You are unable to access in.gov' "
            "page for the corpus user agent, a Chrome user agent, and curl_cffi chrome120 impersonation "
            "(HEAD and GET, 2026-09-10); forms.in.gov root also 403s. No in.gov-hosted copy of the IT-40 "
            "booklet was found. The existing us-in guidance scope (2026-07-24-in-2026-individual-income-tax-"
            "source-hold) already records the portal listing; retry the file host from a US network."
        ),
    },
    "us-ms": {
        "name": "Mississippi",
        "agency": "dor",
        "authority": "Mississippi Department of Revenue",
        "index_url": "https://www.dor.ms.gov/forms-resources/form-search?division=individual_forms",
        "index_document_count": 26,
        "inventory": (
            "Form Search, Individual division: 26 PDF links (Form 80-100 individual income tax "
            "instructions, 80-105 resident return, 80-205 non-resident/part-year return, 80-106 voucher, "
            "80-107 withholding schedule, 80-108 itemized deductions, 80-115 e-file declaration, 80-155 "
            "NOL, 80-160 credit for tax paid to another state, 80-161 PTE credit, 80-315 reforestation "
            "credit + instructions, 80-320 interest/penalty worksheet, 80-340 reservation exclusion, 80-401 "
            "credit summary, 80-491 additional dependents, fiduciary 81-* forms, 70-698, 71-661, transcript "
            "request). Taken: 80-105 and 80-100. Mississippi publishes no separate TY2025 rate schedule."
        ),
        "documents": [
            ("form-80-105", "Form 80-105, Mississippi Resident Individual Income Tax Return (2025)", "https://www.dor.ms.gov/sites/default/files/tax-forms/individual/80105258%201.pdf", "form"),
            ("form-80-100-instructions", "Form 80-100, Mississippi Individual Income Tax Instructions (2025)", "https://www.dor.ms.gov/sites/default/files/tax-forms/individual/80100251%202.pdf", "instructions"),
        ],
    },
    "us-mt": {
        "name": "Montana",
        "agency": "mtdor",
        "authority": "Montana Department of Revenue",
        "index_url": "https://revenue.mt.gov/forms/",
        "index_document_count": 20,
        "inventory": (
            "Forms repository index links the Individual Income Tax publication pages. Form 2 publication "
            "page: 20 PDF links (Form 2 returns 2021-2025, 2024 instructions, 2024/2025 Schedules I-V, "
            "2EC and transition schedule, 2025 instructions); Form 2 instruction booklet page: 7 links "
            "(instructions 2020-2025, SALT-cap instructions). Taken: 2025 Form 2 and 2025 Form 2 "
            "instructions. Montana's rate schedule is inside the instructions."
        ),
        "documents": [
            ("form-2", "Montana Individual Income Tax Return, Form 2 (2025)", "https://revenue.mt.gov/files/Forms/Montana-Individual-Income-Tax-Return-Form-2/2025_Montana_Individual_Income_Tax_Return_Form_2.pdf", "form", "https://revenue.mt.gov/publications/montana-individual-income-tax-return-form-2"),
            ("form-2-instructions", "Montana Individual Income Tax Return, Form 2 Instructions (2025)", "https://revenuefiles.mt.gov/files/Forms/Montana-Individual-Income-Tax-Return-Form-2-Instructions/2025_Montana_Individual_Income_Tax_Return_Form_2_Instructions.pdf", "instructions", "https://revenue.mt.gov/publications/montana-form-2-individual-income-tax-return-forms-and-instructions-includes-form-2ec"),
        ],
    },
}

BATCH_1 = tuple(STATES)  # AL, AR, CO, DC, DE, IA, ID, IN, MS, MT in queue order

# States whose current-year resident individual income tax return material was
# already ingested (work-order list). target_manifest is the prior manifest; the
# scope version is the prior run's version when a local coverage artifact or a
# release selector names it, otherwise None.
DONE: dict[str, tuple[str, str | None]] = {
    "us-ak": ("manifests/us-ak-title-43-individual-income-tax-2026.yaml", "2026-07-24-ak-individual-income-tax"),
    "us-az": ("manifests/us-az-2026-140es-booklet.yaml", "2026-07-21-az-140es-2026"),
    "us-ca": ("manifests/us-ca-2026-form-540-es-instructions.yaml", "2026-07-23-ca-2026-form-540-es"),
    "us-ct": ("manifests/us-ct-2026-supplement-section-12-704e.yaml", "2026-07-24-ct-income-tax-supplement"),
    "us-fl": ("manifests/us-fl-individual-income-tax-zero-liability.yaml", "2026-07-24-fl-individual-income-tax-zero-liability"),
    "us-ga": ("manifests/us-ga-it-511-2025-official-document.yaml", "2026-07-21-ga-it-511-2025"),
    "us-hi": ("manifests/us-hi-2025-n11-capital-gain-worksheet.yaml", "2026-07-22-hi-2025-n11-capital-gain-worksheet"),
    "us-il": ("manifests/us-il-2026-resident-income-tax-core.yaml", "2026-07-24-il-individual-income-tax-resident-core"),
    "us-ks": ("manifests/us-ks-2026-k40es.yaml", "2026-07-21-ks-k40es-2026"),
    "us-ky": ("manifests/us-ky-2026-740-es.yaml", "2026-740-es"),
    "us-la": ("manifests/us-la-2026-it-540es-instructions.yaml", "2026-07-23-la-2026-it-540es-instructions"),
    "us-ma": ("manifests/us-ma-2026-form-1-es.yaml", "2026-07-22-ma-2026-form-1-es"),
    "us-md": ("manifests/us-md-tax-forms.yaml", None),
    "us-me": ("manifests/us-me-individual-income-tax-rates-2026.yaml", "2026-07-23-me-individual-income-tax-rates-2026"),
    "us-mi": ("manifests/us-mi-2026-income-tax-rate-notice.yaml", "2026-07-21-mi-2026-income-tax-rate-notice"),
    "us-mn": ("manifests/us-mn-income-tax-inflation-adjusted-amounts-2026.yaml", "2026-07-22-mn-income-tax-inflation-adjusted-amounts-2026"),
    "us-mo": ("manifests/us-mo-individual-income-tax-forms.yaml", None),
    "us-nc": ("manifests/us-nc-ty2026-income-tax-core.yaml", "2026-07-26-nc-ty2026-income-tax-core"),
    "us-nd": ("manifests/us-nd-individual-income-tax-forms.yaml", None),
    "us-ne": ("manifests/us-ne-2026-1040n-es.yaml", "2026-07-22-ne-1040n-es-2026"),
    "us-nv": ("manifests/us-nv-individual-income-tax-zero-liability.yaml", "2026-07-24-nv-individual-income-tax-zero-liability"),
    "us-ny": ("manifests/us-ny-tax-current-forms.yaml", "2026-06-05-ny-tax-current-forms"),
    "us-oh": ("manifests/us-oh-individual-income-tax-forms.yaml", None),
    "us-or": ("manifests/us-or-2026-or-estimate.yaml", "2026-07-22-or-estimate-2026"),
    "us-pa": ("manifests/us-pa-personal-income-tax-rates.yaml", "2026-07-21-pa-personal-income-tax-rates"),
    "us-ri": ("manifests/us-ri-pit-adv-2025-22-official-documents.yaml", "2026-07-23-ri-pit-adv-2025-22"),
    "us-sc": ("manifests/us-sc-individual-income-tax-forms.yaml", None),
    "us-sd": ("manifests/us-sd-2026-personal-income-tax-zero-liability.yaml", "2026-07-24-sd-personal-income-tax-zero-liability"),
    "us-tn": ("manifests/us-tn-2026-individual-income-tax-zero-liability-guidance.yaml", "2026-07-24-tn-individual-income-tax-zero-liability-guidance"),
    "us-tx": ("manifests/us-tx-2026-individual-income-tax-prohibition.yaml", "2026-07-24-tx-individual-income-tax-prohibition"),
    "us-va": ("manifests/us-va-tax-forms.yaml", None),
    "us-wi": ("manifests/us-wi-2026-form1-es-instructions.yaml", "2026-07-22-wi-form1-es-2026"),
    "us-wv": ("manifests/us-wv-individual-income-tax-forms.yaml", None),
    "us-wy": ("manifests/us-wy-2026-individual-income-tax-absence.yaml", "2026-07-24-wy-individual-income-tax-absence"),
}


def _coverage_class(jurisdiction: str, version: str | None) -> str | None:
    """Return the document_class whose local coverage artifact carries ``version``."""
    if version is None:
        return None
    base = CORPUS_BASE / "coverage" / jurisdiction
    if not base.is_dir():
        return None
    for class_dir in sorted(base.iterdir()):
        if (class_dir / f"{version}.json").is_file():
            return class_dir.name
    return None


def _state_document(jurisdiction: str, state: dict[str, Any], row: tuple[Any, ...]) -> dict[str, Any]:
    doc_id, title, url, subtype = row[:4]
    landing = row[4] if len(row) > 4 else None
    doc = {
        "source_id": f"{jurisdiction}-{state['agency']}-{doc_id}-ty{TAX_YEAR}",
        "jurisdiction": jurisdiction,
        "document_class": "form",
        "title": title,
        "source_url": landing or url,
        "source_format": "pdf",
        "source_as_of": SOURCE_AS_OF,
        "expression_date": TY_EXPRESSION_DATE,
        "citation_path": f"{jurisdiction}/form/{state['agency']}/ty{TAX_YEAR}/{doc_id}",
        "extraction": SINGLE_BLOCK,
        "metadata": {
            "primary_source": True,
            "source_authority": state["authority"],
            "document_subtype": subtype,
            "program": "individual_income_tax",
            "tax_year": TAX_YEAR,
            "source_discovery_group": f"{jurisdiction}/form/individual-income-tax",
            "source_family": "state-resident-individual-income-tax-forms-ty2025",
            "index_url": state["index_url"],
            "discovered_via": f"manual-review:tax-agent-queue; index {state['index_url']}",
        },
    }
    if landing:
        doc["download_url"] = url
    return doc


def _write_manifest(path: Path, documents: list[dict[str, Any]]) -> None:
    path.write_text(
        yaml.safe_dump({"version": SOURCE_AS_OF, "documents": documents}, sort_keys=False, allow_unicode=True, width=120)
    )


def _verify(documents: list[dict[str, Any]]) -> int:
    failures = 0
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for doc in documents:
        url = doc.get("download_url") or doc["source_url"]
        try:
            response = session.head(url, allow_redirects=True, timeout=60)
            if response.status_code >= 400 or response.status_code == 405:
                response = session.get(url, allow_redirects=True, timeout=120, stream=True)
            content_type = response.headers.get("content-type", "")
            ok = response.status_code == 200 and (
                ("pdf" in content_type) if doc["source_format"] == "pdf" else ("html" in content_type)
            )
            print(f"{'ok ' if ok else 'BAD'} {response.status_code} {content_type[:30]:30} {doc['source_id']}")
            response.close()
            failures += 0 if ok else 1
        except requests.RequestException as exc:
            print(f"BAD --- {exc!r} {doc['source_id']}")
            failures += 1
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--verify", action="store_true", help="probe every download URL; write nothing")
    args = parser.parse_args()

    manifests_dir = ROOT / "manifests"
    federal_forms_path = manifests_dir / "us-irs-individual-income-tax-forms-ty2025.yaml"
    federal_guidance_path = manifests_dir / "us-irs-guidance-2026-inflation-adjustments.yaml"
    state_docs: dict[str, list[dict[str, Any]]] = {
        jur: [_state_document(jur, state, row) for row in state["documents"]]
        for jur, state in STATES.items()
        if "documents" in state
    }

    if args.verify:
        all_docs = FEDERAL_FORMS + FEDERAL_GUIDANCE + [d for docs in state_docs.values() for d in docs]
        failures = _verify(all_docs)
        print(f"verified {len(all_docs)} documents, {failures} failures")
        return 1 if failures else 0

    _write_manifest(federal_forms_path, FEDERAL_FORMS)
    _write_manifest(federal_guidance_path, FEDERAL_GUIDANCE)
    written = [federal_forms_path.name, federal_guidance_path.name]
    state_manifest_paths: dict[str, Path] = {}
    for jur, docs in state_docs.items():
        path = manifests_dir / f"{jur}-individual-income-tax-forms-ty2025.yaml"
        _write_manifest(path, docs)
        state_manifest_paths[jur] = path
        written.append(path.name)

    queue_path = manifests_dir / "tax-agent-queue.yaml"
    queue = yaml.safe_load(queue_path.read_text())
    rows = {row["jurisdiction"]: row for row in queue["states"]}
    batch_note = "Batch 1 (2026-09-10) = the first ten queue-order states without a current-year resident return ingest: " + ", ".join(BATCH_1) + "."

    federal = rows["us"]
    federal.update(
        {
            "queue_status": "agent_ready",
            "source_kind": "official_pdf_and_html_forms_instructions",
            "primary_source_url": IRS_1040_INDEX,
            "target_manifest": f"manifests/{federal_forms_path.name}",
            "target_scope": {"jurisdiction": "us", "document_class": "form", "version": FEDERAL_FORMS_VERSION},
            "index_url": IRS_FORMS_INDEX,
            "index_document_count": 35,
            "taken_count": len(FEDERAL_FORMS),
            "notes": (
                "IRS individual income tax core, tax year 2025 (family irs-individual-income-tax-forms-ty2025): "
                "forms/schedules as single-block PDFs, instructions and Publication 17 from the irs.gov HTML "
                "editions (one provision per heading). Forms & Instructions index lists 35 products (popular "
                "forms/instructions/tax table; 1040 family, W-4, 1040-ES, W-9, 4506/4506-T, 2848, 941, W-2/W-3, "
                "9465, SS-4, W-7, 4547) and links the Schedules for Form 1040 page (14 schedules: 1, 1-A, 2, 3, "
                "A-F, H, J, R, SE, EIC, 8812). Taken: 19. Separate manifest "
                f"manifests/{federal_guidance_path.name} (document_class guidance, version "
                f"{FEDERAL_GUIDANCE_VERSION}) adds the 2026 IRB inflation-adjustment items not already in "
                "manifests/us-irs-guidance.yaml: Notice 2026-10, Rev. Proc. 2026-24, Rev. Proc. 2026-26. "
                "Extraction proven 2026-09-10."
            ),
        }
    )

    for jur, row in rows.items():
        if jur == "us":
            continue
        if jur in STATES:
            state = STATES[jur]
            if "blocked" in state:
                row.update(
                    {
                        "queue_status": "blocked_primary_source",
                        "source_kind": "official_pdf_forms_instructions",
                        "primary_source_url": state["index_url"],
                        "target_manifest": None,
                        "target_scope": {"jurisdiction": jur, "document_class": "form", "version": None},
                        "index_url": state["index_url"],
                        "index_document_count": state.get("index_document_count"),
                        "taken_count": 0,
                        "notes": f"{batch_note} Blocked by the publisher: {state['blocked']}",
                    }
                )
            else:
                docs = state_docs[jur]
                row.update(
                    {
                        "queue_status": "agent_ready",
                        "source_kind": "official_pdf_forms_instructions",
                        "primary_source_url": docs[0]["source_url"],
                        "target_manifest": f"manifests/{state_manifest_paths[jur].name}",
                        "target_scope": {"jurisdiction": jur, "document_class": "form", "version": STATE_FORMS_VERSION},
                        "index_url": state["index_url"],
                        "index_document_count": state["index_document_count"],
                        "taken_count": len(docs),
                        "notes": (
                            f"{batch_note} TY2025 resident individual income tax return material confirmed from the "
                            f"{state['authority']} forms index. {state['inventory']} Extraction proven 2026-09-10."
                        ),
                    }
                )
        elif jur in DONE:
            manifest, version = DONE[jur]
            if not (ROOT / manifest).is_file():
                print(f"warning: {jur} done manifest missing: {manifest}", file=sys.stderr)
            document_class = _coverage_class(jur, version)
            row.update(
                {
                    "queue_status": "done",
                    "source_kind": "official_documents_prior_ingest",
                    "primary_source_url": row.get("primary_source_url"),
                    "target_manifest": manifest,
                    "target_scope": {"jurisdiction": jur, "document_class": document_class, "version": version},
                    "taken_count": 0,
                    "notes": (
                        "Current-year individual income tax material already ingested (2026-07 state income tax "
                        "runs / zero-liability states); not re-ingested and not counted toward batch 1. "
                        + (
                            "The prior manifest exists but no local coverage artifact or release selector names its "
                            "version in this checkout; reviewer to confirm the scope."
                            if version is None
                            else "Scope taken from the prior run note / local coverage artifact."
                        )
                    ),
                }
            )
        else:
            row["queue_status"] = "needs_review"
            row["notes"] = f"Not in batch 1; waits for a later batch. {batch_note}"

    queue["states"] = [rows[j] for j in sorted(rows, key=lambda j: (j != "us", j))]
    counts: dict[str, int] = {}
    for row in queue["states"]:
        counts[row["queue_status"]] = counts.get(row["queue_status"], 0) + 1
    queue["status_counts"] = counts
    queue["queue_status"] = "in_progress"
    queue_path.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(f"wrote {len(written)} manifests: {', '.join(written)}")
    print(f"queue {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
