"""Build one official-document manifest per state for the state Medicaid eligibility
policy manuals (batch 1 of `manifests/medicaid-agent-queue.yaml`) and update the queue.

Every document is confirmed from the state Medicaid agency's own index page, fetched
live here so the manifest reflects what the publisher lists today. The lead-list
PolicyEngine citations in the queue are discovery only and are never used as sources.

Batch 1 = the two queued state rows (AR, VA) + the eight largest states by population
(CA, TX, FL, NY, PA, IL, OH, GA). Where a state's Medicaid eligibility chapters are
already in the corpus under a combined manual (FL, IL) the row is marked `done` with a
pointer and the next largest state is pulled (NC for IL; MI for FL, which is itself
already covered by the Bridges manual, so NJ is pulled). CA and OH block retrieval and
are recorded as `blocked_primary_source` with the exact failure.

    uv run python scripts/build_medicaid_state_eligibility_manual_manifests.py            # both batches
    uv run python scripts/build_medicaid_state_eligibility_manual_manifests.py --batch 2  # batch 2 only

Batch 2 = the next ten states by population (WA, AZ, TN, MA, IN, MD, MO, WI, CO, MN). None
was already covered by a combined manual in the corpus, so no replacement state was pulled.
AZ and TN block retrieval and are recorded as `blocked_primary_source` with the exact
failure; CA and OH were retried once each and their row notes record the outcome.
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
from urllib.parse import urljoin

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "manifests" / "medicaid-agent-queue.yaml"
VERSION = "2026-09-10-medicaid-state-eligibility-manual"
SOURCE_AS_OF = dt.date.today().isoformat()
EXPRESSION_DATE = SOURCE_AS_OF  # current-effective manual trees; see run note
UA = "Axiom/1.0 (Legal Archive; contact@axiom-foundation.org) https://github.com/TheAxiomFoundation/axiom-corpus"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DISCOVERED_VIA = "manual-review:medicaid-agent-queue batch 1; publisher index {index}"

_LINK_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)


def fetch(url: str, *, browser: bool = False) -> str:
    """GET with TLS verification on; retry only transient connection errors (e.g. a resolver blip)."""
    for attempt in range(4):
        try:
            resp = requests.get(url, headers={"User-Agent": BROWSER_UA if browser else UA}, timeout=90)
            resp.raise_for_status()
            return resp.text
        except requests.ConnectionError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def links(page: str, base: str) -> list[tuple[str, str]]:
    """Return (absolute href, text) pairs in document order, de-duplicated."""
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for href, text in _LINK_RE.findall(page):
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(text))).strip()
        href = html.unescape(href).strip()
        absolute = urljoin(base, href).split("#", 1)[0]
        if (absolute, text) in seen:
            continue
        seen.add((absolute, text))
        out.append((absolute, text))
    return out


def slug(value: str, limit: int = 80) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:limit].strip("-")


def document(
    jur: str,
    *,
    label: str,
    title: str,
    url: str,
    fmt: str,
    authority: str,
    manual: str,
    index_url: str,
    subtype: str,
    extraction: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "source_id": f"{jur}-medicaid-{label.replace('/', '-')}",
        "jurisdiction": jur,
        "document_class": "manual",
        "title": title,
        "source_url": url,
        "source_format": fmt,
        "source_as_of": SOURCE_AS_OF,
        "expression_date": EXPRESSION_DATE,
        "citation_path": f"{jur}/manual/{extra.pop('agency') if extra and 'agency' in extra else 'x'}/medicaid/{label}",
    }
    if request:
        doc["request"] = request
    if extraction:
        doc["extraction"] = extraction
    doc["metadata"] = {
        "primary_source": True,
        "source_authority": authority,
        "document_subtype": subtype,
        "program": "MEDICAID",
        "manual": manual,
        "manual_index_url": index_url,
        "source_discovery_group": f"{jur}/manual/medicaid",
        "discovered_via": DISCOVERED_VIA.format(index=index_url),
        **(extra or {}),
    }
    return doc


# --------------------------------------------------------------------------- states


def build_va() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://www.dmas.virginia.gov/for-applicants/eligibility-guidance/eligibility-manual/"
    page = fetch(index)
    docs = []
    families: dict[str, dict[str, int]] = {"manual_chapter_pdf": {"found": 0, "taken": 0}, "other_pdf": {"found": 0, "taken": 0}}
    for href, text in links(page, index):
        if not href.lower().endswith(".pdf"):
            continue
        m = re.match(r"^Chapter (M\d{2}) - (.+)$", text)
        if m:
            code, heading = m.group(1).lower(), m.group(2)
            label = code if code != "m00" else f"{code}-{slug(heading)}"
            title = f"Virginia Medical Assistance Eligibility Manual: Chapter {m.group(1)} {heading}"
        elif text == "Table of Contents":
            label, title = "m000-table-of-contents", "Virginia Medical Assistance Eligibility Manual: Table of Contents"
        else:
            families["other_pdf"]["found"] += 1
            continue
        families["manual_chapter_pdf"]["found"] += 1
        families["manual_chapter_pdf"]["taken"] += 1
        docs.append(document("us-va", label=label, title=title, url=href, fmt="pdf",
                             authority="Virginia Department of Medical Assistance Services",
                             manual="Virginia Medical Assistance Eligibility Manual", index_url=index,
                             subtype="eligibility_manual_chapter_pdf", extraction={"ocr": True},
                             extra={"agency": "dmas", "extraction_granularity": "pdf_page"}))
    return docs, {"index_url": index, "families": families}


def build_ny() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://www.health.ny.gov/health_care/medicaid/reference/mrg/"
    page = fetch(index, browser=True)
    chapters = {
        "mrg-intro.pdf": ("introduction", "Introduction to the Medicaid Reference Guide and Instructions for Use"),
        "glossary.pdf": ("glossary", "Glossary"),
        "category.pdf": ("categorical-factors", "Categorical Factors"),
        "income.pdf": ("income", "Income"),
        "resindex.pdf": ("resources", "Resources"),
        "other-eligibility-requirements.pdf": ("other-eligibility-requirements", "Other Eligibility Requirements"),
        "reference.pdf": ("reference", "Reference"),
        "masterindex.pdf": ("master-index", "Cumulative/Master Index"),
    }
    families = {"manual_chapter_pdf": {"found": 0, "taken": 0}, "full_manual_pdf": {"found": 0, "taken": 0},
                "update_archive_pdf_or_html": {"found": 0, "taken": 0}}
    docs = []
    for href, _text in links(page, index):
        if "/reference/mrg/" not in href:
            continue
        name = href.rsplit("/", 1)[-1]
        if name in chapters:
            label, heading = chapters[name]
            families["manual_chapter_pdf"]["found"] += 1
            families["manual_chapter_pdf"]["taken"] += 1
            docs.append(document("us-ny", label=label, title=f"New York Medicaid Reference Guide: {heading}", url=href, fmt="pdf",
                                 authority="New York State Department of Health", manual="New York Medicaid Reference Guide (MRG)",
                                 index_url=index, subtype="eligibility_manual_chapter_pdf",
                                 request={"browser_impersonation": True}, extraction={"ocr": True},
                                 extra={"agency": "doh", "extraction_granularity": "pdf_page",
                                        "request_note": "health.ny.gov returns 403 to the Axiom user agent; browser_impersonation is the existing manifest option for that"}))
        elif name == "mrg.pdf":
            families["full_manual_pdf"]["found"] += 1
        elif re.search(r"\d{4}", name):
            families["update_archive_pdf_or_html"]["found"] += 1
    return docs, {"index_url": index, "families": families}


def build_nc() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = "https://policies.ncdhhs.gov/divisional-a-m/health-benefits-nc-medicaid/"
    pages = {
        "abd": (root + "adult-medicaid/abd-policies-manuals/", "Aged, Blind and Disabled Medicaid Manual"),
        "fcm": (root + "family-and-childrens-medicaid/fcm-policies-manuals/", "Family and Children's Medicaid Manual"),
        "basic": (root + "basic-medicaid-eligibility-requirements/", "Basic Medicaid Eligibility Requirements"),
    }
    other = {
        "abd_administrative_letters": root + "adult-medicaid/abd-administrative-letters/",
        "abd_change_notices": root + "adult-medicaid/abd-change-notices/",
        "fcm_administrative_letters": root + "family-and-childrens-medicaid/fcm-administrative-letters/",
        "fcm_change_notices": root + "family-and-childrens-medicaid/fcm-change-notices/",
        "dhb_forms": root + "dhb-forms/",
        "eligibility_information_system": root + "eligibility-information-system-eis/",
    }
    row_re = re.compile(r'<tr id="post-row-\d+".*?</tr>', re.S)
    title_re = re.compile(r'<td><a href="[^"]+"\s*>(.*?)</a></td>', re.S)
    open_re = re.compile(r'<a href="([^"]+\.pdf)" class="dlp-download-link', re.I)
    docs: list[dict[str, Any]] = []
    families: dict[str, dict[str, int]] = {}
    seen_labels: set[str] = set()
    for key, (url, manual) in pages.items():
        page = fetch(url)
        fam = families.setdefault(f"{key}_manual_section_pdf", {"found": 0, "taken": 0})
        for row in row_re.findall(page):
            t, o = title_re.search(row), open_re.search(row)
            if not (t and o):
                continue
            title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t.group(1)))).strip()
            href = html.unescape(o.group(1))
            fam["found"] += 1
            m = re.match(r"^MA[-\s]*(\d{3,4})(?:-([A-Z])(?![A-Za-z]))?(?![0-9])", title)
            if m:
                label = f"ma-{m.group(1)}" + (f"-{m.group(2).lower()}" if m.group(2) else "")
            elif key == "basic":
                label = "basic-medicaid-eligibility-requirements"
            else:
                label = f"{key}-{slug(title, 50)}"
            if label in seen_labels:
                label = f"{label}-{fam['found']}"
            seen_labels.add(label)
            fam["taken"] += 1
            docs.append(document("us-nc", label=label, title=f"North Carolina {manual}: {title}", url=href, fmt="pdf",
                                 authority="North Carolina Department of Health and Human Services, Division of Health Benefits (NC Medicaid)",
                                 manual=manual, index_url=url, subtype="eligibility_manual_section_pdf",
                                 extraction={"ocr": True}, extra={"agency": "dhb", "extraction_granularity": "pdf_page", "manual_part": key}))
    for name, url in other.items():
        page = fetch(url)
        families[name] = {"found": len(set(re.findall(r'href="([^"]+\.pdf)"', page, re.I))), "taken": 0}
    return docs, {"index_url": root, "families": families}


def build_ga() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://pamms.dhs.ga.gov/dfcs/medicaid/"
    page = fetch(index)
    families = {"manual_section_html": {"found": 0, "taken": 0}, "appendix_html": {"found": 0, "taken": 0},
                "toc_page_html": {"found": 0, "taken": 0}, "pdf_export": {"found": 0, "taken": 0},
                "mt_cover_letter_pdf": {"found": 0, "taken": 0},
                "section_already_in_us_ga_ssp_manual_scope": {"found": 0, "taken": 0}}
    # Section 2578 (SSI Recipients) is already in the corpus under manifests/us-ga-ssp-manual.yaml with the
    # same citation path us-ga/manual/dfcs/medicaid/2578 and identical text; a release rejects duplicate
    # citation paths across scopes, so it is inventoried but not taken here.
    already_in_corpus = {"2578/"}
    docs = []

    def add(label: str, title: str, url: str) -> None:
        docs.append(document("us-ga", label=label, title=f"Georgia Medicaid Policy Manual: {title}", url=url, fmt="html",
                             authority="Georgia Department of Human Services, Division of Family and Children Services",
                             manual="Georgia DFCS Medicaid Policy Manual (ODIS/PAMMS)", index_url=index,
                             subtype="eligibility_manual_section", extraction={"html_content_selector": "article.doc"},
                             extra={"agency": "dfcs"}))

    for href, text in links(page, index):
        rel = href[len(index):] if href.startswith(index) else None
        if rel is None:
            if href.endswith("_exports/medicaid.pdf"):
                families["pdf_export"]["found"] += 1
            continue
        if re.fullmatch(r"\d{4}/", rel):
            if rel in already_in_corpus:
                families["section_already_in_us_ga_ssp_manual_scope"]["found"] += 1
                continue
            families["manual_section_html"]["found"] += 1
            families["manual_section_html"]["taken"] += 1
            add(rel.strip("/"), text, href)
        elif rel.endswith("-toc/") or rel == "manual-toc/":
            families["toc_page_html"]["found"] += 1
            if rel == "appendix-h-medicaid-admin-review-toc/":
                sub = fetch(href)
                for shref, stext in links(sub, href):
                    if "/dfcs/medicaid/appendix-h/" in shref:
                        families["appendix_html"]["found"] += 1
                        families["appendix_html"]["taken"] += 1
                        add("appendix-h-" + shref.rstrip("/").rsplit("/", 1)[-1], f"Appendix H {stext}", shref)
            elif rel == "appendix-g-cover-letters-toc/":
                sub = fetch(href)
                families["mt_cover_letter_pdf"]["found"] = len({h for h, _ in links(sub, href) if "cover-letter" in h})
        elif rel.startswith("appendix-"):
            families["appendix_html"]["found"] += 1
            families["appendix_html"]["taken"] += 1
            add(rel.strip("/"), text, href)
    return docs, {"index_url": index, "families": families}


def build_tx() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Crawl the two HHSC handbooks from their index pages.

    Pages carry either policy text (``article.c-article div.c-field--name-body``) or only a
    "Pages in this section" sub-menu (``.c-view--hb-submenus``); many carry both. Text-bearing
    pages become documents; menu-only pages are counted as landing pages.
    """
    from bs4 import BeautifulSoup

    host = "https://fhb.hhs.texas.gov"
    mepd = host + "/handbooks/medicaid-elderly-people-disabilities-handbook"
    twh = host + "/handbooks/texas-works-handbook"
    families: dict[str, dict[str, int]] = {}
    docs = []
    seen: set[str] = set()

    def crawl(start: str, *, handbook: str, prefix: str, manual: str, family: str, label_re: str) -> None:
        fam = families.setdefault(f"{family}_html", {"found": 0, "taken": 0})
        landing = families.setdefault(f"{family}_landing_html", {"found": 0, "taken": 0})
        queue = [start]
        while queue:
            url = queue.pop(0)
            if url in seen or not url.startswith(handbook + "/"):
                continue
            seen.add(url)
            soup = BeautifulSoup(fetch(url), "html.parser")
            heading = soup.select_one("h1.c-page-title")
            title = re.sub(r"\s+", " ", heading.get_text(" ", strip=True)) if heading else url.rsplit("/", 1)[-1]
            children = [urljoin(url, str(a["href"])).split("#", 1)[0] for a in soup.select(".c-view--hb-submenus a[href]")]
            queue.extend(children)
            m = re.match(re.escape(handbook) + "/" + label_re, url)
            if url == start or m is None:
                landing["found"] += 1
                continue
            if soup.select_one("article.c-article div.c-field--name-body") is None:
                landing["found"] += 1
                continue
            fam["found"] += 1
            fam["taken"] += 1
            docs.append(document("us-tx", label=f"{prefix}-{m.group(1)}", title=f"{manual}: {title}", url=url, fmt="html",
                                 authority="Texas Health and Human Services Commission", manual=manual,
                                 index_url=mepd if prefix == "mepd" else twh, subtype="eligibility_handbook_section",
                                 extraction={"html_content_selector": "article.c-article div.c-field--name-body",
                                             "html_drop_selectors": [".c-field__label"]},
                                 extra={"agency": "hhsc"}))

    mepd_manual = "Medicaid for the Elderly and People with Disabilities Handbook"
    index_page = fetch(mepd)
    chapters = [h for h, _ in links(index_page, mepd) if h.startswith(mepd + "/chapter-")]
    families["mepd_chapter_landing_html"] = {"found": len(chapters), "taken": 0}
    for chref in chapters:
        seen.discard(chref)
        crawl(chref, handbook=mepd, prefix="mepd", manual=mepd_manual, family="mepd_section", label_re=r"([a-r]-\d{4})-")
    crawl(mepd + "/mepd-appendices", handbook=mepd, prefix="mepd", manual=mepd_manual, family="mepd_appendix", label_re=r"(appendix-[a-z]+)-")
    glossary = mepd + "/mepd-glossary"
    families["mepd_glossary_html"] = {"found": 1, "taken": 1}
    docs.append(document("us-tx", label="mepd-glossary", title=f"{mepd_manual}: MEPD Glossary", url=glossary, fmt="html",
                         authority="Texas Health and Human Services Commission", manual=mepd_manual, index_url=mepd,
                         subtype="eligibility_handbook_section",
                         extraction={"html_content_selector": "article.c-article div.c-field--name-body",
                                     "html_drop_selectors": [".c-field__label"]}, extra={"agency": "hhsc"}))
    other = [t for h, t in links(index_page, mepd) if h.startswith(mepd + "/mepd-") and "glossary" not in h and "appendices" not in h]
    families["mepd_forms_notices_revisions_bulletins_pages"] = {"found": len(other), "taken": 0}

    twh_page = fetch(twh)
    parts = [(h, t) for h, t in links(twh_page, twh) if h.startswith(twh + "/part-")]
    families["twh_part_landing_html"] = {"found": len(parts), "taken": 0}
    part_a = twh + "/part-a-determining-eligibility"
    crawl(part_a, handbook=twh, prefix="twh", manual="Texas Works Handbook", family="twh_part_a_section", label_re=r"(a-\d{3,4})-")
    for phref, ptext in parts:
        if phref == part_a:
            continue
        n = len({h for h, _ in links(fetch(phref), phref) if re.match(re.escape(twh) + r"/[a-z]-\d{3,4}-", h)})
        families[f"twh_{slug(ptext.split(',')[0])}_chapters_html"] = {"found": n, "taken": 0}
    return docs, {"index_url": mepd, "twh_index_url": twh, "families": families}


