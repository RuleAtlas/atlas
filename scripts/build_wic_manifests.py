"""Build the WIC corpus manifests from the publishers' own index pages and update
the WIC agent queue.

Federal (USDA Food and Nutrition Service, renamed Food and Nutrition Administration
on 2026-06-01): the WIC policy-memorandum index is the FNA resource browser filtered
to WIC + Policy Memos, https://www.fna.usda.gov/resources?f[0]=program:32&f[1]=resource_type:160.
The www.fns.usda.gov / www.fna.usda.gov front door (Akamai) answers 403 "Access Denied"
to every client we have (plain, browser UA, curl_cffi impersonation, the Claude fetch
proxy, and a real browser on this machine), so the index and memo pages are read from
the publisher's own origin host fns-prod.azureedge.us (the same Drupal site; the
existing manifests/us-snap-guidance.yaml already downloads FNS files from that host).
Memo pages carry no text of their own: each embeds its PDF from the USDA guidance
portal (www.usda.gov/sites/default/files/guidance-documents/...), which serves PDFs
only to browser-impersonated clients; the extractor's existing
``request: browser_impersonation`` option handles that. The Income Eligibility
Guidelines notices are taken from govinfo.gov (Federal Register), which the FNA memo
#2026-5 / #2025-4 pages cite.

States (first batch: the ten largest by population): one manifest per state built from
the state WIC agency's own manual index page; one document per policy/chapter PDF.

TLS: www.cdph.ca.gov (California) presents a chain that certifi cannot complete
(issuer Sectigo Public Server Authentication CA OV R36) and www.dhs.state.il.us
(Illinois) omits its Entrust OV TLS Issuing RSA CA 2 intermediate. Both public
intermediates were fetched from the leaf certificates' AIA URLs into data/certs/ and
are appended to certifi in data/certs/wic-state-ca-bundle.pem. Run extraction with
REQUESTS_CA_BUNDLE pointing at that bundle. No verification is disabled.

    uv run python scripts/build_wic_manifests.py
"""
from __future__ import annotations

import datetime as dt
import re
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import certifi
import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE_AS_OF = dt.date.today().isoformat()
FEDERAL_VERSION = "2026-09-10-wic-fns-guidance"
STATE_VERSION = "2026-09-10-wic-state-policy-manual"
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
FNA_ORIGIN = "https://fns-prod.azureedge.us"
FNA_CANONICAL = "https://www.fna.usda.gov"
FNA_MEMO_INDEX = "/resources?f%5B0%5D=program%3A32&f%5B1%5D=resource_type%3A160"
FNA_GUIDANCE_INDEX = "/resources?f%5B0%5D=program%3A32&f%5B1%5D=resource_type%3A401"
FNA_FR_INDEX = "/resources?f%5B0%5D=program%3A32&f%5B1%5D=resource_type%3A16"
IMPERSONATE = {"browser_impersonation": True, "browser_impersonation_direct": True}
# wic.health.pa.gov stalls urllib3 keep-alive downloads mid-body; the extractor's curl
# range backend exists for exactly that case.
CURL_RANGES = {"range_fetch": True, "range_backend": "curl"}
SINGLE_BLOCK = {"segmentation": "single_block"}

CERTS = ROOT / "data" / "certs"
INTERMEDIATES = (
    CERTS / "sectigo-public-server-authentication-ca-ov-r36.pem",
    CERTS / "entrust-ov-tls-issuing-rsa-ca-2.pem",
)


def ca_bundle() -> Path:
    out = CERTS / "wic-state-ca-bundle.pem"
    out.write_text(
        Path(certifi.where()).read_text()
        + "".join("\n" + p.read_text() for p in INTERMEDIATES)
    )
    return out


def get(url: str, *, verify: str | bool = True, impersonate: bool = False) -> bytes:
    if impersonate:
        from curl_cffi import requests as curl_requests

        resp = curl_requests.get(url, headers=UA, timeout=90, impersonate="chrome120")
        resp.raise_for_status()
        return resp.content
    for attempt in range(1, 4):  # wic.health.pa.gov intermittently stalls mid-response
        try:
            # keep-alive responses from wic.health.pa.gov stall mid-body (Connection: close does not);
            # compressed responses from fns-prod.azureedge.us are cached without the query string,
            # so the facet filter is only honored for identity encoding.
            headers = {**UA, "Connection": "close", "Accept-Encoding": "identity"}
            resp = requests.get(url, headers=headers, timeout=90, verify=verify)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 * attempt)
    raise RuntimeError(url)


