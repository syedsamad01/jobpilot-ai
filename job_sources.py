import os
import requests
import hashlib
from dotenv import load_dotenv

load_dotenv()
TIMEOUT = 18

COUNTRY_NAMES = {
    "us": "United States", "gb": "United Kingdom", "ca": "Canada", "au": "Australia",
    "in": "India", "ae": "United Arab Emirates", "de": "Germany", "fr": "France",
    "nl": "Netherlands", "ie": "Ireland", "sg": "Singapore", "nz": "New Zealand",
    "za": "South Africa", "es": "Spain", "it": "Italy", "pl": "Poland",
    "at": "Austria", "be": "Belgium", "br": "Brazil", "mx": "Mexico", "jp": "Japan",
    "se": "Sweden", "ch": "Switzerland", "pt": "Portugal", "cz": "Czechia",
    "dk": "Denmark", "no": "Norway"
}

def make_job(source, title, company, location, url, description="", salary="", job_type=""):
    title = (title or "Untitled role").strip()
    company = (company or "Company not listed").strip()
    url = url or ""
    raw = f"{source}|{url}|{title}|{company}"
    return {
        "id": hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:14],
        "source": source, "title": title, "company": company,
        "location": location or "Location not listed", "url": url,
        "description": (description or "").strip(), "salary": salary or "",
        "job_type": job_type or ""
    }

def search_adzuna(query, country, location="", limit=20):
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return [], "Adzuna skipped: add ADZUNA_APP_ID and ADZUNA_APP_KEY to .env."
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {"app_id": app_id, "app_key": app_key, "results_per_page": min(limit, 50),
              "what": query, "content-type": "application/json"}
    if location:
        params["where"] = location
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        results = []
        for x in r.json().get("results", []):
            loc = x.get("location", {}).get("display_name", "")
            salary_min, salary_max = x.get("salary_min"), x.get("salary_max")
            salary = f"{salary_min}–{salary_max}" if salary_min and salary_max else ""
            results.append(make_job("Adzuna", x.get("title"), x.get("company", {}).get("display_name"),
                                    loc, x.get("redirect_url"), x.get("description"), salary,
                                    x.get("contract_type", "")))
        return results, f"Adzuna ({country}): {len(results)} jobs."
    except Exception as exc:
        return [], f"Adzuna ({country}) error: {exc}"

def search_jooble(query, country_name="", location="", limit=20):
    key = os.getenv("JOOBLE_API_KEY")
    if not key:
        return [], "Jooble skipped: add JOOBLE_API_KEY to .env."
    url = f"https://jooble.org/api/" + key
    payload = {"keywords": query}
    where = ", ".join(x for x in [location, country_name] if x)
    if where:
        payload["location"] = where
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        results = []
        for x in r.json().get("jobs", [])[:limit]:
            results.append(make_job("Jooble", x.get("title"), x.get("company"), x.get("location"),
                                    x.get("link"), x.get("snippet"), x.get("salary"), x.get("type")))
        return results, f"Jooble ({country_name or 'general'}): {len(results)} jobs."
    except Exception as exc:
        return [], f"Jooble error: {exc}"

def search_arbeitnow(query, limit=20):
    try:
        r = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=TIMEOUT)
        r.raise_for_status()
        terms = [t.lower() for t in query.split() if len(t) > 2]
        results = []
        for x in r.json().get("data", []):
            haystack = " ".join([x.get("title", ""), x.get("description", ""), " ".join(x.get("tags", []))]).lower()
            if terms and not any(term in haystack for term in terms):
                continue
            results.append(make_job("Arbeitnow", x.get("title"), x.get("company_name"), x.get("location"),
                                    x.get("url"), x.get("description"), "", "Remote" if x.get("remote") else ""))
            if len(results) >= limit:
                break
        return results, f"Arbeitnow: {len(results)} matching jobs from its public feed."
    except Exception as exc:
        return [], f"Arbeitnow error: {exc}"

def search_remotive(query, limit=20):
    try:
        r = requests.get("https://remotive.com/api/remote-jobs",
                         params={"search": query, "limit": limit}, timeout=TIMEOUT)
        r.raise_for_status()
        results = []
        for x in r.json().get("jobs", []):
            results.append(make_job("Remotive", x.get("title"), x.get("company_name"),
                                    x.get("candidate_required_location"), x.get("url"),
                                    x.get("description"), x.get("salary"), "Remote"))
        return results, f"Remotive: {len(results)} remote jobs."
    except Exception as exc:
        return [], f"Remotive error: {exc}"

def search_jobs(query, countries, city="", remote_only=False, max_results=40):
    all_jobs, notes = [], []
    if remote_only:
        jobs, note = search_remotive(query, max_results)
        all_jobs.extend(jobs)
        notes.append(note)
    else:
        selected = countries or ["us", "gb", "ca", "au"]
        # Bound API usage per provider while respecting the candidate's selected markets.
        per_country = max(5, min(15, max_results // max(1, len(selected))))
        for code in selected:
            jobs, note = search_adzuna(query, code, city, per_country)
            all_jobs.extend(jobs); notes.append(note)
            jobs, note = search_jooble(query, COUNTRY_NAMES.get(code, code), city, per_country)
            all_jobs.extend(jobs); notes.append(note)
        jobs, note = search_arbeitnow(query, max_results)
        all_jobs.extend(jobs); notes.append(note)
        # Add remote roles as a supplementary source, even when countries are selected.
        jobs, note = search_remotive(query, min(max_results, 20))
        all_jobs.extend(jobs); notes.append(note)

    seen, unique = set(), []
    for job in all_jobs:
        url = (job.get("url") or "").split("?")[0].lower()
        key = url if url else (job["title"].lower(), job["company"].lower(), job["location"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique[:max_results], notes