def build_pa() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # RoboHelp output; the topic list lives in whxdata/toc.new.js and nested tocN.new.js
    base = "http://services.dpw.state.pa.us/oimpolicymanuals/ma/"
    index = base + "index.htm"
    fetch(index)

    def toc(key: str) -> list[dict[str, Any]]:
        text = fetch(f"{base}whxdata/{key}.new.js")
        m = re.search(r"var toc =\s*(\[.*?\]);\s*window", text, re.S)
        return json.loads(m.group(1)) if m else []

    entries: list[tuple[str, str, str]] = []  # (chapter name, topic name, url)

    def walk(key: str, chapter: str | None) -> None:
        for item in toc(key):
            name, url = item.get("name", ""), item.get("url")
            top = chapter or name
            if url:
                # anchors point into the same topic page; the page is the document
                entries.append((top, name, base + url.split("#", 1)[0]))
            if item.get("type") == "book" and item.get("key"):
                walk(item["key"], top)

    walk("toc", None)
    families = {"handbook_topic_html": {"found": 0, "taken": 0}, "forms_opsmemo_policy_clarification_catalog_html": {"found": 0, "taken": 0}}
    docs = []
    seen: set[str] = set()
    for chapter, name, url in entries:
        if url in seen:
            continue
        seen.add(url)
        if chapter.startswith("300 "):
            families["forms_opsmemo_policy_clarification_catalog_html"]["found"] += 1
            continue
        families["handbook_topic_html"]["found"] += 1
        families["handbook_topic_html"]["taken"] += 1
        rel = re.sub(r"\.htm$", "", url[len(base):])
        label = "/".join(slug(part, 100) for part in rel.split("/"))
        docs.append(document("us-pa", label=label, title=f"Pennsylvania Medical Assistance Eligibility Handbook: {name}", url=url, fmt="html",
                             authority="Pennsylvania Department of Human Services, Office of Income Maintenance",
                             manual="Pennsylvania Medical Assistance Eligibility Handbook", index_url=index,
                             subtype="eligibility_handbook_topic",
                             extraction={"html_drop_selectors": [".topic-header", ".topic-header-shadow"]},
                             extra={"agency": "dhs", "handbook_chapter": chapter,
                                    "transport_note": "publisher serves the handbook over plain http only; https connections time out"}))
    return docs, {"index_url": index, "families": families}