def soup_of(content: bytes) -> BeautifulSoup:
    return BeautifulSoup(content, "html.parser")


def write_manifest(stem: str, documents: list[dict], version: str) -> str:
    path = ROOT / "manifests" / f"{stem}.yaml"
    path.write_text(
        yaml.safe_dump({"version": version, "documents": documents}, sort_keys=False, allow_unicode=True, width=120)
    )
    return f"manifests/{stem}.yaml"


# --------------------------------------------------------------------------- federal

# FY 2025 and FY 2026 WIC policy memoranda confirmed on the FNA index / memo pages.
# The Azure origin host ignores the listing's ``page`` parameter, so only the first
# listing page (the ten newest resources, which cover calendar 2025-2026 exactly per the
# index's own year facet) is enumerable; #2025-1 and #2025-2 (dated December 2024) were
# located by their FNA page slugs and confirmed on those pages. Memo numbers and dates
# were read from each PDF's header.
FEDERAL_MEMOS = [
    # slug, memo number, memo date, title
    ("wic/clarification-corporate-changes-ownership", "2025-1", "2024-12-06",
     "WIC Policy Memorandum #2025-1: Clarification on Corporate Changes of Ownership"),
    ("wic/cancellation-exit-counseling-brochure", "2025-2", "2024-12-20",
     "WIC Policy Memorandum #2025-2: Cancellation of WIC Policy Memorandum #1994-9 WIC Exit Counseling Brochure"),
    ("wic/banked-human-breastmilk", "2025-3", "2025-01-10",
     "WIC Policy Memorandum #2025-3: Policy Memorandum Revision: Use of Banked Human Breast Milk in WIC"),
    ("wic/income-eligibility-guidelines-2025-26", "2025-4", "2025-03-27",
     "WIC Policy Memorandum #2025-4: Publication of the 2025-2026 WIC Income Eligibility Guidelines"),
    ("wic/revised-food-packages-flexibilities", "2025-5", "2025-08-19",
     "WIC Policy Memorandum #2025-5: Implementing Revisions to the WIC Food Packages: Flexibilities to Support Healthy Choices, Healthy Outcomes, and Healthy Families"),
    ("wic/agency/increase-mma-fluidmilk", "2026-1", "2025-12-05",
     "WIC Policy Memorandum #2026-1: Implementation of P.L. 119-37, Temporary Increase to the Maximum Monthly Allowance of Fluid Milk"),
    ("wic/agency/cvvb-fy26", "2026-2", "2025-12-10",
     "WIC Policy Memorandum #2026-2: Fiscal Year 2026 Cash-Value Voucher/Benefit Amounts"),
    ("wic/agency/dgas-eat-real-food", "2026-4", "2026-03-30",
     "WIC Policy Memorandum #2026-4: Dietary Guidelines for Americans, 2025-2030 - Eat Real Food"),
    ("wic/agency/ieg-2026-27", "2026-5", "2026-04-29",
     "WIC Policy Memorandum #2026-5: Publication of 2026-2027 WIC Income Eligibility Guidelines"),
]

FEDERAL_IEG_NOTICES = [
    # period, FR citation, document number, publication date, effective date
    ("2026-2027", "91 FR 23050", "2026-08323", "2026-04-29", "2026-07-01"),
    ("2025-2026", "90 FR 11598", "2025-03576", "2025-03-10", "2025-07-01"),
]


def memo_pdf_url(slug: str) -> str:
    page = soup_of(get(f"{FNA_ORIGIN}/{slug}"))
    frames = [f["src"] for f in page.find_all("iframe", src=True) if "guidance-documents" in f["src"]]
    if len(frames) != 1:
        raise RuntimeError(f"memo page {slug} does not embed exactly one guidance-portal PDF: {frames}")
    return frames[0]


