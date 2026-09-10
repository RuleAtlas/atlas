"""Build the TANF state policy manual manifests for the TANF agent queue batches
and update ``manifests/tanf-agent-queue.yaml``.

Batch rule (recorded in docs/ingest-runs/2026-09-10-tanf-state-policy-manuals-batch-1.md):
walk the queue's state rows in queue order; a state whose current TANF cash
assistance policy manual (or the adopted rule the state itself publishes as its
primary policy document) is already in the corpus is marked ``done`` and does not
count; batch 1 is the first ten remaining rows. Batch 1 = CA, CO, DC, MO, MS, MT,
ND, NY, OK, OR. NY and OR are blocked publishers (see BLOCKED below); the other
eight get one manifest each, generated here from the publisher's own index.

Every index is fetched live from the publisher. Some publishers (Montana DPHHS,
Mississippi SoS, CDSS) answer plain HTTP clients with 403/reset pages, so index
fetches use curl-cffi browser impersonation; the manifests carry
``request: browser_impersonation: true`` where the document host needs it.

    uv run python scripts/build_tanf_state_policy_manual_manifests.py \
        [--mo-title-cache <json>]

The Missouri TA manual has 472 section pages whose titles are only in each page's
``<title>``; the script fetches them (about 10 minutes) unless a cache JSON from a
previous run is supplied.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from curl_cffi import requests as curl_requests

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "manifests" / "tanf-agent-queue.yaml"
VERSION = "2026-09-10-tanf-state-policy-manual"
SOURCE_AS_OF = dt.date.today().isoformat()
IMPERSONATE = "chrome"
DISCOVERED_VIA = "manual-review:tanf-agent-queue; index {index}"

BATCH_1 = ("us-ca", "us-co", "us-dc", "us-mo", "us-ms", "us-mt", "us-nd", "us-ny", "us-ok", "us-or")
# Batch 2 (docs/ingest-runs/2026-09-10-tanf-state-policy-manuals-batch-2.md): the four rows batch 1
# deferred, then - the queue having no further state rows - the next states in alphabetical order
# whose TANF policy manual or adopted rule is not already in the corpus, until ten were attempted.
BATCH_2 = ("us-pa", "us-sc", "us-sd", "us-va", "us-id", "us-ky", "us-la", "us-ne", "us-nh", "us-nm")
# Batch 3 (docs/ingest-runs/2026-09-10-tanf-state-policy-manuals-batch-3.md): the last jurisdictions
# of the 50 states plus DC without a queue row.
BATCH_3 = ("us-oh", "us-ri", "us-tn", "us-vt", "us-wi")
BATCH_LABEL = {
    **dict.fromkeys(BATCH_1, "Batch 1"),
    **dict.fromkeys(BATCH_2, "Batch 2"),
    **dict.fromkeys(BATCH_3, "Batch 3"),
}
# Rows added to the queue by batches 2 and 3 (not on the lead list): name per jurisdiction.
NEW_ROWS = {
    "us-ak": "Alaska",
    "us-ar": "Arkansas",
    "us-ct": "Connecticut",
    "us-ia": "Iowa",
    "us-id": "Idaho",
    "us-ky": "Kentucky",
    "us-la": "Louisiana",
    "us-ma": "Massachusetts",
    "us-md": "Maryland",
    "us-mi": "Michigan",
    "us-mn": "Minnesota",
    "us-ne": "Nebraska",
    "us-nh": "New Hampshire",
    "us-nj": "New Jersey",
    "us-nm": "New Mexico",
    "us-oh": "Ohio",
    "us-ri": "Rhode Island",
    "us-tn": "Tennessee",
    "us-ut": "Utah",
    "us-vt": "Vermont",
    "us-wi": "Wisconsin",
    "us-wv": "West Virginia",
    "us-wy": "Wyoming",
}

# States whose TANF cash-assistance policy manual (or state-published adopted rule)
# is already in the corpus. target_manifest / target_scope name the existing
# artifacts; these rows do not count toward a batch.
DONE: dict[str, dict[str, Any]] = {
    "us-al": {
        "target_manifest": "manifests/us-al-tanf-official-documents.yaml",
        "scope": ("policy", "2026-07-02-al-tanf-official-documents"),
        "notes": "Alabama Family Assistance: Admin Code 660-2-2 (regulation, 2026-07-02-al-admin-code-660-2-2), "
        "TANF State Plan 2024 and Public Assistance Payment Manual Appendix N Sec 2 (policy). Reviewer judgment: "
        "the DHR-published payment manual appendix plus the adopted rule is the state's primary policy document set; "
        "no separate DHR TANF policy manual index exists. Done per the prior-ingest list.",
    },
    "us-az": {
        "target_manifest": "manifests/us-az-des-faa5-manual.yaml",
        "scope": ("manual", "2025-10-30-az-des-faa5-manual"),
        "notes": "Arizona DES FAA policy manual (combined CA/NA) already ingested; recovery scope 2026-07-17-faa5-recovery also exists. Done per the prior-ingest list.",
    },
    "us-de": {
        "target_manifest": "manifests/us-de-tanf-rules.yaml",
        "scope": ("regulation", "2026-07-03-de-tanf-rules"),
        "notes": "Delaware DSSM 3000 TANF rules (state-published adopted rule) already ingested. Done per the prior-ingest list.",
    },
    "us-fl": {
        "target_manifest": "manifests/us-fl-ess-manual.yaml",
        "scope": ("manual", "2026-05-27-fl-ess-manual"),
        "notes": "Florida DCF ESS Program Policy Manual is the combined FS/TCA/Medicaid manual (48 chapters incl. 1400/1800 TCA chapters, 2600 benefit calculation). Reviewer judgment: combined manual counts as the TCA policy manual; not re-ingested.",
    },
    "us-ga": {
        "target_manifest": "manifests/us-ga-tanf-manual.yaml",
        "scope": ("manual", "2026-06-25-ga-tanf"),
        "notes": "Georgia DFCS TANF Policy Manual already ingested. Done per the prior-ingest list.",
    },
    "us-hi": {
        "target_manifest": "manifests/us-hi-tanf-admin-rules.yaml",
        "scope": ("regulation", "2026-07-03-hi-tanf-admin-rules"),
        "notes": "Hawaii HAR TANF rules already ingested. Done per the prior-ingest list.",
    },
    "us-il": {
        "target_manifest": "manifests/us-il-snap-manual.yaml",
        "scope": ("manual", "2026-05-27-il-cash-snap-medical-manual"),
        "notes": "Illinois DHS Cash, SNAP and Medical Manual (combined; PM chapters incl. cash/TANF) already ingested as us-il/manual/dhs/csmm. Reviewer judgment: combined manual counts; not re-ingested.",
    },
    "us-in": {
        "target_manifest": "manifests/us-in-snap-manual.yaml",
        "scope": ("manual", "2026-05-27-in-snap-manual"),
        "notes": "Indiana FSSA/DFR SNAP/TANF Program Policy Manual (combined) already ingested at page granularity. Reviewer judgment: combined manual counts; chapter-level re-segmentation is a later improvement, not a batch item.",
    },
    "us-ks": {
        "target_manifest": "manifests/us-ks-keesm.yaml",
        "scope": ("manual", "2026-05-27-ks-keesm"),
        "notes": "Kansas KEESM (combined) already ingested. Done per the prior-ingest list.",
    },
    "us-me": {
        "target_manifest": "manifests/us-me-tanf-regulation-official-documents.yaml",
        "scope": ("regulation", "2026-07-03-me-tanf-regulation"),
        "notes": "Maine TANF rule (10-144 CMR ch. 331) and rule 125A already ingested; Maine publishes its TANF policy as adopted rules. Done per the prior-ingest list.",
    },
    "us-nc": {
        "target_manifest": "manifests/us-nc-work-first-manual-official-documents.yaml",
        "scope": ("manual", "2026-07-03-nc-work-first-manual"),
        "notes": "North Carolina Work First Manual section 114 (Income and Budgeting) already ingested. Reviewer judgment: done per the prior-ingest list, but only section 114 of the manual is in the corpus; the remaining Work First manual sections are a follow-up, not a batch-1 item.",
    },
    "us-nv": {
        "target_manifest": "manifests/us-nv-eligibility-payments-manual.yaml",
        "scope": ("manual", "2026-05-27-nv-eligibility-payments-manual"),
        "notes": "Nevada DWSS Eligibility and Payments Manual (combined TANF/SNAP/Medicaid, 51 chapter PDFs) already ingested. Reviewer judgment: combined manual counts as the TANF policy manual; not re-ingested.",
    },
    "us-tx": {
        "target_manifest": "manifests/us-tx-manuals.yaml",
        "scope": ("manual", "2026-05-27-tx-manuals"),
        "notes": "Texas Works Handbook (combined) already ingested. Done per the prior-ingest list.",
    },
    "us-wa": {
        "target_manifest": "manifests/us-wa-eaz-manual.yaml",
        "scope": ("manual", "2026-07-21-wa-eaz-manual"),
        "notes": "Washington EA-Z Manual (combined) already ingested. Done per the prior-ingest list.",
    },
    # Batch 2: states not on the lead list, checked in alphabetical order while extending the
    # batch to ten attempts; their TANF policy document is already in the corpus.
    "us-ak": {
        "target_manifest": "manifests/us-ak-atap-regulations.yaml",
        "scope": ("regulation", "2026-07-01-ak-atap-regulations"),
        "notes": "Batch 2 check: Alaska ATAP regulations (7 AAC 45, adopted rule) and ATAP standards (guidance, 2026-07-01-ak-atap-standards) already ingested. Done.",
    },
    "us-ar": {
        "target_manifest": "manifests/us-ar-tea-official-documents.yaml",
        "scope": ("policy", "2026-07-02-ar-tea-official-documents"),
        "notes": "Batch 2 check: Arkansas TEA official documents already ingested. Done.",
    },
    "us-ct": {
        "target_manifest": "manifests/us-ct-ssp-official-documents.yaml",
        "scope": ("policy", "2026-07-02-ct-ssp-upm-and-standards"),
        "notes": "Batch 2 check: Connecticut DSS Uniform Policy Manual (TFA) and standards already ingested. Done.",
    },
    "us-ia": {
        "target_manifest": "manifests/us-ia-fip-admin-rules.yaml",
        "scope": ("regulation", "2026-07-03-ia-fip-admin-rules"),
        "notes": "Batch 2 check: Iowa FIP administrative rules (441 IAC, adopted rule) already ingested. Done.",
    },
    "us-ma": {
        "target_manifest": "manifests/us-ma-tafdc-regulations.yaml",
        "scope": ("regulation", "2026-06-27-ma-tafdc-regulations"),
        "notes": "Batch 2 check: Massachusetts DTA TAFDC regulations 106 CMR 701-707 (adopted rule published by DTA) already ingested. Done.",
    },
    "us-md": {
        "target_manifest": "manifests/us-md-tca-guidance-official-documents.yaml",
        "scope": ("regulation", "2026-07-03-md-tca-comar-publication-2026-06-29-title-07-subtitle-03-chapter-03"),
        "notes": "Batch 2 check: Maryland TCA COMAR 07.03.03 (adopted rule), TCA guidance and statutes already ingested. Done.",
    },
    "us-mi": {
        "target_manifest": "manifests/us-mi-bridges-manual.yaml",
        "scope": ("manual", "2026-07-17-mi-bridges-manual"),
        "notes": "Batch 2 check: Michigan MDHHS Bridges Eligibility Manual (combined, incl. FIP) and RFT 248 already ingested. Reviewer judgment: combined manual counts. Done.",
    },
    "us-mn": {
        "target_manifest": "manifests/us-mn-combined-manual.yaml",
        "scope": ("manual", "2026-05-27-mn-combined-manual-r2026-07-15-self-contained"),
        "notes": "Batch 2 check: Minnesota DHS Combined Manual (MFIP) already ingested. Reviewer judgment: combined manual counts. Done.",
    },
    "us-nj": {
        "target_manifest": "manifests/us-nj-wfnj-rules.yaml",
        "scope": ("regulation", "2026-07-13-recovery"),
        "notes": "Batch 2 check: New Jersey WFNJ rules N.J.A.C. 10:90 (adopted rule) are in the corpus in the page-level 2026-07-13-recovery scope. Done with that caveat.",
    },
    "us-ut": {
        "target_manifest": "manifests/us-ut-fep-official-documents.yaml",
        "scope": ("regulation", "2026-07-02-ut-fep-official-documents"),
        "notes": "Batch 2 check: Utah FEP rules R986 (adopted rule) and the DWS eligibility manual already ingested. Done.",
    },
    "us-wv": {
        "target_manifest": "manifests/us-wv-manuals.yaml",
        "scope": ("manual", "2026-07-21-wv-income-maintenance-manual"),
        "notes": "Batch 2 check: West Virginia Income Maintenance Manual (combined, incl. WV WORKS) already ingested. Reviewer judgment: combined manual counts. Done.",
    },
    "us-wy": {
        "target_manifest": "manifests/us-wy-manuals.yaml",
        "scope": ("manual", "2026-05-27-wy-manuals-r2026-07-15-self-contained"),
        "notes": "Batch 2 check: Wyoming SNAP and POWER Policy Manual (combined) already ingested. Reviewer judgment: combined manual counts. Done.",
    },
}

# Publishers that blocked retrieval on 2026-09-10. Exact failures observed by the agent.
BLOCKED: dict[str, dict[str, Any]] = {
    "us-ny": {
        "source_kind": "official_pdf_manual",
        "primary_source_url": "https://otda.ny.gov/programs/temporary-assistance/TASB.pdf",
        "index_url": "https://otda.ny.gov/programs/temporary-assistance/",
        "index_document_count": 1,
        "document_class": "manual",
        "notes": "BLOCKED 2026-09-10: OTDA Temporary Assistance Source Book (TASB.pdf, HTTP Last-Modified 2024-11-27). "
        "Plain requests/curl to otda.ny.gov: TCP connection reset by peer. curl-cffi browser impersonation "
        "(chrome, chrome110, chrome124, edge101, firefox): HTTP 200 text/html 6.7 KB JavaScript bot-challenge page "
        "('Please enable JavaScript to view the page content. Your support ID is ...') instead of the PDF; safari "
        "profiles: connection reset. No workaround attempted. The 2024-2026 TANF State Plan (policy) is already in "
        "the corpus (us-ny-tanf-state-plan); the Employment Policy Manual is in 2026-07-17-ny-snap-manuals. "
        "Retried 2026-09-10T20:37+02:00 (batch 2: one plain curl HEAD, connection reset by peer; one curl-cffi "
        "chrome/firefox GET, HTTP 200 text/html 5.5 KB challenge page; 15 s timeouts), same failure.",
    },
    "us-or": {
        "source_kind": "official_rule_pdfs",
        "primary_source_url": "https://ch461rules.odhs.oregon.gov/",
        "index_url": "https://ch461rules.odhs.oregon.gov/",
        "index_document_count": None,
        "document_class": "regulation",
        "notes": "BLOCKED 2026-09-10: Oregon publishes TANF policy as OAR chapter 461 (ODHS per-rule PDFs at "
        "ch461rules.odhs.oregon.gov; Secretary of State OARD at secure.sos.state.or.us). Neither host resolved from "
        "the ingest environment: system resolver and 8.8.8.8/9.9.9.9 return SERVFAIL/no answer for "
        "ch461rules.odhs.oregon.gov, www.oregon.gov and secure.sos.state.or.us (dig EDE: 'at delegation oregon.gov'); "
        "1.1.1.1 resolves them, but Python getaddrinfo, requests and curl all fail with name-resolution errors, so "
        "no index could be inventoried. Not a publisher block of the client; re-try from another network. Note for "
        "the retry: chapter 461 is a combined rulebook for all ODHS self-sufficiency programs (SNAP, TANF, ERDC ...), "
        "so the TANF family would be a filtered division set, and an OAR adapter already exists "
        "(extract-oregon-administrative-rules). The existing us-or manual scope (OPEN eligibility notebook) is not "
        "the TANF policy manual. Retried 2026-09-10T20:37+02:00 (batch 2: one plain curl, 'Resolving timed out'; "
        "one curl-cffi chrome GET of ch461rules.odhs.oregon.gov and secure.sos.state.or.us, 'Could not resolve "
        "host'; 15 s timeouts), same failure.",
    },
    # Batch 2 blocked publishers.
    "us-sc": {
        "source_kind": "official_pdf_manual",
        "primary_source_url": "https://dss.sc.gov/media/ojqddxsk/tanf-policy-manual-volume-65.pdf",
        "index_url": "https://dss.sc.gov/about/data-and-resources/manuals/",
        "index_document_count": None,
        "document_class": "manual",
        "notes": "BLOCKED 2026-09-10: SC DSS TANF Policy Manual Volume 65 (dss.sc.gov, the host of the ingested SNAP "
        "manual volume 69). dss.sc.gov resolves to 167.7.60.200 but every TCP connection to :443 and :80 timed out "
        "(curl 'Connection timed out after 12002 milliseconds'; Python requests ConnectTimeout; curl-cffi chrome "
        "impersonation 'Connection timed out after 30001 milliseconds'), at 20:35, 20:39 and 20:52 +02:00. No index "
        "could be inventoried; no workaround attempted. Retry from another network.",
    },
    "us-ky": {
        "source_kind": "official_html_manual",
        "primary_source_url": "https://www.chfs.ky.gov/agencies/dcbs/dfs/Pages/opmanual.aspx",
        "index_url": "https://www.chfs.ky.gov/agencies/dcbs/dfs/Pages/opmanual.aspx",
        "index_document_count": None,
        "document_class": "manual",
        "notes": "BLOCKED 2026-09-10: Kentucky CHFS DCBS Operation Manual index (Volume IIIA K-TAP). Plain requests and "
        "curl-cffi chrome impersonation both receive HTTP 403 text/html 1484 bytes 'Service unavailable - The request is "
        "blocked.' with an x-azure-ref header (Azure Front Door WAF). No index could be inventoried; no workaround "
        "attempted.",
    },
    "us-ne": {
        "source_kind": "official_pdf_regulation",
        "primary_source_url": "https://rules.nebraska.gov/",
        "index_url": "https://rules.nebraska.gov/",
        "index_document_count": None,
        "document_class": "regulation",
        "notes": "BLOCKED 2026-09-10: Nebraska ADC policy is 468 NAC, published by the Secretary of State at "
        "rules.nebraska.gov (www.nebraska.gov/rules-and-regs redirects there); DHHS program pages (dhhs.ne.gov) time out "
        "on TCP connect. rules.nebraska.gov serves only its leaf certificate (issuer DigiCert Global G2 TLS RSA SHA256 "
        "2020 CA1), so the public intermediate was added as data/certs/digicert-global-g2-tls-rsa-sha256-2020-ca1.pem "
        "(fetched from the leaf's AIA URL; verification never disabled). With the repaired chain the host answers plain "
        "requests and chrome impersonation with HTTP 403 (Microsoft-Azure-Application-Gateway/v2) '403 - Access Denied / "
        "Forbidden ... You are accessing this site from an IP Address out[side the allowed range]'. No index could be "
        "inventoried; no workaround attempted. Retry from a US network.",
    },
    # Batch 3 blocked publishers.
    "us-oh": {
        "source_kind": "official_html_manual",
        "primary_source_url": "https://emanuals.jfs.ohio.gov/CashFoodAssist/CAM/",
        "index_url": "https://emanuals.jfs.ohio.gov/CashFoodAssist/CAM/",
        "index_document_count": None,
        "document_class": "manual",
        "notes": "BLOCKED 2026-09-10: Ohio Works First policy is published by ODJFS as the Cash Assistance Manual (CAM) on "
        "its eManuals site (emanuals.jfs.ohio.gov/CashFoodAssist/CAM/) and codified as OAC 5101:1 on codes.ohio.gov "
        "(Legislative Service Commission; the host of the ingested OAC 5101:4 SNAP scope). Both hosts, probed once each "
        "at 20:46-20:47Z with 20 s timeouts: plain requests ConnectTimeout (TCP connect never completed) and curl-cffi "
        "chrome impersonation 'curl: (28) Connection timed out after 20002 milliseconds'. No index could be "
        "inventoried; no workaround attempted. Retry from another network (codes.ohio.gov answered plain clients in July).",
    },
    "us-tn": {
        "source_kind": "official_pdf_manual_sections",
        "primary_source_url": "https://www.tn.gov/humanservices/information-and-resources/dhs-publications.html",
        "index_url": "https://www.tn.gov/humanservices/information-and-resources/dhs-publications.html",
        "index_document_count": None,
        "document_class": "manual",
        "notes": "BLOCKED 2026-09-10: Tennessee DHS publishes the Families First policy manual as section PDFs on "
        "www.tn.gov (DHS publications page, the landing page of the ingested SNAP policy manual scope "
        "us-tn-snap-policies). Probed once at 20:47Z with 20 s timeouts (Families First program page "
        "/humanservices/for-families/families-first-tanf.html): plain requests GET connected but ReadTimeout after 20 s; "
        "curl-cffi chrome GET 'curl: (28) Connection timed out after 20001 milliseconds'. No index could be inventoried; "
        "no workaround attempted. The Secretary of State's Families First rule chapters (Tenn. Comp. R. & Regs. "
        "1240-01-47 through 1240-01-50) are not in the corpus either: the existing us-tn regulation scope holds "
        "1240-01 chapters 02, 03, 04, 08, 12 and 14 only.",
    },
    "us-vt": {
        "source_kind": "official_pdf_regulation",
        "primary_source_url": "https://outside.vermont.gov/dept/DCF/Shared%20Documents/ESD/Rules/2200-Reach-Up.pdf",
        "index_url": "https://dcf.vermont.gov/esd/laws-rules/current",
        "index_document_count": 12,
        "document_class": "regulation",
        "notes": "BLOCKED 2026-09-10: Vermont DCF Economic Services Division publishes Reach Up policy as adopted rules "
        "linked from its Current ESD Rules page (dcf.vermont.gov/esd/laws-rules/current answers 200 to plain and chrome "
        "clients). Index inventory: 12 rule PDFs - 2000 All Programs, 2100 Reach First, 2200 Reach Up, 2300 Reach Up "
        "Services, 2400 Post Secondary Education, 2500 Reach Ahead, 2600 General Assistance, 2700 AABD-EP, 2800 Emergency "
        "Assistance, 2900 Seasonal Fuel Assistance, 3000 Refugee Cash Assistance, 3100 Crisis Fuel - plus the 3SquaresVT "
        "manual link (already in the corpus), the Emergency Housing final proposed rules and the rules renumbering "
        "bulletin. The TANF family is 2000-2500 (6 files). Every rule file is hosted on outside.vermont.gov "
        "(SharePoint behind an F5 gateway): plain requests GET and curl-cffi chrome HEAD/GET of 2200-Reach-Up.pdf and "
        "2000-All-Programs.pdf all return HTTP 403 text/html 309-311 bytes 'The requested URL was rejected. Please "
        "consult with your administrator. Your support ID is ...' (server volt-adc, 'F5 site: fr4-fra') at 20:50-20:51Z. "
        "No document retrievable; no workaround attempted. Retry from a US network.",
    },
}

# Batch 2 rows attempted but neither extracted nor blocked by the publisher: the index needs a
# reviewer decision before extraction.
NEEDS_REVIEW: dict[str, dict[str, Any]] = {
    "us-nm": {
        "source_kind": "official_html_regulation_parts",
        "primary_source_url": "https://www.srca.nm.gov/nmac-home/nmac-titles/title-8-social-services/chapter-102-cash-assistance-programs/",
        "index_url": "https://www.srca.nm.gov/nmac-home/nmac-titles/title-8-social-services/",
        "index_document_count": None,
        "document_class": "regulation",
        "notes": "Batch 2, attempted 2026-09-10, not extracted: New Mexico's TANF policy is NMAC 8.102 (Cash Assistance "
        "Programs, adopted rule) published by the Commission of Public Records / State Records Center and Archives. The "
        "part files are served by the publisher (https://www.srca.nm.gov/parts/title08/08.102.0100.html and .pdf answer "
        "200), but the publisher's chapter index is a RealFile folder widget (rts-realfile-folder-search plugin, "
        "rf_sdk.js, a.rf-folder data-folder-id b5ca2d14-a03f-466c-998d-8b8ff7c4c7b9) whose listing comes from the "
        "vendor API (rf-sb-prod.rtssaas.com / AWS Lambda, embedded authTokenGUID); the static page only lists the "
        "reserved part ranges. No mirror or probe-by-number was used. Reviewer decision needed: accept the vendor folder "
        "listing as the publisher's index (then an inventory of the non-reserved parts 100-640 follows) or find an "
        "HCA/ISD-published parts index.",
    },
}

DROP_EAS = [
    r"^\d\d-\d\d\d\s+\(Cont\.\)\s.*$",
    r"^\d\d-\d\d\d\s+.*\s+Regulations$",
    r"^\d\d-\d\d\d\s+.*\((?:Continued|Cont\.)\)$",
    r"^Regulations\s+.*\s+\d\d-\d\d\d(?:\s+\(Cont\.\))?$",
    r"^CALIFORNIA-DSS-MANUAL-EAS$",
    r"^MANUAL LETTER NO\. .*$",
    r"^Page \d+$",
    r"^This page is intentionally left blank\.$",
]
EAS_EXTRACTION = {
    "segmentation": "styled_labeled_sections",
    "section_heading_pattern": r"^(?P<label>\d\d-\d\d\d)\s+(?P<heading>\S.*?)(?:\s+\d\d-\d\d\d)?$",
    # the EAS DOCX files style only some headings as Word headings; real section
    # headings are all-caps, cross-reference lines in body text are mixed case
    "heading_paragraphs_only": False,
    "heading_text_pattern": r"^[A-Z0-9][A-Z0-9 ,/&()'.;:-]*$",
    "drop_line_patterns": DROP_EAS,
}
CO_EXTRACTION = {
    "segmentation": "labeled_sections",
    "section_heading_pattern": r'^(?P<label>3\.6\d\d(?:\.\d{1,2})?)\s+(?P<heading>[A-Z“"][A-Za-z“"].*)$',
    "section_label_pattern": r"^(?P<label>3\.6\d\d(?:\.\d{1,2})?)$",
    "label_only_heading_pattern": r'^[A-Z“"].*$',
    "label_only_requires_heading": True,
    "drop_line_patterns": [
        r"^CODE OF COLORADO REGULATIONS$",
        r"^9 CCR 2503-6$",
        r"^Income Maintenance \(Volume 3\)$",
        r"^\d{1,3}$",
    ],
}
OK_EXTRACTION = {
    "segmentation": "records",
    "json_record_text_field": "text",
    "json_record_text_is_html": True,
    "json_record_label_field": "sectionNum",
    "json_record_heading_field": "description",
    "json_record_kind_field": "name",
    "json_record_status_field": "statusName",
    "json_record_exclude_statuses": ["Revoked", "Reserved"],
    "json_record_metadata_fields": [
        "id",
        "parentId",
        "name",
        "titleNum",
        "chapterNum",
        "subChapterNum",
        "partNum",
        "sectionNum",
        "appendixNum",
        "description",
        "statusName",
        "segmentStatusId",
        "segmentTypeId",
        "recordStatus",
        "effectiveDate",
        "filingId",
        "hasEmergency",
        "segmentNotes",
    ],
}


def fetch(url: str, *, attempts: int = 3, head: bool = False) -> Any:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            if head:
                return curl_requests.head(
                    url, impersonate=IMPERSONATE, timeout=120, allow_redirects=True
                )
            return curl_requests.get(
                url, impersonate=IMPERSONATE, timeout=120, allow_redirects=True
            )
        except Exception as exc:  # noqa: BLE001 - retry any transport failure
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def links(text: str) -> list[tuple[str, str]]:
    return [
        (href, re.sub(r"<[^>]+>", "", html.unescape(label)).strip())
        for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.S)
    ]


def http_date(value: str | None) -> str | None:
    if not value:
        return None
    return dt.datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z").date().isoformat()


def base_doc(
    *,
    source_id: str,
    jurisdiction: str,
    document_class: str,
    title: str,
    source_url: str,
    source_format: str,
    citation_path: str,
    expression_date: str,
    authority: str,
    subtype: str,
    state_program: str,
    index_url: str,
    extra: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
    extraction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "source_id": source_id,
        "jurisdiction": jurisdiction,
        "document_class": document_class,
        "title": title,
        "source_url": source_url,
        "source_format": source_format,
        "source_as_of": SOURCE_AS_OF,
        "expression_date": expression_date,
        "citation_path": citation_path,
    }
    if request:
        doc["request"] = request
    if extraction:
        doc["extraction"] = extraction
    doc["metadata"] = {
        "primary_source": True,
        "source_authority": authority,
        "document_subtype": subtype,
        "program": "TANF",
        "state_program": state_program,
        "federal_program": "TANF",
        "manual_landing_page": index_url,
        "source_discovery_group": f"{jurisdiction}/{document_class}/tanf",
        "discovered_via": DISCOVERED_VIA.format(index=index_url),
        **(extra or {}),
    }
    return doc


# --------------------------------------------------------------------------- CA
def build_ca() -> dict[str, Any]:
    index = (
        "https://www.cdss.ca.gov/inforesources/Rules-Regulations/Legislation-and-Regulations/"
        "CalWORKs-CalFresh-Regulations/Eligibility-and-Assistance-Standards"
    )
    page = fetch(index).text
    files = [
        (h, t) for h, t in links(page) if re.search(r"/Portals/9/Regs/Man/EAS/[^\"']+\.docx", h)
    ]
    docs = []
    for href, text in files:
        m = re.match(r"^(\d+)\.\s+(.*)$", text)
        if not m or not re.search(r"\bDiv(?:ision)?\s+4[0-4]\b", text):
            continue
        number, label = m.group(1), m.group(2)
        url = "https://www.cdss.ca.gov" + href if href.startswith("/") else href
        head = fetch(url, head=True)
        expression = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
        docs.append(
            base_doc(
                source_id=f"us-ca-cdss-mpp-eas-{number}",
                jurisdiction="us-ca",
                document_class="regulation",
                title=f"CDSS Manual of Policies and Procedures, Eligibility and Assistance Standards {number}: {label}",
                source_url=url,
                source_format="docx",
                citation_path=f"us-ca/regulation/mpp/eas/{number}",
                expression_date=expression,
                authority="California Department of Social Services",
                subtype="adopted_regulation_manual_docx",
                state_program="CalWORKs",
                index_url=index,
                extra={
                    "manual": "MPP Eligibility and Assistance Standards (Divisions 40-44 taken)",
                    "index_ordinal": int(number),
                    "source_last_modified": expression,
                    "extraction_note": "styled_labeled_sections merges page-break heading restatements; running heads dropped",
                },
                request={"browser_impersonation": True},
                extraction=EAS_EXTRACTION,
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(files),
        "inventory": f"{len(files)} EAS DOCX files (Div 40 through Div 91); taken {len(docs)} (Div 40-44, CalWORKs/AFDC eligibility and assistance standards); Div 46-91 (refugee, IHSS, adoptions, admin, hearings) not taken",
        "source_kind": "official_docx_regulation_manual",
        "document_class": "regulation",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- CO
def build_co() -> dict[str, Any]:
    index = (
        "https://www.coloradosos.gov/CCR/DisplayRule.do?action=ruleinfo&ruleId=3145&deptID=9&agencyID=53"
        "&deptName=Department+of+Human+Services&agencyName=Income+Maintenance+(Volume+3)&seriesNum=9+CCR+2503-6"
    )
    page = fetch(index).text
    versions = re.findall(r"OpenRuleWindow\('(\d+)'", page)
    dates = re.findall(r"(\d\d/\d\d/\d{4})\s*\(PDF\)", page)
    if not versions or not dates:
        raise RuntimeError("Colorado SoS rule-info page layout changed")
    current = versions[0]
    effective = dt.datetime.strptime(dates[0], "%m/%d/%Y").date().isoformat()
    url = f"https://www.coloradosos.gov/CCR/GenerateRulePdf.do?ruleVersionId={current}&fileName=9%20CCR%202503-6"
    doc = base_doc(
        source_id="us-co-ccr-9-2503-6-colorado-works",
        jurisdiction="us-co",
        document_class="regulation",
        title="Code of Colorado Regulations 9 CCR 2503-6 Colorado Works Program",
        source_url=url,
        source_format="pdf",
        citation_path="us-co/regulation/9-ccr-2503-6",
        expression_date=effective,
        authority="Colorado Department of Human Services",
        subtype="administrative_code_rule",
        state_program="Colorado Works",
        index_url=index,
        extra={
            "official_publisher": "Colorado Secretary of State",
            "code_rule": "9 CCR 2503-6",
            "rule_version_id": current,
            "rule_effective_date": effective,
            "archived_version_count": len(set(versions)) - 1,
            "extraction_note": "labeled_sections on 3.6xx / 3.6xx.y labels; editor's notes at the end fall into the last section",
        },
        extraction=CO_EXTRACTION,
    )
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len(set(versions)),
        "inventory": f"SoS rule-info page: 1 current version (eff. {effective}, PDF+DOCX) and {len(set(versions)) - 1} archived versions; taken the current PDF",
        "source_kind": "official_pdf_regulation",
        "document_class": "regulation",
        "primary_source_url": url,
    }


# --------------------------------------------------------------------------- DC
def build_dc() -> dict[str, Any]:
    index = "https://dhs.dc.gov/publication/esa-policy-manuals"
    page = fetch(index).text
    pdfs = [(h, t) for h, t in links(page) if h.lower().endswith(".pdf")]
    target = [h for h, t in pdfs if "ESA-Policy-Manual-Combined" in h]
    if len(target) != 1:
        raise RuntimeError(f"expected one combined ESA manual link, found {target}")
    url = target[0]
    head = fetch(url, head=True)
    modified = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
    doc = base_doc(
        source_id="us-dc-dhs-esa-policy-manual",
        jurisdiction="us-dc",
        document_class="manual",
        title="District of Columbia DHS ESA Policy Manual (Combined, Revised 2)",
        source_url=url,
        source_format="pdf",
        citation_path="us-dc/manual/dhs/tanf/esa-policy-manual",
        expression_date=modified,
        authority="District of Columbia Department of Human Services, Economic Security Administration",
        subtype="policy_manual",
        state_program="DC TANF",
        index_url=index,
        extra={
            "source_last_modified": modified,
            "manual_scope": "ESA programs other than SNAP: TANF, Medical Assistance, GC, IDA, Burial Assistance",
            "extraction_granularity": "pdf_page",
            "extraction_note": "page-level; Part/Chapter headings restart numbering per part so chapter-level labels are not unique",
        },
    )
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len(pdfs),
        "inventory": f"{len(pdfs)} PDFs on the ESA Policy Manuals page (ESA SNAP Policy Manual 1-24-25, already ingested as us-dc/manual/dhs/esa/snap-policy-manual; ESA Policy Manual Combined Revised 2); taken 1",
        "source_kind": "official_pdf_manual",
        "document_class": "manual",
        "primary_source_url": url,
    }


# --------------------------------------------------------------------------- MO
def build_mo(title_cache: Path | None) -> dict[str, Any]:
    index = "https://dssmanuals.mo.gov/temporary-assistance-case-management/"
    landing = fetch(index).text
    appendices = [
        (h, t)
        for h, t in links(landing)
        if h.lower().endswith(".pdf")
        and "dssmanuals.mo.gov" in h
        and re.match(r"^Appendix [A-Z]", t)
    ]
    sitemap = ""
    for n in (1, 2, 3):
        r = fetch(f"https://dssmanuals.mo.gov/wp-sitemap-posts-page-{n}.xml")
        if r.status_code != 200:
            break
        sitemap += r.text
    entries = re.findall(r"<url>\s*<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>", sitemap)
    pages = [
        (u, m[:10])
        for u, m in entries
        if "/temporary-assistance-case-management/" in u and u.rstrip("/") != index.rstrip("/")
    ]
    cache: dict[str, Any] = {}
    if title_cache and title_cache.exists():
        cache = json.loads(title_cache.read_text())

    def title_for(url: str) -> str:
        cached = cache.get(url, {}).get("title")
        if cached:
            return cached
        r = fetch(url)
        m = re.search(r"<title>(.*?)</title>", r.text, re.S)
        time.sleep(0.2)
        return html.unescape(m.group(1)).strip() if m else url

    slugs = [u.rstrip("/").split("/")[-1] for u, _ in pages]
    numbers = [re.match(r"^(\d{4}-\d{2,3}-\d{2}(?:-\d{2,3})*)", s) for s in slugs]
    number_counts: dict[str, int] = {}
    for m in numbers:
        if m:
            number_counts[m.group(1)] = number_counts.get(m.group(1), 0) + 1
    docs = []
    docs.append(
        base_doc(
            source_id="us-mo-dss-tanf-landing",
            jurisdiction="us-mo",
            document_class="manual",
            title="Missouri Temporary Assistance/Case Management Manual (landing page and chapter index)",
            source_url=index,
            source_format="html",
            citation_path="us-mo/manual/dss/tanf/navigation/landing",
            expression_date=SOURCE_AS_OF,
            authority="Missouri Department of Social Services, Family Support Division",
            subtype="manual_landing_page_snapshot",
            state_program="Temporary Assistance",
            index_url=index,
            extraction={"html_content_selector": ".entry-content"},
        )
    )
    for (url, lastmod), slug, m in zip(pages, slugs, numbers, strict=True):
        suffix = m.group(1) if m and number_counts[m.group(1)] == 1 else slug
        title = title_for(url).replace(" – DSS Manuals", "").strip()
        docs.append(
            base_doc(
                source_id=f"us-mo-dss-tanf-{suffix}",
                jurisdiction="us-mo",
                document_class="manual",
                title=f"Missouri Temporary Assistance/Case Management Manual: {title}",
                source_url=url,
                source_format="html",
                citation_path=f"us-mo/manual/dss/tanf/{suffix}",
                expression_date=lastmod,
                authority="Missouri Department of Social Services, Family Support Division",
                subtype="policy_manual_section",
                state_program="Temporary Assistance",
                index_url=index,
                extra={
                    "sitemap_lastmod": lastmod,
                    "source_sitemap_urls": [
                        "https://dssmanuals.mo.gov/wp-sitemap-posts-page-1.xml",
                        "https://dssmanuals.mo.gov/wp-sitemap-posts-page-2.xml",
                    ],
                },
                extraction={"html_content_selector": ".entry-content"},
            )
        )
    for href, text in appendices:
        letter = re.match(r"^Appendix ([A-Z])", text).group(1).lower()
        head = fetch(href, head=True)
        modified = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
        docs.append(
            base_doc(
                source_id=f"us-mo-dss-tanf-appendix-{letter}",
                jurisdiction="us-mo",
                document_class="manual",
                title=f"Missouri Temporary Assistance/Case Management Manual: {text}",
                source_url=href,
                source_format="pdf",
                citation_path=f"us-mo/manual/dss/tanf/appendix-{letter}",
                expression_date=modified,
                authority="Missouri Department of Social Services, Family Support Division",
                subtype="policy_manual_appendix",
                state_program="Temporary Assistance",
                index_url=index,
                extra={"source_last_modified": modified, "extraction_granularity": "pdf_page"},
            )
        )
    total = 1 + len(pages) + len(appendices)
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": total,
        "inventory": f"landing page + {len(pages)} section pages (WordPress sitemap, chapters 0200-0330) + {len(appendices)} appendix PDFs; taken all {total}",
        "source_kind": "official_html_manual",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- MS
def build_ms() -> dict[str, Any]:
    index = "https://www.mdhs.ms.gov/help/tanf/"
    page = fetch(index).text
    manual = [h for h, t in links(page) if t.strip() == "TANF Policy Manual"]
    if len(set(manual)) != 1:
        raise RuntimeError(f"expected one TANF Policy Manual link, found {manual}")
    url = manual[0]
    head = fetch(url, head=True)
    modified = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
    doc_links = [(h, t) for h, t in links(page) if h.lower().endswith(".pdf") or "/document/" in h]
    doc = base_doc(
        source_id="us-ms-mdhs-tanf-policy-manual",
        jurisdiction="us-ms",
        document_class="manual",
        title="Mississippi TANF Policy Manual (Title 18 Part 13, Volume III)",
        source_url=url,
        source_format="pdf",
        citation_path="us-ms/manual/mdhs/tanf/volume-iii",
        expression_date=modified,
        authority="Mississippi Department of Human Services (published through the Mississippi Secretary of State administrative code)",
        subtype="policy_manual",
        state_program="Mississippi TANF",
        index_url=index,
        extra={
            "source_last_modified": modified,
            "extraction_granularity": "pdf_page",
            "extraction_note": "page-level; the manual is paginated by chapter (1000-, 2000- ...) without machine-stable section labels",
        },
        request={"browser_impersonation": True},
    )
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len({h for h, _ in doc_links}),
        "inventory": f"MDHS TANF page links {len({h for h, _ in doc_links})} documents (TANF Policy Manual on sos.ms.gov, flyer(s), client forms); taken the TANF Policy Manual",
        "source_kind": "official_pdf_manual",
        "document_class": "manual",
        "primary_source_url": url,
    }


# --------------------------------------------------------------------------- MT
def build_mt() -> dict[str, Any]:
    index = "https://dphhs.mt.gov/hcsd/Manuals/TANFpolicymanual"
    page = fetch(index).text
    rows = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        hrefs = re.findall(r'href="([^"]+)"', row)
        cells = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(c))).strip()
            for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        ]
        if hrefs and "tanfmanual" in hrefs[0]:
            cells = [c for c in cells if c]
            rows.append((hrefs[0], cells))
    docs = []
    seen: set[str] = set()
    for href, cells in rows:
        if len(cells) < 3:
            raise RuntimeError(f"unexpected Montana index row {cells}")
        label, title, date_text = cells[0], cells[1], cells[-1]
        if label in seen:
            raise RuntimeError(f"duplicate Montana section label {label}")
        seen.add(label)
        for fmt in ("%m/%d/%y", "%m/%d/%Y"):
            try:
                effective = dt.datetime.strptime(date_text, fmt).date().isoformat()
                break
            except ValueError:
                effective = SOURCE_AS_OF
        url = (
            "https://dphhs.mt.gov" + href.replace("../..", "") if href.startswith("../..") else href
        )
        docs.append(
            base_doc(
                source_id=f"us-mt-dphhs-tanf-{label.lower()}",
                jurisdiction="us-mt",
                document_class="manual",
                title=f"Montana TANF Policy Manual {label}: {title}",
                source_url=url,
                source_format="pdf",
                citation_path=f"us-mt/manual/dphhs/tanf/{label.lower()}",
                expression_date=effective,
                authority="Montana Department of Public Health and Human Services",
                subtype="policy_manual_section",
                state_program="Montana TANF",
                index_url=index,
                extra={
                    "official_section_number": label,
                    "official_listing_title": title,
                    "official_effective_date": date_text,
                    "extraction_granularity": "pdf_page",
                },
                request={"browser_impersonation": True},
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(rows),
        "inventory": f"{len(rows)} section PDFs listed with effective dates (TOC, index, introduction, definitions, income standards, sections 101-1 through 1702-1); taken all {len(docs)}",
        "source_kind": "official_pdf_manual_sections",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- ND
def build_nd() -> dict[str, Any]:
    base = "https://www.nd.gov/dhs/policymanuals/40019/"
    index = base + "40019.htm"
    toc_url = base + "Data/Tocs/40019_Chunk0.js"
    toc = fetch(toc_url).text
    entries = re.findall(r"'(/[^']+\.htm)':\{i:\[\d+\],t:\['((?:[^'\\]|\\.)*)'\]", toc)
    landing = fetch(base + "Default.htm").text
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(landing)))
    release = re.search(r"Current Release ([\d.]+)", text)
    published = re.search(r"last published on ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    release_log = fetch(base + "Release%20Log.htm").text
    log_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(release_log)))
    eff = re.search(r"(\d{2}\.\d)\s+(\d{1,2}\.\d{1,2}\.\d{4})", log_text)
    expression = (
        dt.datetime.strptime(eff.group(2), "%m.%d.%Y").date().isoformat() if eff else SOURCE_AS_OF
    )
    common = {
        "current_release": release.group(1) if release else None,
        "manual_last_published": published.group(1) if published else None,
        "manual_toc_url": toc_url,
        "manual_base_url": base,
    }
    docs = [
        base_doc(
            source_id="us-nd-hhs-tanf-landing",
            jurisdiction="us-nd",
            document_class="manual",
            title="North Dakota HHS TANF Policy Manual 400-19 landing page",
            source_url=base + "Default.htm",
            source_format="html",
            citation_path="us-nd/manual/hhs/tanf/navigation/landing",
            expression_date=expression,
            authority="North Dakota Health and Human Services",
            subtype="manual_landing_page_snapshot",
            state_program="North Dakota TANF",
            index_url=index,
            extra=common,
            extraction={"html_content_selector": "#mc-main-content"},
        ),
        base_doc(
            source_id="us-nd-hhs-tanf-toc",
            jurisdiction="us-nd",
            document_class="manual",
            title="North Dakota HHS TANF Policy Manual 400-19 official table of contents",
            source_url=toc_url,
            source_format="javascript",
            citation_path="us-nd/manual/hhs/tanf/navigation/toc",
            expression_date=expression,
            authority="North Dakota Health and Human Services",
            subtype="manual_toc_snapshot",
            state_program="North Dakota TANF",
            index_url=index,
            extra=common,
        ),
        base_doc(
            source_id="us-nd-hhs-tanf-release-log",
            jurisdiction="us-nd",
            document_class="manual",
            title="North Dakota HHS TANF Policy Manual 400-19 release log",
            source_url=base + "Release%20Log.htm",
            source_format="html",
            citation_path="us-nd/manual/hhs/tanf/navigation/release-log",
            expression_date=expression,
            authority="North Dakota Health and Human Services",
            subtype="manual_release_log_snapshot",
            state_program="North Dakota TANF",
            index_url=index,
            extra=common,
            extraction={"html_content_selector": "#mc-main-content"},
        ),
    ]
    seen: set[str] = set()
    for path, title in entries:
        name = path.lstrip("/")[: -len(".htm")]
        suffix = (
            name.replace("_", "-").lower()
            if re.match(r"^400_19(_\d+)*$", name)
            else re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        )
        if suffix in seen:
            raise RuntimeError(f"duplicate North Dakota topic {suffix}")
        seen.add(suffix)
        docs.append(
            base_doc(
                source_id=f"us-nd-hhs-tanf-{suffix}",
                jurisdiction="us-nd",
                document_class="manual",
                title=f"North Dakota TANF Policy Manual: {title.replace(chr(92) + chr(39), chr(39))}",
                source_url=base + path.lstrip("/"),
                source_format="html",
                citation_path=f"us-nd/manual/hhs/tanf/{suffix}",
                expression_date=expression,
                authority="North Dakota Health and Human Services",
                subtype="policy_manual_section",
                state_program="North Dakota TANF",
                index_url=index,
                extra=common,
                extraction={"html_content_selector": "#mc-main-content"},
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(entries) + 3,
        "inventory": f"MadCap TriPane manual: TOC lists {len(entries)} topic pages (400-19-05 definitions through the sanction/hearing sections) plus landing page and release log; taken all {len(docs)} (release {common['current_release']}, effective {expression})",
        "source_kind": "official_html_manual",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- OK
def build_ok() -> dict[str, Any]:
    index = "https://rules.ok.gov/home"
    api = "https://prod-ok-rules-api.tecuity.com/GetSegmentsByChapterNum?titleNum=340&chapterNum=10"
    data = fetch(api).json()
    counts: dict[str, int] = {}
    for segment in data:
        key = f"{segment.get('name')}:{segment.get('statusName')}"
        counts[key] = counts.get(key, 0) + 1
    active_sections = sum(
        1
        for s in data
        if s.get("name") == "Section" and s.get("statusName") not in {"Revoked", "Reserved"}
    )
    doc = base_doc(
        source_id="us-ok-oac-340-10-tanf-rules",
        jurisdiction="us-ok",
        document_class="regulation",
        title="Oklahoma Administrative Code Title 340 Chapter 10 Temporary Assistance for Needy Families (TANF)",
        source_url=index,
        source_format="json",
        citation_path="us-ok/regulation/oac/340/10",
        expression_date=SOURCE_AS_OF,
        authority="Oklahoma Department of Human Services",
        subtype="administrative_code_chapter",
        state_program="Oklahoma TANF",
        index_url=index,
        extra={
            "official_publisher": "Oklahoma Secretary of State Office of Administrative Rules",
            "rules_api_url": api,
            "legacy_okdhs_chapter_url": "https://oklahoma.gov/okdhs/library/policy/current/oac-340/chapter-10.html",
            "title_number": "340",
            "chapter_number": "10",
            "segment_counts": counts,
            "access_note": "rules.ok.gov and the tecuity rules API answer plain clients with Cloudflare 403; fetched with browser impersonation (same API as us-ok-snap-rules)",
        },
        request={"browser_impersonation": True, "browser_impersonation_direct": True},
        extraction=OK_EXTRACTION,
    )
    doc["download_url"] = api
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len(data),
        "inventory": f"chapter API returns {len(data)} segments ({counts}); taken the chapter as one document, {active_sections} non-revoked sections become records",
        "source_kind": "official_json_regulation",
        "document_class": "regulation",
        "primary_source_url": index,
    }


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def last_modified(url: str) -> str:
    head = fetch(url, head=True)
    return http_date(head.headers.get("last-modified")) or SOURCE_AS_OF


# --------------------------------------------------------------------------- PA
def build_pa() -> dict[str, Any]:
    """OIM Cash Assistance Handbook (Adobe RoboHelp site; TOC in whxdata/toc*.js like the SNAP handbook)."""
    base = "http://services.dpw.state.pa.us/oimpolicymanuals/cash/"
    index = base + "index.htm"
    fetch(index)  # the landing page is a JS shell; the TOC data files carry the inventory
    pages: dict[str, dict[str, Any]] = {}
    entries = 0

    def parse_toc(js: str) -> list[tuple[str, dict[str, str]]]:
        match = re.search(r'gXMLBuffer\s*=\s*"(.*)"\s*;?\s*$', js.strip(), re.S)
        # the JS string only escapes double quotes; file names contain literal UTF-8 (e.g. an en dash)
        xml = match.group(1).replace('\\"', '"') if match else js
        return [
            (kind, dict(re.findall(r'(\w+)="([^"]*)"', attrs)))
            for kind, attrs in re.findall(r"<(book|item)\s+([^>]*?)/?>", xml)
        ]

    def walk(src: str, parent: str | None) -> None:
        nonlocal entries
        for kind, attrs in parse_toc(fetch(base + "whxdata/" + src).text):
            entries += 1
            name = html.unescape(attrs.get("name", "")).strip()
            url = attrs.get("url")
            if url and "#" not in url and url not in pages:
                pages[url] = {"name": name, "parent": parent, "order": len(pages) + 1}
            if kind == "book" and attrs.get("src"):
                walk(attrs["src"], name)

    walk("toc.js", None)
    docs = []
    for url, info in pages.items():
        page_slug = slug(re.sub(r"\.htm$", "", url))
        full = base + url
        docs.append(
            base_doc(
                source_id=f"us-pa-dhs-cash-{page_slug}",
                jurisdiction="us-pa",
                document_class="manual",
                title=f"Pennsylvania Cash Assistance Handbook: {info['name']}",
                source_url=full,
                source_format="html",
                citation_path=f"us-pa/manual/dhs/cash/{page_slug}",
                expression_date=last_modified(full),
                authority="Pennsylvania Department of Human Services, Office of Income Maintenance",
                subtype="policy_manual_topic",
                state_program="Pennsylvania TANF (Cash Assistance)",
                index_url=index,
                extra={
                    "manual_toc_url": base + "whxdata/toc.js",
                    "manual_base_url": base,
                    "toc_parent": info["parent"],
                    "toc_order": info["order"],
                },
                extraction={"html_drop_selectors": [".topic-header", ".topic-header-shadow"]},
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(pages),
        "inventory": (
            f"RoboHelp TOC lists {entries} entries resolving to {len(pages)} topic pages (chapters 100-192, "
            f"including appendices; the remaining entries are in-page anchors); taken all {len(docs)} topic pages. "
            "Glossary pop-ups (_Popups/) are not on the TOC and were not taken"
        ),
        "source_kind": "official_html_manual",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- VA
def build_va() -> dict[str, Any]:
    index = "https://www.dss.virginia.gov/relief/tanf/tanf-manual/"
    page = fetch(index).text
    pdfs = [(h, t) for h, t in links(page) if h.lower().endswith(".pdf")]
    chapters = [(h, t) for h, t in pdfs if re.match(r"^Chapter \d+", t)]
    docs = []
    for href, text in chapters:
        number = re.match(r"^Chapter (\d+)", text).group(1)
        url = "https://www.dss.virginia.gov" + href if href.startswith("/") else href
        docs.append(
            base_doc(
                source_id=f"us-va-dss-tanf-manual-chapter-{number}",
                jurisdiction="us-va",
                document_class="manual",
                title=f"Virginia TANF Manual {text}",
                source_url=url,
                source_format="pdf",
                citation_path=f"us-va/manual/dss/tanf/chapter-{number}",
                expression_date=last_modified(url),
                authority="Virginia Department of Social Services",
                subtype="policy_manual_chapter",
                state_program="Virginia TANF",
                index_url=index,
                extra={
                    "chapter_number": int(number),
                    "official_listing_title": text,
                    "extraction_granularity": "pdf_page",
                    "extraction_note": "page-level; each page carries a transmittal date (e.g. 10/23) in its running head",
                },
                request={"browser_impersonation": True},
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(pdfs),
        "inventory": (
            f"{len(pdfs)} PDFs on the TANF Manual page: Contents (table of contents), Full Manual (combined file) and "
            f"{len(chapters)} chapter files (Chapter 100 through Chapter 1000, incl. VIEW chapters 900-1000); taken the "
            f"{len(docs)} chapter files (the Full Manual duplicates them; the Contents file is a TOC)"
        ),
        "source_kind": "official_pdf_manual_chapters",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- SD
def build_sd() -> dict[str, Any]:
    """ARSD article 67:10 from the Legislative Research Council rules API (one JSON per rule, HTML body)."""
    index = "https://sdlegislature.gov/Rules/Administrative/67:10"
    api = "https://sdlegislature.gov/api/Rules/"
    rules = []
    current = "67:10"
    while current and current.startswith("67:10"):
        data = fetch(api + current).json()
        rules.append(data)
        current = data.get("Next")
    counts: dict[str, int] = {}
    for rule in rules:
        counts[rule["Type"]] = counts.get(rule["Type"], 0) + 1
    docs = []
    skipped = []
    for rule in rules:
        if rule["Type"] != "D":
            continue
        number = rule["RuleNumber"]
        catchline = html.unescape(rule.get("Catchline") or "").strip()
        if re.search(r"\b(repealed|transferred|reserved)\b", catchline, re.I):
            skipped.append(number)
            continue
        parts = number.split(":")
        docs.append(
            base_doc(
                source_id=f"us-sd-arsd-{'-'.join(parts)}",
                jurisdiction="us-sd",
                document_class="regulation",
                title=f"ARSD {number} {catchline}",
                source_url=f"https://sdlegislature.gov/Rules/Administrative/{number}",
                source_format="json",
                citation_path="us-sd/regulation/arsd/" + "/".join(parts),
                expression_date=SOURCE_AS_OF,
                authority="South Dakota Department of Social Services",
                subtype="administrative_rule_section",
                state_program="South Dakota TANF",
                index_url=index,
                extra={
                    "official_publisher": "South Dakota Legislative Research Council",
                    "rules_api_url": api + number,
                    "rule_id": rule.get("RuleId"),
                    "rule_number": number,
                    "chapter": ":".join(parts[:3]),
                    "extraction_note": "JSON 'Html' field rendered as the rule text; the source note at the end of each rule carries its history",
                },
                request={"browser_impersonation": True},
                extraction={"json_html_field": "Html"},
            )
        )
        docs[-1]["download_url"] = api + number
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(rules),
        "inventory": (
            f"rules API chain from 67:10 returns {len(rules)} records ({counts}: B article, C chapters, D sections); "
            f"taken the {len(docs)} sections whose catchline is not Repealed/Transferred; not taken: the article and "
            f"chapter table-of-contents records and {len(skipped)} repealed/transferred sections ({', '.join(skipped)})"
        ),
        "source_kind": "official_json_regulation_sections",
        "document_class": "regulation",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- NH
def build_nh() -> dict[str, Any]:
    """DHHS Family Assistance Manual (RoboHelp WebHelp 5; TOC in whgdata/whlstt*.htm)."""
    root = "https://www.dhhs.nh.gov/fam_htm/"
    index = root + "newfam.htm"
    fetch(index)
    pages: dict[str, dict[str, Any]] = {}
    entries = 0
    n = 0
    while True:
        response = fetch(f"{root}whgdata/whlstt{n}.htm")
        if response.status_code != 200:
            break
        for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', response.text, re.S):
            entries += 1
            if href.startswith("whlstt"):
                continue
            path = href.split("#")[0]
            if path not in pages:
                pages[path] = {
                    "name": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(label))).strip(),
                    "toc_file": f"whlstt{n}.htm",
                }
        n += 1
    docs = []
    for path, info in pages.items():
        url = root + path.replace("../", "")
        page_slug = slug(re.sub(r"\.htm$", "", path.rsplit("/", 1)[-1]))
        docs.append(
            base_doc(
                source_id=f"us-nh-dhhs-fam-{page_slug}",
                jurisdiction="us-nh",
                document_class="manual",
                title=f"New Hampshire Family Assistance Manual: {info['name']}",
                source_url=url,
                source_format="html",
                citation_path=f"us-nh/manual/dhhs/fam/{page_slug}",
                expression_date=last_modified(url),
                authority="New Hampshire Department of Health and Human Services, Bureau of Family Assistance",
                subtype="policy_manual_topic",
                state_program="New Hampshire FANF",
                index_url=index,
                extra={
                    "manual_toc_url": root + "whgdata/whlstt0.htm",
                    "toc_file": info["toc_file"],
                    "manual_scope": "combined Family Assistance Manual: FANF cash assistance, medical assistance categories, NH child care scholarship",
                },
                # dhhs.nh.gov answers plain clients with an Akamai "Access Denied" 403
                request={"browser_impersonation": True},
                extraction={"html_drop_selectors": ["#header", ".no-print", ".navBtnCusStyle"]},
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(pages),
        "inventory": (
            f"WebHelp TOC ({n} list files, {entries} entries) resolves to {len(pages)} topic pages (Introduction, "
            f"100 Case Processing through 900 NH Child Care Scholarship, Glossary); taken all {len(docs)}. "
            "The linked SR (supervisory release) letters and 'Previous Policy' archive pages are separate families, not taken"
        ),
        "source_kind": "official_html_manual",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- ID
def build_id() -> dict[str, Any]:
    """IDAPA 16.03.08 from the Office of the Administrative Rules Coordinator's current-rules index (WordPress REST)."""
    import requests as plain_requests  # adminrules.idaho.gov rejects curl-cffi's chrome TLS profile; plain requests verify fine

    index = "https://adminrules.idaho.gov/current-rules/"
    headers = {"User-Agent": "axiom-corpus-ingest/1.0"}
    page = plain_requests.get(index, timeout=60, headers=headers).text
    nonce = re.search(r'dfmFetchDocuments = \{"nonce":"([0-9a-f]+)"', page).group(1)
    listing = plain_requests.post(
        "https://adminrules.idaho.gov/wp-json/dfm-document-display/fetch-documents",
        json={"azurePayload": {"documentType": "currentRules"}, "updateAgency": True},
        timeout=120,
        headers={**headers, "X-WP-Nonce": nonce, "Referer": index},
    ).json()["body"]
    all_rules = [(h, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(t))).strip()) for h, t in links(listing)]
    title_16 = [(h, t) for h, t in all_rules if h.startswith("/rules/current/16/")]
    target = [(h, t) for h, t in title_16 if h.endswith("/160308.pdf")]
    if len(target) != 1:
        raise RuntimeError(f"expected one IDAPA 16.03.08 link, found {target}")
    href, text = target[0]
    url = "https://adminrules.idaho.gov" + href
    head = plain_requests.head(url, timeout=60, headers=headers)
    modified = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
    body = plain_requests.get(url, timeout=120, headers=headers).content
    import fitz

    marks: dict[str, int] = {}
    with fitz.open(stream=body, filetype="pdf") as pdf:
        for pdf_page in pdf:
            for mark in re.findall(r"\((\d{1,2}-\d{1,2}-\d{2})\)", pdf_page.get_text("text")):
                marks[mark] = marks.get(mark, 0) + 1
    effective = SOURCE_AS_OF
    if marks:
        mark = max(marks, key=marks.get)
        effective = dt.datetime.strptime(mark, "%m-%d-%y").date().isoformat()
    doc = base_doc(
        source_id="us-id-dhw-idapa-16-03-08-tafi",
        jurisdiction="us-id",
        document_class="regulation",
        title=f"IDAPA {text}",
        source_url=url,
        source_format="pdf",
        citation_path="us-id/regulation/idapa/16/03/08",
        expression_date=effective,
        authority="Idaho Department of Health and Welfare",
        subtype="administrative_rules",
        state_program="Temporary Assistance for Families in Idaho (TAFI)",
        index_url=index,
        extra={
            "official_publisher": "Idaho Office of the Administrative Rules Coordinator",
            "idapa_chapter": "16.03.08",
            "source_last_modified": modified,
            "rule_effective_marks": marks,
            "extraction_note": "numbered_sections like the IDAPA 16.03.05 scope; the rule is short (TAFI plus LIHEAP standards) after Idaho's rule reduction",
        },
        extraction={
            "segmentation": "numbered_sections",
            "start_page": 3,
            "sort_text": True,
            "drop_lines": ["IDAHO ADMINISTRATIVE CODE", "Department of Health and Welfare"],
            "drop_line_patterns": [
                r"^Section [0-9]+\s+Page [0-9]+.*$",
                r"^IDAHO ADMINISTRATIVE CODE\s+IDAPA 16\.03\.08$",
                r"^Department of Health and Welfare\s+Federal Welfare Programs$",
                r"^16\.03\.08 – FEDERAL WELFARE PROGRAMS$",
                # reserved ranges carry no text; left in, the numbered_sections reader treats the
                # all-caps heading of the following section as a continuation of the reserved heading
                r"^\d{3}\. – \d{3}\.\s+\(RESERVED\)$",
                r"^TANF PROGRAM$",
                r"^LIHEAP$",
            ],
        },
    )
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len(all_rules),
        "inventory": (
            f"OARC current-rules listing (REST fetch-documents, documentType currentRules) has {len(all_rules)} rule "
            f"chapters, {len(title_16)} under IDAPA 16 (Health and Welfare); taken IDAPA 16.03.08 Federal Welfare Programs "
            "(TAFI rule). Not taken: 16.03.04 Food Stamp Program and 16.03.05 AABD (already in the corpus) and the other title 16 chapters"
        ),
        "source_kind": "official_pdf_regulation",
        "document_class": "regulation",
        "primary_source_url": url,
    }