def build_ar() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://humanservices.arkansas.gov/divisions-shared-services/county-operations/division-policies/"
    page = fetch(index)
    wanted = {"Medical Services Policy Manual": ("policy-manual", "Arkansas Medical Services Policy Manual"),
              "Medical Services Appendices": ("appendices", "Arkansas Medical Services Policy Manual: Appendices")}
    families = {"medical_services_manual_pdf": {"found": 0, "taken": 0}, "other_program_manual_pdf": {"found": 0, "taken": 0}}
    docs = []
    for href, text in links(page, index):
        if not href.lower().endswith(".pdf"):
            continue
        if text in wanted:
            label, title = wanted[text]
            families["medical_services_manual_pdf"]["found"] += 1
            families["medical_services_manual_pdf"]["taken"] += 1
            docs.append(document("us-ar", label=label, title=title, url=href, fmt="pdf",
                                 authority="Arkansas Department of Human Services, Division of County Operations",
                                 manual="Arkansas Medical Services Policy Manual", index_url=index,
                                 subtype="eligibility_manual_pdf", extraction={"ocr": True},
                                 extra={"agency": "dco", "extraction_granularity": "pdf_page"}))
        else:
            families["other_program_manual_pdf"]["found"] += 1
    return docs, {"index_url": index, "families": families}


def build_nj() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://www.nj.gov/humanservices/notices/rules-and-fees/rules-and-regulations/"
    page = fetch(index)
    wanted = {"10:69": "AFDC-Related Medicaid", "10:70": "Medically Needy Program", "10:71": "Medicaid Only",
              "10:72": "New Jersey Care Special Medicaid Programs Manual", "10:78": "NJ FamilyCare",
              "10:79": "NJ FamilyCare - Children's Program"}
    families = {"medicaid_eligibility_chapter_pdf": {"found": 0, "taken": 0}, "other_title_10_chapter_pdf": {"found": 0, "taken": 0}}
    docs = []
    for href, text in links(page, index):
        if not re.match(r"^10:\d+[A-Z]?$", text):
            continue
        if text in wanted:
            families["medicaid_eligibility_chapter_pdf"]["found"] += 1
            families["medicaid_eligibility_chapter_pdf"]["taken"] += 1
            docs.append(document("us-nj", label=f"njac-{slug(text)}", title=f"New Jersey Medicaid Eligibility Manuals: N.J.A.C. {text} {wanted[text]}",
                                 url=href, fmt="pdf",
                                 authority="New Jersey Department of Human Services (Office of Legal and Regulatory Affairs; Division of Medical Assistance and Health Services)",
                                 manual="New Jersey Medicaid Eligibility and Service Manuals (N.J.A.C. Title 10)", index_url=index,
                                 subtype="eligibility_manual_chapter_pdf", extraction={"ocr": True},
                                 extra={"agency": "dhs", "extraction_granularity": "pdf_page", "njac_chapter": text}))
        else:
            families["other_title_10_chapter_pdf"]["found"] += 1
    return docs, {"index_url": index, "families": families}