def federal_index_inventory() -> dict:
    """Return the index's own counts (rows on the first listing page and year facets)."""
    page = soup_of(get(FNA_ORIGIN + FNA_MEMO_INDEX))
    rows = []
    active = [a.get_text(" ", strip=True) for a in page.find_all("a") if a.get_text(" ", strip=True).startswith("(-)")]
    if not any("WIC" in t for t in active) or not any("Policy Memos" in t for t in active):
        raise RuntimeError(f"FNA listing did not apply the WIC / Policy Memos facets: {active}")
    for row in page.select(".views-row"):
        a = row.find("a", href=True)
        d = row.select_one(".listing__date")
        rows.append({"date": d.get_text(strip=True) if d else None, "title": a.get_text(" ", strip=True), "href": a["href"]})
    facets = {}
    for a in page.find_all("a", href=True):
        m = re.match(r"^(\d{4}) \((\d+)\)$", a.get_text(" ", strip=True))
        if m:
            facets[m.group(1)] = int(m.group(2))
        m = re.match(r"^\(-\) Policy Memos \((\d+)\)$", a.get_text(" ", strip=True))
        if m:
            facets["total"] = int(m.group(1))
    return {"first_page_rows": rows, "year_facets": facets}


def build_federal() -> tuple[str, int, dict]:
    inventory = federal_index_inventory()
    docs = []
    for period, citation, number, published, effective in FEDERAL_IEG_NOTICES:
        docs.append({
            "source_id": f"us-fns-wic-income-eligibility-guidelines-{period}",
            "jurisdiction": "us",
            "document_class": "guidance",
            "title": f"WIC: {period.replace('-', '/')} Income Eligibility Guidelines ({citation})",
            "source_url": f"https://www.govinfo.gov/content/pkg/FR-{published}/html/{number}.htm",
            "source_format": "html",
            "source_as_of": SOURCE_AS_OF,
            "expression_date": published,
            "citation_path": f"us/guidance/fns/wic/income-eligibility-guidelines/{period}",
            "metadata": {
                "primary_source": True,
                "source_authority": "USDA Food and Nutrition Service (Food and Nutrition Administration since 2026-06-01) via U.S. Government Publishing Office",
                "document_subtype": "federal_register_notice",
                "program": "WIC",
                "federal_register_citation": citation,
                "federal_register_document_number": number,
                "federal_register_publication_date": published,
                "federal_register_pdf_url": f"https://www.govinfo.gov/content/pkg/FR-{published}/pdf/{number}.pdf",
                "effective_start": effective,
                "effective_end": f"{int(effective[:4]) + 1}-06-30",
                "source_discovery_group": "us/guidance/fns/wic",
                "discovered_via": "manual-review:wic-agent-queue; FNA WIC agency page 'View guidelines' link and policy memo transmitting the notice",
            },
        })
    for slug, number, memo_date, title in FEDERAL_MEMOS:
        pdf = memo_pdf_url(slug)
        fy = number.split("-")[0]
        docs.append({
            "source_id": f"us-fns-wic-policy-memo-{number}",
            "jurisdiction": "us",
            "document_class": "guidance",
            "title": title,
            "source_url": f"{FNA_CANONICAL}/{slug}",
            "download_url": pdf,
            "source_format": "pdf",
            "source_as_of": SOURCE_AS_OF,
            "expression_date": memo_date,
            "citation_path": f"us/guidance/fns/wic/policy-memo/{number}",
            "request": dict(IMPERSONATE),
            "extraction": dict(SINGLE_BLOCK),
            "metadata": {
                "primary_source": True,
                "source_authority": "USDA Food and Nutrition Service (Food and Nutrition Administration since 2026-06-01)",
                "document_subtype": "policy_memorandum",
                "program": "WIC",
                "memo_number": number,
                "memo_date": memo_date,
                "fiscal_year": fy,
                "index_url": FNA_CANONICAL + FNA_MEMO_INDEX.replace("%5B", "[").replace("%5D", "]").replace("%3A", ":"),
                "source_discovery_group": "us/guidance/fns/wic",
                "discovered_via": "manual-review:wic-agent-queue; FNA resource browser WIC/Policy Memos",
                "access_note": (
                    "www.fna.usda.gov / www.fns.usda.gov answer HTTP 403 to every client; the memo page was read from the "
                    "publisher's origin host fns-prod.azureedge.us and carries only an embedded PDF from the USDA guidance "
                    "portal, which is downloaded with browser impersonation."
                ),
            },
        })
    return write_manifest("us-wic-fns-guidance", docs, FEDERAL_VERSION), len(docs), inventory


# --------------------------------------------------------------------------- states

