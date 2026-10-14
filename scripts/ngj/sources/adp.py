"""ADP Workforce Now public career-center adapter.

A company is configured by its career center,
``https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=<uuid>``,
and fetched from the same tenant's requisition list, which needs no key::

    GET https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions
        ?cid=<uuid>&$top=20&$skip=N

Results are newest first with ``meta.totalNumber``. The server caps pages at 20
whatever ``$top`` says, and ``$skip`` is effectively 1-based (``startSequence``
is 1), so stepping by the rows returned repeats one row at the first page
boundary; postings are de-duplicated by their public id. A page that only repeats
known postings ends paging, so a server that ignored ``$skip`` could not loop
forever (a page of rows without public ids does not end it).

The public id is the ``ExternalJobID`` custom field (not ``itemID``), and the
posting page is ``<career center>&jobId=<ExternalJobID>``. ``jobId`` is only
unique within a company, which is why ``contracts.canonical_url`` keeps ``cid``
on this host. Internal ids (item, client requisition) are never copied.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ngj import http as ngj_http
from ngj.models import KIND_CONFIG, SourceError, SourceResult
from ngj.settings import DEFAULT_HTTP_TIMEOUT, Settings

SOURCE = "adp"
SOURCE_LABEL = "ADP"
# The server never returns more than 20 rows per page.
PAGE_SIZE = 20
REQUISITIONS_URL = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions"

_CAREERS_RE = re.compile(
    r"^https://workforcenow\.adp\.com/mascsr/default/mdf/recruitment/recruitment\.html"
    r"\?cid=([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$"
)


def careers_cid(url: str) -> str | None:
    """The tenant ``cid`` of a configured career-center URL, else None."""
    match = _CAREERS_RE.match((url or "").strip())
    return match.group(1) if match else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _public_id(raw: Mapping[str, Any]) -> str:
    for field in _mapping(raw.get("customFieldGroup")).get("stringFields") or ():
        if _mapping(_mapping(field).get("nameCode")).get("codeValue") == "ExternalJobID":
            return str(_mapping(field).get("stringValue") or "").strip()
    return ""


def _location(raw: Mapping[str, Any]) -> str:
    places: list[str] = []
    for location in raw.get("requisitionLocations") or ():
        location = _mapping(location)
        name = str(_mapping(location.get("nameCode")).get("shortName") or "").strip()
        if not name:
            address = _mapping(location.get("address"))
            region = _mapping(address.get("countrySubdivisionLevel1")).get("codeValue")
            name = ", ".join(str(part) for part in (address.get("cityName"), region) if part)
        if name and name not in places:
            places.append(name)
    return "; ".join(places)


def _to_job(company_name: str, careers: str, public_id: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "company": company_name,
        "title": (raw.get("requisitionTitle") or "").strip(),
        "location": _location(raw),
        "url": f"{careers}&jobId={public_id}",
        "posted_at": raw.get("postDate") or "",
        "source": SOURCE_LABEL,
        "description": "",  # Not in the list payload.
    }


def _page_parser(company_name: str, careers: str, totals: list[int]) -> Callable[[Any], SourceResult | None]:
    def parse(data: Any) -> SourceResult | None:
        rows = data.get("jobRequisitions") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return None
        total = _mapping(data.get("meta")).get("totalNumber")
        totals.append(total if isinstance(total, int) and not isinstance(total, bool) else 0)
        jobs = []
        for raw in rows:
            public_id = _public_id(raw) if isinstance(raw, Mapping) else ""
            # A requisition without a public id has no posting page, so it is skipped.
            if public_id:
                jobs.append(_to_job(company_name, careers, public_id, raw))
        return SourceResult(jobs=tuple(jobs), raw_count=len(rows))

    return parse


def fetch_adp_jobs(
    company_name: str,
    url: str,
    *,
    max_jobs: int = 1000,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> SourceResult:
    """Fetch one career center, newest first, up to ``max_jobs`` postings.

    A timeout or network error returns no jobs, so the retry pass cannot
    publish the company twice.
    """
    cid = careers_cid(url)
    if cid is None:
        message = f"not an ADP Workforce Now career-center URL: {url}"
        return SourceResult(errors=(SourceError(company_name, SOURCE, KIND_CONFIG, None, message),))

    # Built from the lowercased cid, so a tenant configured in another case keeps
    # the same job URLs (canonical_url preserves query-value case).
    careers = f"https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid={cid.lower()}"
    jobs: dict[str, dict[str, Any]] = {}
    totals: list[int] = []
    parse = _page_parser(company_name, careers, totals)
    skip = 0
    for _ in range(-(-max_jobs // PAGE_SIZE) + 1):
        page = ngj_http.fetch_json_with_retry(
            company_name, SOURCE, SOURCE_LABEL, f"{REQUISITIONS_URL}?cid={cid}&$top={PAGE_SIZE}&$skip={skip}", parse,
            timeout=timeout)
        if page.errors:
            if any(error.kind in ngj_http.TRANSIENT_KINDS for error in page.errors):
                return SourceResult(errors=page.errors)
            return SourceResult(jobs=tuple(jobs.values()), errors=page.errors, raw_count=len(jobs))
        new = {job["url"]: job for job in page.jobs if job["url"] not in jobs}
        jobs = {**jobs, **dict(list(new.items())[: max_jobs - len(jobs)])}
        skip += page.raw_count
        reported_total = totals[-1] if totals else 0
        # A page that only repeats known postings ends paging (a server ignoring
        # $skip); a page whose rows have no public id does not.
        repeated_only = bool(page.jobs) and not new
        if (not page.raw_count or repeated_only or len(jobs) >= max_jobs
                or 0 < reported_total <= len(jobs)):
            break
    return SourceResult(jobs=tuple(jobs.values()), raw_count=len(jobs))


def fetch_all_adp_jobs(companies: Sequence[dict[str, Any]], settings: Settings) -> SourceResult:
    """Fetch every configured ADP Workforce Now career center in parallel."""

    def fetch(company: dict[str, Any], timeout: int) -> SourceResult:
        return fetch_adp_jobs(company["name"], company["url"], max_jobs=settings.adp_max_jobs_per_company,
                              timeout=timeout)

    first_pass = ngj_http.fan_out(
        list(companies),
        lambda c: fetch(c, settings.http_timeout),
        max_workers=min(settings.adp_max_workers, max(1, len(companies))),
        source=SOURCE,
        describe=lambda c: c.get("name", "<unknown>"),
        label=SOURCE_LABEL,
    )
    return ngj_http.retry_transient_failures(
        list(companies),
        first_pass,
        lambda c: fetch(c, settings.http_timeout * 2),
        describe=lambda c: c.get("name", "<unknown>"),
    )