# --------------------------------------------------------------------------- batch 2 states

DISCOVERED_VIA_B2 = "manual-review:medicaid-agent-queue batch 2; publisher index {index}"


def document2(jur: str, **kwargs: Any) -> dict[str, Any]:
    """Batch-2 wrapper around ``document``: same shape, batch-2 discovery provenance."""
    doc = document(jur, **kwargs)
    doc["metadata"]["discovered_via"] = DISCOVERED_VIA_B2.format(index=kwargs["index_url"])
    return doc


def build_wa() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """HCA Apple Health eligibility manual: four hub pages (Drupal views) list the manual pages."""
    from bs4 import BeautifulSoup

    host = "https://www.hca.wa.gov"
    index = host + "/health-care-services-supports/program-administration/apple-health-eligibility-manual"
    overview = fetch(index)
    hubs = {"general": "General eligibility requirements that apply to all Apple Health programs",
            "non-magi": "Classic (Non-MAGI-based) programs manual",
            "magi": "Modified Adjusted Gross Income (MAGI-based) programs manual",
            "ltss": "Long-term services and supports (LTSS) manual"}
    soup = BeautifulSoup(overview, "html.parser")
    body = soup.select_one("main")
    hub_links = [urljoin(index, str(a["href"])) for a in body.select("a[href]") if a.get_text(" ", strip=True).startswith("View ")]
    tools = [(urljoin(index, str(a["href"])), a.get_text(" ", strip=True)) for a in body.select("a[href]")
             if a.get_text(" ", strip=True) in {"Introduction overview", "Program standards for income and resources",
                                                 "Apple Health (Medicaid) manual WAC index", "Apple Health (Medicaid) manual revision log",
                                                 "Forms and publications", "Authorized Representative DSHS form 14-532"}]
    families: dict[str, dict[str, int]] = {}
    docs: list[dict[str, Any]] = []
    seen: set[str] = set()
    manual = "Washington Apple Health Eligibility Manual"

    def add(url: str, text: str, part: str) -> bool:
        final = url.rstrip("/")
        label = slug(final.rsplit("/", 1)[-1], 100)
        if label in seen:
            return False  # the same page is listed under more than one hub / tool list
        seen.add(label)
        docs.append(document2("us-wa", label=label, title=f"{manual}: {text}", url=final, fmt="html",
                              authority="Washington State Health Care Authority", manual=manual, index_url=index,
                              subtype="eligibility_manual_page",
                              extraction={"html_content_selector": "main article.node--type-eligibility-manual",
                                          "html_drop_selectors": [".field--name-field-report-link"]},
                              extra={"agency": "hca", "manual_part": part}))
        return True

    for hub_url in hub_links:
        page = BeautifulSoup(fetch(hub_url), "html.parser")
        block = page.select_one(".region-content-views .block-views")
        key = next(k for k in hubs if block.get("id", "").endswith(k))
        fam = families.setdefault(f"{key}_manual_page_html", {"found": 0, "taken": 0})
        for a in block.select("a[href]"):
            fam["found"] += 1
            if add(urljoin(hub_url, str(a["href"])), a.get_text(" ", strip=True), key):
                fam["taken"] += 1
    families["hub_landing_page_html"] = {"found": len(hub_links), "taken": 0}
    families["additional_tool_manual_page_html"] = {"found": 0, "taken": 0}
    families["additional_tool_other_page_or_form"] = {"found": 0, "taken": 0}
    for url, text in tools:
        if text in {"Introduction overview", "Program standards for income and resources"}:
            families["additional_tool_manual_page_html"]["found"] += 1
            # /node/N redirects to the canonical alias; resolve it so source_url is the published path
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=90, allow_redirects=True)
            resp.raise_for_status()
            if add(resp.url, text, "general"):
                families["additional_tool_manual_page_html"]["taken"] += 1
        else:
            families["additional_tool_other_page_or_form"]["found"] += 1
    return docs, {"index_url": index, "families": families}


def build_ma() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """MassHealth member eligibility regulations 130 CMR 501-522 from the mass.gov law library.

    The regulation page carries only the downloads; the text is the official PDF, so the page is
    ``source_url`` and the PDF is ``download_url``. mass.gov rate-limits: pace requests, retry 403.
    """
    from bs4 import BeautifulSoup

    index = "https://www.mass.gov/law-library/130-cmr"

    def slow_fetch(url: str) -> str:
        for attempt in range(4):
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=90)
            if resp.status_code == 403 and attempt < 3:
                time.sleep(20 * (attempt + 1))
                continue
            resp.raise_for_status()
            time.sleep(3)
            return resp.text
        raise AssertionError("unreachable")

    page = slow_fetch(index)
    families = {"member_eligibility_regulation_pdf": {"found": 0, "taken": 0}, "other_130_cmr_regulation": {"found": 0, "taken": 0}}
    docs = []
    seen: set[str] = set()
    for href, text in links(page, index):
        m = re.match(r"^130 CMR (\d{3})\.000: MassHealth: (.+)$", text)
        if "/regulations/130-CMR-" not in href or href in seen:
            continue
        seen.add(href)
        if not m or not (501 <= int(m.group(1)) <= 522):
            families["other_130_cmr_regulation"]["found"] += 1
            continue
        chapter, heading = m.group(1), m.group(2)
        families["member_eligibility_regulation_pdf"]["found"] += 1
        reg = BeautifulSoup(slow_fetch(href), "html.parser")
        pdf = None
        for a in reg.select("a.ma__download-link__file-link[href]"):
            if "Open PDF file" in a.get_text(" ", strip=True):
                pdf = urljoin(href, str(a["href"]))
                break
        if pdf is None:
            print(f"us-ma: no PDF download on {href}", file=sys.stderr)
            continue
        families["member_eligibility_regulation_pdf"]["taken"] += 1
        doc = document2("us-ma", label=f"130-cmr-{chapter}", title=f"MassHealth Member Regulations: 130 CMR {chapter}.000 {heading}", url=href, fmt="pdf",
                        authority="Massachusetts Executive Office of Health and Human Services (MassHealth)",
                        manual="MassHealth member eligibility regulations (130 CMR 501.000-522.000)", index_url=index,
                        subtype="eligibility_regulation_chapter_pdf", extraction={"ocr": True},
                        extra={"agency": "eohhs", "extraction_granularity": "pdf_page", "cmr_chapter": f"130 CMR {chapter}.000",
                               "download_note": "the mass.gov regulation page carries no text, only the official PDF/DOCX downloads; the PDF is fetched as download_url"})
        doc["download_url"] = pdf
        docs.append(doc)
    return docs, {"index_url": index, "families": families}