def state_doc(jur: str, agency: str, label: str, title: str, url: str, *, authority: str, index_url: str,
              manual: str, request: dict | None = None, extra: dict | None = None) -> dict:
    doc = {
        "source_id": f"{jur}-wic-manual-{label.lower()}",
        "jurisdiction": jur,
        "document_class": "manual",
        "title": title,
        "source_url": url,
        "source_format": "pdf",
        "source_as_of": SOURCE_AS_OF,
        "citation_path": f"{jur}/manual/{agency}/wic/{label.lower()}",
        "extraction": dict(SINGLE_BLOCK),
        "metadata": {
            "primary_source": True,
            "source_authority": authority,
            "document_subtype": "state_policy_manual_section",
            "program": "WIC",
            "manual": manual,
            "section_label": label,
            "index_url": index_url,
            "source_discovery_group": f"{jur}/manual/wic",
            "discovered_via": "manual-review:wic-agent-queue; state WIC agency manual index page",
            **(extra or {}),
        },
    }
    if request:
        doc["request"] = dict(request)
    return doc


def build_ca(bundle: Path) -> tuple[str, int, dict]:
    index = "https://www.cdph.ca.gov/Programs/CFH/DWICSN/Pages/LocalAgencies/PoliciesandPolicyResources/WPPM.aspx"
    page = soup_of(get(index, verify=str(bundle)))
    docs, seen, families = [], {}, {"wppm_policy_pdf": 0, "other_link": 0}
    for a in page.find_all("a", href=True):
        text = a.get_text(" ", strip=True).replace("​", "")
        m = re.match(r"^\s*(\d{3,4}-\d{2,4})\s+(.*?)\s*(\(PDF\))?\s*$", text)
        if not (m and "/WPPM/" in a["href"]):
            if a["href"].lower().endswith(".pdf"):
                families["other_link"] += 1
            continue
        families["wppm_policy_pdf"] += 1
        label, title = m.group(1), m.group(2)
        if title.lower().endswith("- spanish"):
            label = f"{label}-es"
        if label in seen:  # the index links two files under one policy number
            seen[label] += 1
            label = f"{label}-{seen[label]}"
        else:
            seen[label] = 1
        docs.append(state_doc(
            "us-ca", "cdph", label, f"California WIC Policy and Procedures Manual WPPM #{m.group(1)}: {title}",
            urljoin(index, a["href"]), authority="California Department of Public Health, WIC Division",
            index_url=index, manual="WIC Policy and Procedures Manual (WPPM)",
            extra={"tls_note": "extraction uses REQUESTS_CA_BUNDLE = certifi + data/certs/sectigo-public-server-authentication-ca-ov-r36.pem"},
        ))
    if len(docs) < 100:
        raise RuntimeError(f"CA index yielded only {len(docs)} policies")
    return write_manifest("us-ca-wic-policy-manual", docs, STATE_VERSION), len(docs), {"index_url": index, **families}


def build_tx() -> tuple[str, int, dict]:
    index = "https://www.hhs.texas.gov/providers/wic-providers/wic-policy-procedures-manual"
    page = soup_of(get(index, impersonate=True))
    main = page.select_one("main") or page
    docs, families = [], {"policy_pdf": 0, "policy_pdf_working_draft": 0, "complete_manual_pdf": 0}
    for a in main.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if not a["href"].lower().endswith(".pdf"):
            continue
        if "policy-manual.pdf" in a["href"]:
            families["complete_manual_pdf"] += 1
            continue
        m = re.match(r"^([A-Z]{2,3}):(\d{2}\.\d)\s*(\(T\))?\s*(.*)$", text)
        if not m:
            continue
        draft = bool(m.group(3))
        families["policy_pdf_working_draft" if draft else "policy_pdf"] += 1
        label = f"{m.group(1)}-{m.group(2)}" + ("t" if draft else "")
        docs.append(state_doc(
            "us-tx", "hhsc", label, f"Texas WIC Policy and Procedures Manual {m.group(1)}:{m.group(2)}{' (T)' if draft else ''} {m.group(4)}",
            urljoin(index, a["href"]), authority="Texas Health and Human Services Commission, WIC",
            index_url=index, manual="Texas WIC Policy and Procedures Manual", request=IMPERSONATE,
            extra={"working_draft": draft, "access_note": "hhs.texas.gov answers 403 to non-browser clients; fetched with browser impersonation"},
        ))
    if len(docs) < 100:
        raise RuntimeError(f"TX index yielded only {len(docs)} policies")
    return write_manifest("us-tx-wic-policy-manual", docs, STATE_VERSION), len(docs), {"index_url": index, **families}


