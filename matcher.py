import re

STOPWORDS = set("""
the and for with from that this your you are was were have has had our their they job role
will can not all any into about using use used required preferred skills experience work
""".split())

def tokens(text):
    return [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", (text or "").lower())
            if t not in STOPWORDS and len(t) > 2]

def score_jobs(jobs, cv_text, desired_role, preferences=""):
    cv_tokens = set(tokens(cv_text))
    role_tokens = set(tokens(desired_role))
    preference_tokens = set(tokens(preferences or ""))
    for job in jobs:
        title_tokens = set(tokens(job.get("title", "")))
        job_text = " ".join(str(job.get(k, "")) for k in ["title", "description", "company", "location", "job_type"])
        job_tokens = set(tokens(job_text))
        role_overlap = len(role_tokens & job_tokens) / max(1, len(role_tokens))
        title_overlap = len(role_tokens & title_tokens) / max(1, len(role_tokens))
        cv_overlap = len(cv_tokens & job_tokens) / max(1, min(len(cv_tokens), 40)) if cv_tokens else 0
        pref_overlap = len(preference_tokens & job_tokens) / max(1, len(preference_tokens)) if preference_tokens else 0
        score = round(100 * (0.42 * role_overlap + 0.28 * title_overlap + 0.25 * min(cv_overlap, 1) + 0.05 * pref_overlap))
        job["match_score"] = max(0, min(99, score))
        matched = sorted((role_tokens | preference_tokens | cv_tokens) & job_tokens)
        job["match_reason"] = ("Matched terms: " + ", ".join(matched[:8])) if matched else "Limited text overlap; review the listing manually."
    return jobs