def build_in() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://www.in.gov/fssa/ompp/forms-documents-and-tools/medicaid-eligibility-policy-manual/"
    page = fetch(index)
    families = {"manual_chapter_pdf": {"found": 0, "taken": 0}, "combined_manual_pdf": {"found": 0, "taken": 0},
                "transmittal_pdf": {"found": 0, "taken": 0}}
    docs = []
    manual = "Indiana Health Coverage Program Policy Manual (IHCPPM)"
    seen: set[str] = set()
    for href, text in links(page, index):
        m = re.search(r"/Medicaid_PM_(\d{4})\.pdf", href)
        if m and href not in seen:
            seen.add(href)
            families["manual_chapter_pdf"]["found"] += 1
            families["manual_chapter_pdf"]["taken"] += 1
            docs.append(document2("us-in", label=f"ihcppm-chapter-{m.group(1)}", title=f"{manual}: Chapter {m.group(1)} {text}", url=href, fmt="pdf",
                                  authority="Indiana Family and Social Services Administration, Office of Medicaid Policy and Planning",
                                  manual=manual, index_url=index, subtype="eligibility_manual_chapter_pdf", extraction={"ocr": True},
                                  extra={"agency": "fssa", "extraction_granularity": "pdf_page", "manual_chapter": m.group(1)}))
        elif "/Medicaid_Combined_PM.pdf" in href and href not in seen:
            seen.add(href)
            families["combined_manual_pdf"]["found"] += 1
        elif href.rstrip("/").endswith("medicaid-program-policy-manual-transmittals"):
            sub = fetch(href)
            families["transmittal_pdf"]["found"] = len({h for h, _ in links(sub, href) if re.search(r"/dA/|\.pdf", h, re.I)})
    return docs, {"index_url": index, "families": families}


def build_md() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://health.maryland.gov/mmcp/Pages/MedicaidManual.aspx"
    page = fetch(index)
    families = {"manual_section_pdf": {"found": 0, "taken": 0}, "manual_supplement_action_transmittal_pdf": {"found": 0, "taken": 0},
                "coverage_group_guide_pdf": {"found": 0, "taken": 0}}
    docs = []
    manual = "Maryland Medical Assistance Eligibility Manual"
    seen: set[str] = set()
    for href, text in links(page, index):
        if not href.lower().endswith(".pdf") or href in seen:
            continue
        seen.add(href)
        if "/ManualSupplements/" in href:
            families["manual_supplement_action_transmittal_pdf"]["found"] += 1
        elif "/Coverage%20Groups/" in href or "/Coverage Groups/" in href:
            families["coverage_group_guide_pdf"]["found"] += 1
        elif "/Medicaid%20Manual/" in href or "/Medicaid Manual/" in href:
            families["manual_section_pdf"]["found"] += 1
            families["manual_section_pdf"]["taken"] += 1
            m = re.match(r"^Section[- ]?(\d{3,4})[- ]*(.*)$", text)
            if m and not re.search(r"Resource[- ]Table", text):
                label, title = f"section-{m.group(1)}", f"Section {m.group(1)} {m.group(2).strip(' -')}"
            elif m:
                label, title = f"section-{m.group(1)}-resource-table-2024", "Section 800 Resource Table 2024"
            elif text.startswith("Appendix schedules"):
                label, title = "appendix-schedules-2026", "Appendix schedules 2026 (effective 1/1/2026)"
            else:
                label, title = slug(text), text
            docs.append(document2("us-md", label=label, title=f"{manual}: {title}", url=href, fmt="pdf",
                                  authority="Maryland Department of Health, Medicaid (Medical Care Programs) Administration",
                                  manual=manual, index_url=index, subtype="eligibility_manual_section_pdf", extraction={"ocr": True},
                                  extra={"agency": "mdh", "extraction_granularity": "pdf_page"}))

    def order(doc: dict[str, Any]) -> tuple[int, int, str]:
        label = doc["citation_path"].rsplit("/", 1)[-1]
        m = re.match(r"^section-(\d+)", label)
        return (1 if m else (0 if label in {"beginning-of-manual", "manual-table-of-contents"} else 2), int(m.group(1)) if m else 0, label)

    docs.sort(key=order)  # manual order: front matter, sections 200-1600, appendix/tables
    return docs, {"index_url": index, "families": families}


def build_mo() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """DSS manuals site (WordPress): the section pages are enumerated from the site's own sitemap,
    as the MO SNAP manual scope did; the appendix files hang off the manual landing pages' menus."""
    from bs4 import BeautifulSoup

    host = "https://dssmanuals.mo.gov"
    manuals = {"magi": (host + "/family-mo-healthnet-magi/", "Missouri Family MO HealthNet (MAGI) Manual", "menu-magi-appendices-container"),
               "mhabd": (host + "/mo-healthnet-for-the-aged-blind-and-disabled/", "Missouri MO HealthNet for the Aged, Blind, and Disabled (MHABD) Manual",
                         "menu-mhabdsubnav-container")}
    sitemaps = [host + "/wp-sitemap-posts-page-1.xml", host + "/wp-sitemap-posts-page-2.xml"]
    urls: list[str] = []
    for sm in sitemaps:
        urls.extend(re.findall(r"<loc>([^<]+)</loc>", fetch(sm)))
    families: dict[str, dict[str, int]] = {}
    docs = []
    for key, (landing, manual, menu_class) in manuals.items():
        fam = families.setdefault(f"{key}_manual_page_html", {"found": 0, "taken": 0})
        for url in urls:
            if not url.startswith(landing):
                continue
            rel = url[len(landing):].strip("/")
            fam["found"] += 1
            fam["taken"] += 1
            label = key if not rel else key + "/" + "/".join(slug(p, 100) for p in rel.split("/"))
            title = manual if not rel else f"{manual}: {rel.rsplit('/', 1)[-1]}"
            docs.append(document2("us-mo", label=label, title=title, url=url, fmt="html",
                                  authority="Missouri Department of Social Services, Family Support Division", manual=manual,
                                  index_url=landing, subtype="eligibility_manual_section", extraction={"html_content_selector": ".entry-content"},
                                  extra={"agency": "dss", "manual_part": key, "source_sitemap_urls": sitemaps}))
        soup = BeautifulSoup(fetch(landing), "html.parser")
        menu = soup.select_one(f".{menu_class}")
        pdf_fam = families.setdefault(f"{key}_appendix_pdf", {"found": 0, "taken": 0})
        other_fam = families.setdefault(f"{key}_appendix_spreadsheet", {"found": 0, "taken": 0})
        for a in menu.select("a[href*='wp-content/uploads']"):
            href, text = str(a["href"]), a.get_text(" ", strip=True)
            m = re.match(r"^Appendix ([A-Z])\b", text)
            if not href.lower().endswith(".pdf"):
                other_fam["found"] += 1
                continue
            pdf_fam["found"] += 1
            pdf_fam["taken"] += 1
            docs.append(document2("us-mo", label=f"{key}/appendix-{m.group(1).lower()}", title=f"{manual}: {text}", url=href, fmt="pdf",
                                  authority="Missouri Department of Social Services, Family Support Division", manual=manual,
                                  index_url=landing, subtype="eligibility_manual_appendix_pdf", extraction={"ocr": True},
                                  extra={"agency": "dss", "manual_part": key, "extraction_granularity": "pdf_page"}))
    return docs, {"index_url": manuals["magi"][0], "mhabd_index_url": manuals["mhabd"][0], "families": families}