def build_ga() -> tuple[str, int, dict]:
    index = "https://dph.georgia.gov/WIC/wic-policy-and-procedures-manual"
    page = soup_of(get(index))
    main = page.select_one("main") or page
    docs, families = [], {"policy_pdf": 0, "section_outline_pdf": 0, "combined_section_pdf": 0}
    for a in main.find_all("a", href=True):
        text = a.get_text(" ", strip=True).replace("\xa0", " ")
        m = re.match(r"^([A-Z]{2,3})-\s?(\d{3,4}\.\d{2})\s*(.*)$", text)
        if not m:
            if re.match(r"^[A-Z]{2,3}-\s?Outline$", text):
                families["section_outline_pdf"] += 1
            elif "Policies Combined" in text:
                families["combined_section_pdf"] += 1
            continue
        label = f"{m.group(1)}-{m.group(2)}"
        # eleven index entries point at document pages or media ids the publisher no longer serves
        # (HTTP 404, one 403); probe each link and record those instead of taking them
        probe = requests.get(urljoin(index, a["href"]), headers=UA, timeout=60, stream=True)
        head = next(probe.iter_content(8), b"")
        probe.close()
        if probe.status_code != 200 or head[:4] != b"%PDF":
            families[f"policy_link_{probe.status_code}_on_publisher"] = families.get(
                f"policy_link_{probe.status_code}_on_publisher", []
            ) + [label]
            continue
        families["policy_pdf"] += 1
        docs.append(state_doc(
            "us-ga", "dph", label, f"Georgia WIC Policy and Procedures Manual {label}: {m.group(3)}".rstrip(": "),
            urljoin(index, a["href"]), authority="Georgia Department of Public Health, WIC Program",
            index_url=index, manual="Georgia WIC Policy and Procedures Manual",
        ))
    if len(docs) < 100:
        raise RuntimeError(f"GA index yielded only {len(docs)} policies")
    return write_manifest("us-ga-wic-policy-manual", docs, STATE_VERSION), len(docs), {"index_url": index, **families}


def build_mi() -> tuple[str, int, dict]:
    index = "https://www.michigan.gov/mdhhs/assistance-programs/wic/wic-staff/wicpolicymanual/mi-wic-policy-manual-table-of-contents"
    page = soup_of(get(index, impersonate=True))
    main = page.select_one("main") or page
    docs, families = [], {"numbered_policy_or_exhibit_pdf": 0, "unnumbered_attachment_pdf": 0, "policy_index_pdf": 0}
    for li in main.find_all("li"):
        a = li.find("a", href=re.compile(r"\.pdf", re.I))
        if not a or a.find_parent("li") is not li:
            continue
        own = li.get_text(" ", strip=True)
        text = a.get_text(" ", strip=True)
        if "Policy Index" in text:
            families["policy_index_pdf"] += 1
            continue
        m = re.match(r"^(\d+\.\d+[A-Z]?)\b", own)
        if not m:
            families["unnumbered_attachment_pdf"] += 1
            continue
        families["numbered_policy_or_exhibit_pdf"] += 1
        label = m.group(1)
        docs.append(state_doc(
            "us-mi", "mdhhs", label, f"MI-WIC Policy Manual {label}: {text}",
            urljoin(index, a["href"]), authority="Michigan Department of Health and Human Services, WIC Division",
            index_url=index, manual="MI-WIC Policy Manual", request=IMPERSONATE,
            extra={"access_note": "michigan.gov answers 403 to non-browser clients; fetched with browser impersonation"},
        ))
    if len(docs) < 80:
        raise RuntimeError(f"MI index yielded only {len(docs)} policies")
    return write_manifest("us-mi-wic-policy-manual", docs, STATE_VERSION), len(docs), {"index_url": index, **families}