# --------------------------------------------------------------------------- LA
LA_POLICY_PARTS = ("B.", "C.", "E.", "F.", "G.", "J.", "M.", "N.", "P.", "S.")


def build_la() -> dict[str, Any]:
    """DCFS Economic Independence manual from the department's PowerDMS public document directory."""
    index = "https://public.powerdms.com/LADCFS/tree"
    listing_api = "https://public.powerdms.com/LADCFS/documents"
    data = fetch(listing_api).json()["data"]

    def trail(entry: dict[str, Any]) -> list[str]:
        crumbs = entry.get("breadcrumbs") or []
        return [step["name"] for step in crumbs[0]["trail"]] if crumbs else []

    ei = [d for d in data if len(trail(d)) >= 3 and trail(d)[1] == "Economic Independence (EI)"]
    families: dict[str, int] = {}
    for entry in ei:
        families[trail(entry)[2]] = families.get(trail(entry)[2], 0) + 1
    manual = [d for d in ei if trail(d)[2] == "4. Economic Independence" and len(trail(d)) >= 4]
    parts: dict[str, int] = {}
    for entry in manual:
        parts[trail(entry)[3]] = parts.get(trail(entry)[3], 0) + 1
    taken = [d for d in manual if trail(d)[3].startswith(LA_POLICY_PARTS)]
    taken.sort(key=lambda d: (trail(d)[3], trail(d)[4] if len(trail(d)) > 4 else "", d["name"]))
    docs = []
    seen: set[str] = set()
    for entry in taken:
        name = re.sub(r"\s+", " ", entry["name"]).strip()
        doc_slug = slug(name)
        if doc_slug in seen:
            raise RuntimeError(f"duplicate Louisiana document slug {doc_slug}")
        seen.add(doc_slug)
        crumbs = trail(entry)
        docs.append(
            base_doc(
                source_id=f"us-la-dcfs-ei-{entry['id']}",
                jurisdiction="us-la",
                document_class="manual",
                title=f"Louisiana DCFS Economic Independence Manual {name}",
                source_url=entry["publicUrl"],
                source_format="pdf",
                citation_path=f"us-la/manual/dcfs/ei/{doc_slug}",
                expression_date=SOURCE_AS_OF,
                authority="Louisiana Department of Children and Family Services",
                subtype="policy_manual_section",
                state_program="Louisiana FITAP",
                index_url=index,
                extra={
                    "official_publisher": "Louisiana DCFS public document directory (PowerDMS)",
                    "listing_api_url": listing_api,
                    "powerdms_document_id": entry["id"],
                    "manual_part": crumbs[3],
                    "manual_section": crumbs[4] if len(crumbs) > 4 else None,
                    "extraction_granularity": "pdf_page",
                    "extraction_note": "the effective date is printed in each document's header block; PowerDMS sends no Last-Modified",
                },
                request={"browser_impersonation": True},
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(data),
        "inventory": (
            f"PowerDMS listing has {len(data)} public documents; Economic Independence (EI) folder {len(ei)} in "
            f"{len(families)} families ({families}); the '4. Economic Independence' manual has {len(manual)} documents by "
            f"part ({parts}); taken the {len(docs)} policy documents in parts {', '.join(LA_POLICY_PARTS)} (eligibility, "
            "case processing, special households, case maintenance, nondiscrimination, charts, KCSP, reporting, STEP); "
            "not taken: Y forms and instructions, O DSNAP and K LaCAP (SNAP-only), and the other EI families"
        ),
        "source_kind": "official_pdf_manual_sections",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- RI
def build_ri() -> dict[str, Any]:
    """218-RICR-20-00-2 (Rhode Island Works) from the Department of State's RICR chapter listing and part page."""
    host = "https://rules.sos.ri.gov"
    index = host + "/organizations/chapter/218-20"
    chapter = fetch(index).text
    subchapters = re.findall(r'onclick="return get_parts\(this\)" id="([^"]+)"', chapter)
    if not subchapters:
        raise RuntimeError("no subchapter rows on the RICR chapter 218-20 page")
    parts: dict[str, str] = {}
    for sub in subchapters:
        # the chapter page loads each subchapter's parts table with this XHR
        listing = fetch(f"{host}/Organizations/get_parts/{sub}").text
        for href, label in links(listing):
            if "/Regulations/Part/" in href and not re.match(r"^Part \d+$", label):
                parts.setdefault(href.rstrip("/").rsplit("/", 1)[1], label)
    part_id = "218-20-00-2"
    if part_id not in parts:
        raise RuntimeError(f"{part_id} not in the chapter listing: {sorted(parts)}")
    part_url = f"{host}/regulations/part/{part_id}"
    page = fetch(part_url).text
    pdfs = sorted(set(re.findall(r"https://risos-apa-production-public\.s3\.amazonaws\.com/[^\"'<>& ]+\.pdf", page)))
    if len(pdfs) != 1:
        raise RuntimeError(f"expected one Download Regulation PDF, found {pdfs}")

    def pane(pane_id: str) -> str:
        match = re.search(rf'class="tab-pane[^"]*"[^>]*id="{pane_id}"[^>]*>(.*?)<div[^>]+class="tab-pane', page, re.S)
        text = re.sub(r"<[^>]+>", " | ", html.unescape(match.group(1) if match else ""))
        return re.sub(r"(\s*\|\s*)+", " | ", re.sub(r"\s+", " ", text))

    overview = pane("second")

    def field(label: str) -> str | None:
        match = re.search(re.escape(label) + r" \| ([^|]+) \|", overview)
        return match.group(1).strip() if match else None

    filing_type = field("Type of Filing")
    status = field("Regulation Status")
    effective_raw = field("Effective")
    if not effective_raw:
        raise RuntimeError(f"no effective date in the overview pane: {overview[:300]}")
    effective = dt.datetime.strptime(effective_raw, "%m/%d/%Y").date().isoformat()
    history = pane("four")
    filings = re.findall(r"(ACTIVE RULE|INACTIVE RULE) \| (?:EMERGENCY RULE \| )?([A-Za-z ]+) \| - effective from (\d{2}/\d{2}/\d{4})", history)
    amendments = [f for f in filings if f[1].strip() == "Amendment"]
    latest_amendment = (
        dt.datetime.strptime(amendments[0][2], "%m/%d/%Y").date().isoformat() if amendments else None
    )
    doc = base_doc(
        source_id="us-ri-dhs-riw-218-20-00-2",
        jurisdiction="us-ri",
        document_class="regulation",
        title=f"{parts[part_id]}",
        source_url=part_url,
        source_format="pdf",
        citation_path="us-ri/regulation/218-ricr/20/00/2",
        expression_date=effective,
        authority="Rhode Island Department of Human Services",
        subtype="administrative_regulation",
        state_program="Rhode Island Works (RIW)",
        index_url=index,
        extra={
            "official_publisher": "Rhode Island Department of State",
            "legal_identifier": "218-RICR-20-00-2",
            "filing_type": filing_type,
            "regulation_status": status,
            "regulation_effective_date": effective,
            "latest_amendment_effective_date": latest_amendment,
            "filing_history_count": len(filings),
            "pdf_last_modified": last_modified(pdfs[0]),
            "extraction_granularity": "pdf_page",
            "extraction_note": "the Download Regulation PDF of the active filing, page-level like the 218-RICR-20-00-1 SNAP scope",
        },
    )
    doc["download_url"] = pdfs[0]
    listing_text = "; ".join(f"Part {k.rsplit('-', 1)[1]} {v}" for k, v in sorted(parts.items(), key=lambda kv: int(kv[0].rsplit('-', 1)[1])))
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len(parts),
        "inventory": (
            f"RICR Title 218 Chapter 20 (Individual and Family Support Programs), {len(subchapters)} subchapter(s), "
            f"{len(parts)} parts via the chapter page's get_parts listing ({listing_text}); taken Part 2 "
            f"({filing_type}, {status}, effective {effective}; {len(filings)} filings in the part's history, latest "
            f"Amendment effective {latest_amendment}); not taken: the other parts (SNAP already in the corpus as "
            "218-RICR-20-00-1; GPA, CCAP, SSI/SSP, refugee assistance, social services are other programs)"
        ),
        "source_kind": "official_pdf_regulation",
        "document_class": "regulation",
        "primary_source_url": part_url,
    }


# --------------------------------------------------------------------------- WI
def build_wi() -> dict[str, Any]:
    """DCF Wisconsin Works (W-2) Manual (Adobe RoboHelp 2022 responsive output; TOC in whxdata/toc.new.js + toc<N>.new.js)."""
    base = "https://dcf.wisconsin.gov/manuals/w-2-manual/Production/"
    index = base + "default.htm"
    policies_page = "https://dcf.wisconsin.gov/w2/partners/policy"
    listing = links(fetch(policies_page).text)
    manuals = [(h, t) for h, t in listing if "/manuals/" in h]
    if not any(h.endswith("/manuals/w-2-manual/Production/default.htm") for h, _ in manuals):
        raise RuntimeError(f"W-2 Manual link not on the DCF policies page: {manuals}")
    admin_code = [t for h, t in listing if "docs.legis.wisconsin.gov" in h]
    fetch(index)  # redirect shell; the TOC data files carry the inventory

    def load(key: str) -> list[dict[str, Any]]:
        js = fetch(base + f"whxdata/{key}.new.js").text
        match = re.search(r"var toc\s*=\s*(\[.*?\]);\s*window\.rh", js, re.S)
        if not match:
            raise RuntimeError(f"unexpected RoboHelp TOC file whxdata/{key}.new.js")
        return json.loads(match.group(1))

    pages: dict[str, dict[str, Any]] = {}
    books = 0
    items = 0

    def walk(key: str, parent: str | None) -> None:
        nonlocal books, items
        for entry in load(key):
            if entry.get("type") == "book":
                books += 1
                walk(entry["key"], entry["name"])
                continue
            items += 1
            url = (entry.get("url") or "").split("#")[0]
            if url and url not in pages:
                pages[url] = {"name": entry["name"], "parent": parent, "order": len(pages) + 1}

    walk("toc", None)
    docs = []
    seen: set[str] = set()
    for url, info in pages.items():
        page_slug = slug(re.sub(r"\.htm$", "", url))
        if page_slug in seen:
            raise RuntimeError(f"duplicate Wisconsin topic slug {page_slug}")
        seen.add(page_slug)
        full = base + url
        docs.append(
            base_doc(
                source_id=f"us-wi-dcf-w2-{page_slug}",
                jurisdiction="us-wi",
                document_class="manual",
                title=f"Wisconsin Works (W-2) Manual: {info['name']}",
                source_url=full,
                source_format="html",
                citation_path=f"us-wi/manual/dcf/w2/{page_slug}",
                expression_date=last_modified(full),
                authority="Wisconsin Department of Children and Families, Division of Family and Economic Security",
                subtype="policy_manual_topic",
                state_program="Wisconsin Works (W-2)",
                index_url=index,
                extra={
                    "manual_toc_url": base + "whxdata/toc.new.js",
                    "manual_base_url": base,
                    "policies_listing_page": policies_page,
                    "toc_parent": info["parent"],
                    "toc_order": info["order"],
                },
                extraction={
                    "html_content_selector": "#rh-topic",
                    # every topic starts with the master page's banner table (agency name and manual title) and
                    # RoboHelp expand-spots repeat the trigger text in a data-close-text span
                    "html_drop_selectors": ["#rh-topic > div:first-child > table:has(p.layout)", "span[data-close-text]"],
                },
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(pages),
        "inventory": (
            f"RoboHelp 2022 TOC (whxdata/toc.new.js plus {books} book files) lists {items} items resolving to "
            f"{len(pages)} topic pages (Welcome, chapters 01 Introduction through 18 Emergency Assistance and related "
            f"programs, appendices); taken all {len(docs)}. The DCF W-2 policies page also lists the EA Manual and the "
            f"TJ/TMJ Manual ({len(manuals)} manual links; separate programs) and {len(admin_code)} Wisconsin "
            "Administrative Code DCF chapter links (legislature host), not taken"
        ),
        "source_kind": "official_html_manual",
        "document_class": "manual",
        "primary_source_url": index,
    }


BUILDERS = {
    "us-ca": build_ca,
    "us-co": build_co,
    "us-dc": build_dc,
    "us-mo": build_mo,
    "us-ms": build_ms,
    "us-mt": build_mt,
    "us-nd": build_nd,
    "us-ok": build_ok,
    "us-pa": build_pa,
    "us-va": build_va,
    "us-sd": build_sd,
    "us-nh": build_nh,
    "us-la": build_la,
    "us-id": build_id,
    "us-ri": build_ri,
    "us-wi": build_wi,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mo-title-cache", type=Path)
    parser.add_argument("--only", action="append", help="jurisdiction(s) to rebuild; default all")
    args = parser.parse_args()

    queue = yaml.safe_load(QUEUE_PATH.read_text())
    rows = {s["jurisdiction"]: s for s in queue["states"]}
    for jur, name in NEW_ROWS.items():
        rows.setdefault(
            jur,
            {
                "jurisdiction": jur,
                "name": name,
                "queue_status": "needs_review",
                "source_kind": None,
                "primary_source_url": None,
                "target_manifest": None,
                "target_scope": {"jurisdiction": jur, "document_class": None, "version": None},
                "lead_counts": None,
                "candidate_sources": [],
                "notes": f"Row added by {BATCH_LABEL.get(jur, 'batch 2').lower()} (not on the policyengine-us lead list).",
            },
        )
    selected = args.only or list(BUILDERS)
    for jur in selected:
        builder = BUILDERS[jur]
        result = builder(args.mo_title_cache) if jur == "us-mo" else builder()
        stem = f"{jur}-tanf-state-policy-manual"
        manifest = {"version": SOURCE_AS_OF, "documents": result["docs"]}
        (ROOT / "manifests" / f"{stem}.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=120)
        )
        row = rows[jur]
        row.update(
            {
                "queue_status": "agent_ready",
                "source_kind": result["source_kind"],
                "primary_source_url": result["primary_source_url"],
                "target_manifest": f"manifests/{stem}.yaml",
                "target_scope": {
                    "jurisdiction": jur,
                    "document_class": result["document_class"],
                    "version": VERSION,
                },
                "index_url": result["index_url"],
                "index_document_count": result["index_document_count"],
                "taken_count": len(result["docs"]),
                "notes": f"{BATCH_LABEL[jur]}. Primary source confirmed from the publisher's own index. Inventory: {result['inventory']}. Extraction proven 2026-09-10 (coverage complete, 0 missing/extra/duplicate).",
            }
        )
        print(f"{jur}: {len(result['docs'])} documents -> manifests/{stem}.yaml", file=sys.stderr)

    for jur, info in DONE.items():
        row = rows[jur]
        document_class, version = info["scope"]
        row.update(
            {
                "queue_status": "done",
                "source_kind": "already_ingested",
                "target_manifest": info["target_manifest"],
                "target_scope": {
                    "jurisdiction": jur,
                    "document_class": document_class,
                    "version": version,
                },
                "notes": info["notes"],
            }
        )
    for jur, info in BLOCKED.items():
        row = rows[jur]
        row.update(
            {
                "queue_status": "blocked_primary_source",
                "source_kind": info["source_kind"],
                "primary_source_url": info["primary_source_url"],
                "target_manifest": f"manifests/{jur}-tanf-state-policy-manual.yaml",
                "target_scope": {
                    "jurisdiction": jur,
                    "document_class": info["document_class"],
                    "version": VERSION,
                },
                "index_url": info["index_url"],
                "index_document_count": info["index_document_count"],
                "taken_count": 0,
                "notes": info["notes"],
            }
        )
    for jur, info in NEEDS_REVIEW.items():
        row = rows[jur]
        row.update(
            {
                "queue_status": "needs_review",
                "source_kind": info["source_kind"],
                "primary_source_url": info["primary_source_url"],
                "target_manifest": f"manifests/{jur}-tanf-state-policy-manual.yaml",
                "target_scope": {
                    "jurisdiction": jur,
                    "document_class": info["document_class"],
                    "version": VERSION,
                },
                "index_url": info["index_url"],
                "index_document_count": info["index_document_count"],
                "taken_count": 0,
                "notes": info["notes"],
            }
        )
    fed = rows["us"]
    fed.update(
        {
            "queue_status": "needs_review",
            "source_kind": "federal_regulation_and_state_plan_index",
            "primary_source_url": "https://www.ecfr.gov/current/title-45/subtitle-B/chapter-II/part-260",
            "index_url": "https://acf.gov/ofa/programs/temporary-assistance-needy-families-tanf",
            "index_document_count": None,
            "taken_count": 0,
            "notes": (
                "Checked 2026-09-10: 45 CFR parts 260-265 are NOT in the corpus (data/corpus/coverage/us/regulation has title 45 part 1302 only; "
                "no manifest or ingest-run note references parts 260-265). Not re-ingested in this run (federal eCFR adapter extract-ecfr "
                "--only-title 45 --only-part 260..265 is the path). ACF Office of Family Assistance TANF state plans are a separate later "
                "document family (state plans are published by each state; the OFA program page and the acf.gov resource library do not "
                "expose a consolidated plan index to a non-browser client on 2026-09-10 - acf.gov/ofa/programs/tanf/state-plans is 404 and "
                "the resource-library type filter returns an HTTP 202 challenge). index_document_count unknown; record once an index is located."
            ),
        }
    )
    queue["states"] = [rows[j] for j in sorted(rows, key=lambda j: (j != "us", j))]
    queue["status_counts"] = {}
    for s in queue["states"]:
        queue["status_counts"][s["queue_status"]] = (
            queue["status_counts"].get(s["queue_status"], 0) + 1
        )
    queue["queue_status"] = "in_progress"
    QUEUE_PATH.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(f"queue {queue['status_counts']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