def build_wi() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """DHS publications library collections for the two eligibility handbooks; the online handbook
    host (emhandbooks.wisconsin.gov) does not answer TCP from this network, so the publisher's own
    PDF release is taken, as the FoodShare handbook scope did."""
    collections = {"meh": ("https://www.dhs.wisconsin.gov/library/collection/p-10030", "Wisconsin Medicaid Eligibility Handbook", r"p10030-(\d\d-\d\d)\.pdf"),
                   "badgercare-plus-handbook": ("https://www.dhs.wisconsin.gov/library/collection/p-10171", "Wisconsin BadgerCare Plus Eligibility Handbook", r"p10171-(\d\d-\d\d)\.pdf")}
    families: dict[str, dict[str, int]] = {}
    docs = []
    for key, (index, manual, pat) in collections.items():
        page = fetch(index)
        releases = []
        for href, text in links(page, index):
            m = re.search(pat, href)
            if m:
                releases.append((m.group(1), href, text))
        releases.sort(reverse=True)
        current = releases[0]
        families[f"{key}_current_release_pdf"] = {"found": 1, "taken": 1}
        families[f"{key}_prior_release_pdf"] = {"found": len(releases) - 1, "taken": 0}
        docs.append(document2("us-wi", label=f"{key}-release-{current[0]}", title=f"{manual}: Release {current[0]}", url=current[1], fmt="pdf",
                              authority="Wisconsin Department of Health Services", manual=manual, index_url=index,
                              subtype="eligibility_handbook_release_pdf", extraction={"ocr": True},
                              extra={"agency": "dhs", "extraction_granularity": "pdf_page", "release": current[0],
                                     "online_handbook_url": "https://www.emhandbooks.wisconsin.gov/" + ("meh-ebd/meh.htm" if key == "meh" else "bcplus/bcplus.htm"),
                                     "transport_note": "emhandbooks.wisconsin.gov TCP connections time out from this network (curl 28, plain and browser-impersonated); the DHS publications library PDF of the same release is the publisher's own copy"}))
    return docs, {"index_url": collections["meh"][0], "badgercare_index_url": collections["badgercare-plus-handbook"][0], "families": families}