def build_pa() -> tuple[str, int, dict]:
    index = "https://wic.health.pa.gov/pawic/PoliciesAndProcedures.aspx"
    page = soup_of(get(index))
    docs, families = [], {"policy_pdf": 0, "policy_index_pdf": 0, "other_pdf": 0}
    for a in page.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if not a["href"].lower().endswith(".pdf"):
            continue
        if "PoliciesAndProcedures/" not in a["href"]:
            families["other_pdf"] += 1
            continue
        m = re.match(r"^(\d\.\d\d)\s+(.*)$", text)
        if not m:
            families["policy_index_pdf"] += 1
            continue
        families["policy_pdf"] += 1
        docs.append(state_doc(
            "us-pa", "doh", m.group(1), f"Pennsylvania WIC Policy and Procedure Manual {m.group(1)}: {m.group(2)}",
            urljoin(index, quote(a["href"], safe="/:%")),  # hrefs contain literal spaces; curl rejects them
            authority="Pennsylvania Department of Health, Bureau of Women, Infants and Children",
            index_url=index, manual="Pennsylvania WIC Policy and Procedure Manual", request=CURL_RANGES,
            extra={"access_note": "wic.health.pa.gov stalls urllib3 keep-alive downloads mid-body; fetched with the curl range backend"},
        ))
    if len(docs) < 40:
        raise RuntimeError(f"PA index yielded only {len(docs)} policies")
    return write_manifest("us-pa-wic-policy-manual", docs, STATE_VERSION), len(docs), {"index_url": index, **families}


def build_nc() -> tuple[str, int, dict]:
    index = "https://www.ncdhhs.gov/divisions/child-and-family-well-being/community-nutrition-services-section/wic/staff/wic-local-agency-resources"
    page = soup_of(get(index))
    docs, families = [], {"chapter_pdf": 0, "complete_manual_pdf": 0}
    for a in page.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if "complete-nc-wic-program-manual" in a["href"]:
            families["complete_manual_pdf"] += 1
            continue
        m = re.match(r"^Chapter (\d+[A-Z]?):\s*(.*)$", text)
        if not m:
            continue
        families["chapter_pdf"] += 1
        label = f"chapter-{m.group(1).lower()}"
        docs.append(state_doc(
            "us-nc", "ncdhhs", label, f"North Carolina WIC Program Manual Chapter {m.group(1)}: {m.group(2)}",
            urljoin(index, a["href"]), authority="North Carolina Department of Health and Human Services, Community Nutrition Services Section",
            index_url=index, manual="North Carolina WIC Program Manual",
        ))
    if len(docs) < 20:
        raise RuntimeError(f"NC index yielded only {len(docs)} chapters")
    return write_manifest("us-nc-wic-policy-manual", docs, STATE_VERSION), len(docs), {"index_url": index, **families}


BLOCKED = {
    "us-ny": (
        "New York State Department of Health",
        "https://www.health.ny.gov/prevention/nutrition/wic/",
        "The NYS WIC Program Manual is not published on health.ny.gov: the WIC pages link no manual, the only copies on "
        "the host are inactive procurement attachments (funding/ifb/inactive/16429/wic_program_manual_*.pdf), and current "
        "copies exist only as reposts on non-government sites (nwica.org, thewichub.org), which the queue forbids.",
    ),
    "us-fl": (
        "Florida Department of Health",
        "https://www.floridahealth.gov/individual-family-health/womens-health/wic/",
        "The Florida WIC Procedure Manual (DHM 150-24) is not published on floridahealth.gov: the WIC and health-care-provider "
        "pages link only forms, the vendor handbook and outreach material; the manual is referenced by number in county "
        "documents but no state index or PDF is available.",
    ),
    "us-il": (
        "Illinois Department of Human Services",
        "https://www.dhs.state.il.us/page.aspx?item=36418",
        "The IDHS 'WIC Policy and Procedure Manual' page (item=36418) now redirects to 'Page Not Found' (item=27893); the WIC "
        "program page (item=31907) links no manual. One chapter PDF (onenetlibrary/27896/.../wic/ppm/3_certificationstandards.pdf, "
        "issue date May 2006) is still served, but there is no publisher index from which the current manual can be confirmed.",
    ),
    "us-oh": (
        "Ohio Department of Health",
        "https://odh.ohio.gov/know-our-programs/Women-Infants-Children/Local-Staff",
        "The Ohio WIC Policy and Procedure Manual is not published on odh.ohio.gov: the Local Staff and program pages link no "
        "manual; the only public copy is a July 2015 repost by a county health department, which is neither current nor the publisher.",
    ),
}

STATE_NAMES = {"us-ca": "California", "us-tx": "Texas", "us-fl": "Florida", "us-ny": "New York", "us-pa": "Pennsylvania",
               "us-il": "Illinois", "us-oh": "Ohio", "us-ga": "Georgia", "us-nc": "North Carolina", "us-mi": "Michigan"}


