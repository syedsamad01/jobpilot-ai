import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "jobpilot.db")

def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with _connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS saved_jobs (
            id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT, url TEXT,
            source TEXT, description TEXT, salary TEXT, job_type TEXT, status TEXT DEFAULT 'Saved'
        )""")

def save_job(job):
    with _connect() as con:
        con.execute("""INSERT OR IGNORE INTO saved_jobs
            (id,title,company,location,url,source,description,salary,job_type,status)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (job.get("id"), job.get("title"), job.get("company"), job.get("location"),
             job.get("url"), job.get("source"), job.get("description"), job.get("salary"),
             job.get("job_type"), "Saved"))

def get_saved_jobs():
    with _connect() as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute("SELECT * FROM saved_jobs ORDER BY rowid DESC").fetchall()]

def update_status(job_id, status):
    with _connect() as con:
        con.execute("UPDATE saved_jobs SET status=? WHERE id=?", (status, job_id))

def delete_saved_job(job_id):
    with _connect() as con:
        con.execute("DELETE FROM saved_jobs WHERE id=?", (job_id,))