def build_co() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Colorado has no separate eligibility manual: Medical Assistance eligibility is 10 CCR 2505-10
    section 8.100 on the Secretary of State CCR site (the publisher used by the CO SNAP rules scope)."""
    index = ("https://www.sos.state.co.us/CCR/NumericalCCRDocList.do?deptID=7&deptName=2505,1305%20Department%20of%20Health%20Care%20Policy%20and%20Financing"
             "&agencyID=69&agencyName=2505%20Medical%20Services%20Board%20(Volume%208;%20Medical%20Assistance,%20Children's%20Health%20Plan)")
    page = fetch(index)
    families = {"medical_assistance_eligibility_rule_pdf": {"found": 0, "taken": 0}, "other_volume_8_rule": {"found": 0, "taken": 0}}
    docs = []
    for m in re.finditer(r"<a[^>]+href=['\"]([^'\"]*ruleId[^'\"]*)['\"][^>]*>(.*?)</a></TD>\s*<TD>(.*?)</TD>", page, re.S | re.I):
        series = re.sub(r"\s+", " ", m.group(2)).strip()
        title = html.unescape(re.sub(r"\s+", " ", m.group(3)).strip())
        if series != "10 CCR 2505-10 8.100":
            families["other_volume_8_rule"]["found"] += 1
            continue
        families["medical_assistance_eligibility_rule_pdf"]["found"] += 1
        info_url = urljoin(index, html.unescape(m.group(1)))
        info = fetch(info_url)
        cur = re.search(r"<b>Current version</b>.*?OpenRuleWindow\('(\d+)',\s*'([^']+)'\s*\)\"\s*>\s*(\d{2}/\d{2}/\d{4})\s*\(PDF\)", info, re.S)
        if not cur:
            print("us-co: current version link not found on rule info page", file=sys.stderr)
            continue
        version_id, file_name, effective = cur.group(1), cur.group(2), cur.group(3)
        pdf = f"https://www.sos.state.co.us/CCR/GenerateRulePdf.do?ruleVersionId={version_id}&fileName={file_name.replace(' ', '%20')}"
        families["medical_assistance_eligibility_rule_pdf"]["taken"] += 1
        doc = document2("us-co", label="10-ccr-2505-10-8-100", title=f"Colorado Medical Assistance Rules: 10 CCR 2505-10 Section 8.100 {title.split('8.100', 1)[-1].strip(' ,')}",
                        url=info_url, fmt="pdf", authority="Colorado Department of Health Care Policy and Financing, Medical Services Board",
                        manual="Colorado Medical Assistance Eligibility Rules (10 CCR 2505-10 Section 8.100)", index_url=index,
                        subtype="eligibility_rule_pdf", extraction={"ocr": True},
                        extra={"agency": "hcpf", "extraction_granularity": "pdf_page", "official_publisher": "Colorado Secretary of State",
                               "code_rule": "10 CCR 2505-10 8.100", "rule_version_id": version_id,
                               "rule_effective_date": dt.datetime.strptime(effective, "%m/%d/%Y").date().isoformat()})
        doc["download_url"] = pdf
        docs.append(doc)
    return docs, {"index_url": index, "families": families}


def build_mn() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # RoboHelp output like the PA handbook: topic tree in whxdata/toc.new.js + nested tocN.new.js
    base = "https://hcopub.dhs.state.mn.us/epm/"
    index = base + "home.htm"
    home = fetch(index)

    def toc(key: str) -> list[dict[str, Any]]:
        text = fetch(f"{base}whxdata/{key}.new.js")
        m = re.search(r"var toc =\s*(\[.*?\]);\s*window", text, re.S)
        return json.loads(m.group(1)) if m else []

    entries: list[tuple[str, str]] = []

    def walk(key: str) -> None:
        for item in toc(key):
            if item.get("url"):
                entries.append((item.get("name", ""), base + item["url"].split("#", 1)[0]))
            if item.get("type") == "book" and item.get("key"):
                walk(item["key"])

    walk("toc")
    families = {"manual_topic_html": {"found": 0, "taken": 0}, "home_page_bulletin_pdf": {"found": 0, "taken": 0}}
    families["home_page_bulletin_pdf"]["found"] = len({h for h, _ in links(home, index) if h.lower().endswith(".pdf")})
    docs = []
    seen: set[str] = set()
    manual = "Minnesota Health Care Programs Eligibility Policy Manual (EPM)"
    for name, url in entries:
        families["manual_topic_html"]["found"] += 1
        if url in seen:
            continue  # the TOC lists 2.1.1.2.1 twice
        seen.add(url)
        families["manual_topic_html"]["taken"] += 1
        label = slug(url[len(base):].rsplit(".", 1)[0])
        docs.append(document2("us-mn", label=label, title=f"{manual}: {name}", url=url, fmt="html",
                              authority="Minnesota Department of Human Services", manual=manual, index_url=index,
                              subtype="eligibility_manual_topic",
                              extraction={"html_content_selector": "#rh-topic", "html_drop_selectors": ["p.Footer"]},
                              extra={"agency": "dhs"}))
    return docs, {"index_url": index, "families": families}


BUILDERS_BATCH2 = {"us-wa": build_wa, "us-ma": build_ma, "us-in": build_in, "us-md": build_md,
                   "us-mo": build_mo, "us-wi": build_wi, "us-co": build_co, "us-mn": build_mn}
NAMES_BATCH2 = {"us-wa": "Washington", "us-az": "Arizona", "us-tn": "Tennessee", "us-ma": "Massachusetts", "us-in": "Indiana",
                "us-md": "Maryland", "us-mo": "Missouri", "us-wi": "Wisconsin", "us-co": "Colorado", "us-mn": "Minnesota"}
SOURCE_KIND_BATCH2 = {"us-wa": "official_html_manual_pages", "us-ma": "official_pdf_cmr_chapters", "us-in": "official_pdf_manual_chapters",
                      "us-md": "official_pdf_manual_sections", "us-mo": "official_html_manual_sections", "us-wi": "official_pdf_handbook_releases",
                      "us-co": "official_pdf_ccr_rule", "us-mn": "official_html_manual_topics"}
RETRY_NOTE = (" Retried 2026-09-10T18:36Z (plain request) and 2026-09-10T18:37Z (curl-cffi chrome120 browser impersonation, 20 s timeouts), "
              "same failure: {detail}")
STATIC_ROWS_BATCH2: dict[str, dict[str, Any]] = {
    "us-az": {
        "queue_status": "blocked_primary_source",
        "source_kind": "official_html_manual_pages",
        "primary_source_url": "https://www.azahcccs.gov/Resources/EligibilityPolicy/",
        "target_manifest": "manifests/us-az-medicaid-eligibility-manual.yaml",
        "target_scope": {"jurisdiction": "us-az", "document_class": "manual", "version": VERSION},
        "index_url": "https://www.azahcccs.gov/Resources/EligibilityPolicy/",
        "index_document_count": None, "taken_count": 0,
        "notes": ("Blocked 2026-09-10: azahcccs.gov (AHCCCS Eligibility Policy Manual index, the AHCCCS Medical Policy Manual path and the site root) "
                  "returns HTTP 403 Forbidden from 'Microsoft-Azure-Application-Gateway/v2' within 1 s for the Axiom user agent, a plain Chrome user "
                  "agent and curl-cffi chrome120 impersonation (179-581 byte bodies). No workaround attempted. Index inventory not possible."),
    },
    "us-tn": {
        "queue_status": "blocked_primary_source",
        "source_kind": "official_pdf_policy_documents",
        "primary_source_url": "https://www.tn.gov/tenncare/policy-guidelines/eligibility-policy.html",
        "target_manifest": "manifests/us-tn-medicaid-eligibility-manual.yaml",
        "target_scope": {"jurisdiction": "us-tn", "document_class": "manual", "version": VERSION},
        "index_url": "https://www.tn.gov/tenncare/policy-guidelines/eligibility-policy.html",
        "index_document_count": None, "taken_count": 0,
        "notes": ("Blocked 2026-09-10: tn.gov (TennCare Eligibility Policy index) returns HTTP 403 Forbidden from 'awselb/2.0' within 1 s (118-520 byte "
                  "bodies) for the Axiom user agent, a plain Chrome user agent and curl-cffi chrome120 impersonation; the tn.gov/tenncare.html root "
                  "did not answer at all (curl exit 0 bytes). No workaround attempted. Index inventory not possible."),
    },
}


BUILDERS = {"us-va": build_va, "us-ny": build_ny, "us-nc": build_nc, "us-ga": build_ga,
            "us-tx": build_tx, "us-pa": build_pa, "us-ar": build_ar, "us-nj": build_nj}
NAMES = {"us-ar": "Arkansas", "us-va": "Virginia", "us-ca": "California", "us-tx": "Texas", "us-fl": "Florida",
         "us-ny": "New York", "us-pa": "Pennsylvania", "us-il": "Illinois", "us-oh": "Ohio", "us-ga": "Georgia",
         "us-nc": "North Carolina", "us-mi": "Michigan", "us-nj": "New Jersey"}
SOURCE_KIND = {"us-va": "official_pdf_manual_chapters", "us-ny": "official_pdf_manual_chapters", "us-nc": "official_pdf_manual_sections",
               "us-ga": "official_html_manual_sections", "us-tx": "official_html_handbook_sections",
               "us-pa": "official_html_handbook_topics", "us-ar": "official_pdf_manual", "us-nj": "official_pdf_njac_chapters"}

STATIC_ROWS: dict[str, dict[str, Any]] = {
    "us": {
        "queue_status": "needs_review",
        "source_kind": "federal_regulation_ecfr",
        "primary_source_url": "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-435",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us", "document_class": "regulation", "version": "2026-06-25-title-42-part-435"},
        "index_url": "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C",
        "index_document_count": None, "taken_count": 0,
        "notes": ("Batch 1 finding (2026-09-10): 42 CFR part 435 is already in the corpus as us/regulation version "
                  "2026-06-25-title-42-part-435 (coverage complete, 168 provisions) plus the CMS-2454-IFC community-engagement "
                  "scopes; 42 CFR part 436 (Puerto Rico, Guam, Virgin Islands eligibility) is NOT in the corpus (no coverage, "
                  "manifest, or ingest-run note mentions part 436). Nothing federal was re-ingested and none of the federal lead-list "
                  "URLs were taken in this run. A later run should extract part 436 through extract-ecfr --only-title 42 --only-part 436."),
    },
    "us-ca": {
        "queue_status": "blocked_primary_source",
        "source_kind": "official_pdf_manual_articles",
        "primary_source_url": "https://www.dhcs.ca.gov/services/medi-cal/eligibility/Pages/MEPM.aspx",
        "target_manifest": "manifests/us-ca-medicaid-eligibility-manual.yaml",
        "target_scope": {"jurisdiction": "us-ca", "document_class": "manual", "version": VERSION},
        "index_url": "https://www.dhcs.ca.gov/services/medi-cal/eligibility/Pages/MEPM.aspx",
        "index_document_count": None, "taken_count": 0,
        "notes": ("Blocked 2026-09-10: the DHCS Medi-Cal Eligibility Procedures Manual (MEPM) index returns HTTP 403 with an Imperva/Incapsula "
                  "'Request unsuccessful' interstitial (incident id 648000110623365723-464410415712436979) for the Axiom user agent, a plain "
                  "browser user agent, and curl-cffi impersonation profiles chrome120, chrome131, safari17_0, firefox133 and edge101 "
                  "(the existing manifest browser_impersonation option). No workaround attempted. Index inventory not possible."),
    },
    "us-oh": {
        "queue_status": "blocked_primary_source",
        "source_kind": "official_html_oac_rules_and_mepl",
        "primary_source_url": "https://codes.ohio.gov/ohio-administrative-code/5160:1",
        "target_manifest": "manifests/us-oh-medicaid-eligibility-manual.yaml",
        "target_scope": {"jurisdiction": "us-oh", "document_class": "manual", "version": VERSION},
        "index_url": "https://medicaid.ohio.gov/resources-for-providers/policies-guidelines/medicaid-eligibility-procedure-letters/",
        "index_document_count": None, "taken_count": 0,
        "notes": ("Blocked 2026-09-10: Ohio's eligibility manual is OAC 5160:1 (Ohio Laws and Administrative Rules, codes.ohio.gov, the same "
                  "publisher used for the OH SNAP rules scope) with ODM Medicaid Eligibility Procedure Letters on medicaid.ohio.gov. "
                  "codes.ohio.gov: TCP connect to 198.234.74.32:443 times out (curl 28 after 60-75 s, curl-cffi chrome120 the same, "
                  "WebFetch ECONNREFUSED). medicaid.ohio.gov and ohio.gov: every path including the site root returns HTTP 404 "
                  "(5,279-byte error page) from this client and from WebFetch. Only the dam.assets.ohio.gov asset host answers. "
                  "No workaround attempted; retry from another network before assuming a permanent block."),
    },
    "us-fl": {
        "queue_status": "done",
        "source_kind": "official_html_combined_manual",
        "primary_source_url": "https://www.myflfamilies.com/services/public-assistance/ess-program-policy-manual",
        "target_manifest": "manifests/us-fl-ess-manual.yaml",
        "target_scope": {"jurisdiction": "us-fl", "document_class": "manual", "version": "2026-05-27-fl-ess-manual-r2026-07-15-self-contained"},
        "index_url": None, "index_document_count": None, "taken_count": 0,
        "notes": ("Already in corpus: Florida DCF ESS Program Policy Manual (manifests/us-fl-ess-manual.yaml, 48 documents) carries the "
                  "Medicaid eligibility chapters (1400/1600/1800 MFAM-MSSI, 2000 Coverage Groups, 2200 Standard Filing Unit, 2400 Budgeting, "
                  "2600 Calculation of Benefits, Appendix A-7 Family-Related Medicaid income limits, A-9 SSI-related standards, A-9.1 MSP). "
                  "Not duplicated in batch 1; does not count toward the batch, Michigan pulled instead (itself already covered), then New Jersey."),
    },
    "us-il": {
        "queue_status": "done",
        "source_kind": "official_html_combined_manual",
        "primary_source_url": "https://www.dhs.state.il.us/page.aspx?item=13473",
        "target_manifest": "manifests/us-il-snap-manual.yaml",
        "target_scope": {"jurisdiction": "us-il", "document_class": "manual", "version": "2026-05-27-il-cash-snap-medical-manual-r2026-07-15-self-contained"},
        "index_url": None, "index_document_count": None, "taken_count": 0,
        "notes": ("Already in corpus: Illinois DHS Cash, SNAP and Medical Manual (manifests/us-il-snap-manual.yaml, 4,750 documents) includes "
                  "PM/WAG 15 Eligibility for Medical Only Programs, PM/WAG 20 Medical Program and the medical-program sub-sections. "
                  "Not duplicated in batch 1; does not count toward the batch, North Carolina pulled instead."),
    },
    "us-mi": {
        "queue_status": "done",
        "source_kind": "official_pdf_combined_manual",
        "primary_source_url": "https://mdhhs-pres-prod.michigan.gov/OLMWeb/ex/BP/Public/BEM/000.pdf",
        "target_manifest": "manifests/us-mi-bridges-manual.yaml",
        "target_scope": {"jurisdiction": "us-mi", "document_class": "manual", "version": "2026-07-17-mi-bridges-manual"},
        "index_url": None, "index_document_count": None, "taken_count": 0,
        "notes": ("Already in corpus: Michigan Bridges Eligibility Manual (manifests/us-mi-bridges-manual.yaml, 196 documents) carries the MA "
                  "chapters BEM 105-174, 211, 260, 402, 405, 530-547. Pulled as the replacement for Florida, found covered, so New Jersey was "
                  "pulled next. Does not count toward the batch."),
    },
}


BATCHES = {
    "1": (BUILDERS, STATIC_ROWS, NAMES, SOURCE_KIND,
          "Batch 1 (2026-09-10): the two queued state rows plus the eight largest states by population; done-already states "
          "are replaced by the next largest. Generator: scripts/build_medicaid_state_eligibility_manual_manifests.py."),
    "2": (BUILDERS_BATCH2, STATIC_ROWS_BATCH2, NAMES_BATCH2, SOURCE_KIND_BATCH2,
          "Batch 2 (2026-09-10): the next ten states by population (WA, AZ, TN, MA, IN, MD, MO, WI, CO, MN); none was already covered "
          "by a combined manual, so no replacement was pulled. CA and OH retried once each. Generator: "
          "scripts/build_medicaid_state_eligibility_manual_manifests.py --batch 2."),
}
BATCH1_RETRY_DETAILS = {
    "us-ca": "HTTP 403 Incapsula interstitial (incident id 648000110658208525-192905496909841125) for both requests.",
    "us-oh": ("codes.ohio.gov TCP connect timeout (curl 28 at 20 s) for both requests; medicaid.ohio.gov MEPL index still 404 (5,279 bytes) "
              "to the plain request but returned HTTP 200 (399,073 bytes) to chrome120 impersonation, so the procedure-letter family is "
              "reachable with the existing browser_impersonation option while the OAC 5160:1 rules on codes.ohio.gov remain unreachable; "
              "not ingested in batch 2 (the rules are the eligibility manual; the letters alone are a separate family)."),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batch", choices=["1", "2", "all"], default="all",
                        help="which batch's builders and static rows to (re)build; rows of the other batch are left untouched")
    parser.add_argument("--only", action="append", default=[], metavar="JURISDICTION",
                        help="restrict live builders to these jurisdictions (static rows of the batch are still applied)")
    args = parser.parse_args()
    batches = ["1", "2"] if args.batch == "all" else [args.batch]
    queue = yaml.safe_load(QUEUE.read_text())
    rows = {s["jurisdiction"]: s for s in queue["states"]}
    summary: dict[str, Any] = {}
    for batch in batches:
        builders, static_rows, names, source_kind, batch_note = BATCHES[batch]
        for jur, build in builders.items():
            if args.only and jur not in args.only:
                continue
            docs, info = build()
            if not docs:
                print(f"{jur}: no documents found; index layout changed?", file=sys.stderr)
                return 1
            paths = [d["citation_path"] for d in docs]
            if len(set(paths)) != len(paths):
                dupes = sorted({p for p in paths if paths.count(p) > 1})
                print(f"{jur}: duplicate citation paths {dupes}", file=sys.stderr)
                return 1
            stem = f"{jur}-medicaid-eligibility-manual"
            (ROOT / "manifests" / f"{stem}.yaml").write_text(
                yaml.safe_dump({"version": VERSION, "documents": docs}, sort_keys=False, allow_unicode=True, width=120))
            found = sum(f["found"] for f in info["families"].values())
            taken = sum(f["taken"] for f in info["families"].values())
            summary[jur] = {"documents": len(docs), **info}
            row = rows.get(jur) or {"jurisdiction": jur, "name": names[jur], "lead_counts": {}, "candidate_sources": []}
            row.update({
                "name": names[jur], "queue_status": "agent_ready", "source_kind": source_kind[jur],
                "primary_source_url": docs[0]["source_url"], "target_manifest": f"manifests/{stem}.yaml",
                "target_scope": {"jurisdiction": jur, "document_class": "manual", "version": VERSION},
                "index_url": info["index_url"], "index_document_count": found, "taken_count": taken,
                "index_families": info["families"],
                "notes": (f"Batch {batch} (2026-09-10): {len(docs)} manual documents taken from the publisher's own index ({found} documents inventoried "
                          f"across {len(info['families'])} families; {taken} taken). Extraction proven with the official-documents extractor; "
                          f"see docs/ingest-runs/2026-09-10-medicaid-state-eligibility-manuals-batch-{batch}.md."),
            })
            rows[jur] = row
            print(f"{jur}: {len(docs)} documents; index families {info['families']}")
        for jur, static in static_rows.items():
            row = rows.get(jur) or {"jurisdiction": jur, "name": names.get(jur, "Federal"), "lead_counts": {}, "candidate_sources": []}
            row.update(static)
            rows[jur] = row
        if batch == "2":
            for jur, detail in BATCH1_RETRY_DETAILS.items():
                note = RETRY_NOTE.format(detail=detail)
                if jur in rows and note not in rows[jur]["notes"]:
                    rows[jur]["notes"] = rows[jur]["notes"] + note
        notes = queue.setdefault("policy", {}).setdefault("notes", [])
        if batch_note not in notes:
            notes.append(batch_note)
    queue["states"] = [rows[j] for j in sorted(rows, key=lambda j: (j != "us", j))]
    queue["status_counts"] = {}
    for s in queue["states"]:
        queue["status_counts"][s["queue_status"]] = queue["status_counts"].get(s["queue_status"], 0) + 1
    queue["queue_status"] = "in_progress"
    QUEUE.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(json.dumps(summary, indent=1))
    print(f"queue {queue['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