def main() -> int:
    bundle = ca_bundle()
    queue_path = ROOT / "manifests" / "wic-agent-queue.yaml"
    queue = yaml.safe_load(queue_path.read_text())
    rows = {s["jurisdiction"]: s for s in queue["states"]}

    manifest, count, inventory = build_federal()
    fed = rows["us"]
    fed.update({
        "queue_status": "agent_ready",
        "source_kind": "official_agency_guidance_pdf_and_federal_register_html",
        "primary_source_url": FNA_CANONICAL + "/wic/agency",
        "target_manifest": manifest,
        "target_scope": {"jurisdiction": "us", "document_class": "guidance", "version": FEDERAL_VERSION},
        "index_url": FNA_CANONICAL + "/resources?f[0]=program:32&f[1]=resource_type:160",
        "index_document_count": inventory["year_facets"].get("total"),
        "taken_count": count,
        "index_inventory": inventory,
        "notes": (
            "FNS became the Food and Nutrition Administration on 2026-06-01; www.fns.usda.gov and www.fna.usda.gov answer 403 "
            "to every client, so the index and memo pages were read from the publisher's origin host fns-prod.azureedge.us and "
            "the memo PDFs from the USDA guidance portal with browser impersonation. Taken: FY2025 memos #2025-1..#2025-5, "
            "FY2026 memos #2026-1, #2026-2, #2026-4, #2026-5 (no #2026-3 is listed), and the 2025-2026 and 2026-2027 Income "
            "Eligibility Guidelines Federal Register notices from govinfo. 7 CFR 246 is already in the corpus "
            "(data/corpus/provisions/us/regulation/2026-07-13-recovery-r2026-07-17-dedup.jsonl, 268 provisions under "
            "us/regulation/7/246) and was not re-ingested."
        ),
    })

    results = {}
    for jur, builder in (("us-ca", lambda: build_ca(bundle)), ("us-tx", build_tx), ("us-ga", build_ga),
                         ("us-mi", build_mi), ("us-pa", build_pa), ("us-nc", build_nc)):
        manifest, count, inventory = builder()
        results[jur] = (manifest, count, inventory)
        agency = manifest.split("-")[1]
        row = rows.get(jur) or {"jurisdiction": jur, "name": STATE_NAMES[jur], "lead_counts": {}, "candidate_sources": []}
        row.update({
            "name": STATE_NAMES[jur],
            "queue_status": "agent_ready",
            "source_kind": "official_state_agency_manual_pdf_per_section",
            "primary_source_url": inventory["index_url"],
            "target_manifest": manifest,
            "target_scope": {"jurisdiction": jur, "document_class": "manual", "version": STATE_VERSION},
            "index_url": inventory["index_url"],
            "index_document_count": sum(
                len(v) if isinstance(v, list) else v for k, v in inventory.items() if k != "index_url"
            ),
            "taken_count": count,
            "index_inventory": {k: v for k, v in inventory.items() if k != "index_url"},
            "notes": (
                "Current WIC policy manual confirmed on the state WIC agency's own index page; one document per policy/chapter "
                "PDF listed there, single_block extraction. Selected in the first batch as one of the ten largest states by population."
            ),
        })
        rows[jur] = row
        print(f"{jur}: {count} documents -> {manifest}; index {inventory}")

    for jur, (agency_name, index_url, failure) in BLOCKED.items():
        row = rows.get(jur) or {"jurisdiction": jur, "name": STATE_NAMES[jur], "lead_counts": {}, "candidate_sources": []}
        row.update({
            "name": STATE_NAMES[jur],
            "queue_status": "blocked_primary_source",
            "source_kind": "official_state_agency_manual_not_published",
            "primary_source_url": None,
            "target_manifest": f"manifests/{jur}-wic-policy-manual.yaml",
            "target_scope": {"jurisdiction": jur, "document_class": "manual", "version": None},
            "index_url": index_url,
            "index_document_count": 0,
            "taken_count": 0,
            "notes": f"{agency_name}: {failure} Selected in the first batch as one of the ten largest states by population.",
        })
        rows[jur] = row

    queue["states"] = [rows[j] for j in sorted(rows, key=lambda j: (j != "us", j))]
    queue["status_counts"] = {}
    for s in queue["states"]:
        queue["status_counts"][s["queue_status"]] = queue["status_counts"].get(s["queue_status"], 0) + 1
    queue["queue_status"] = "in_progress"
    queue_path.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(f"federal: {rows['us']['taken_count']} documents; queue {queue['status_counts']}; ca bundle {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
