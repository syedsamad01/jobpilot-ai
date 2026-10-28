# JobPilot AI Plus

CV-first job search and application tracker built with Python, Streamlit, and SQLite.

## Features
- PDF CV upload and text extraction
- Desired role, country, city, remote, experience and visa preference controls
- Multi-source search using Adzuna, Jooble, Arbeitnow and Remotive where available
- Deduplication, heuristic CV match scores, and match explanations
- Sort/filter results and export results to CSV
- Save jobs, track application status, remove saved jobs, and export tracker
- Optional API credentials loaded from `.env`

## Windows installation
Extract this ZIP. Open CMD in the extracted `JobPilotAI-Plus` folder and run:

```bat
py -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
venv\Scripts\python.exe -m streamlit run app.py
```

If `py` is unavailable, install Python from https://www.python.org/downloads/windows/ and select "Add python.exe to PATH" during installation.

## API setup
Edit `.env` with your Adzuna and/or Jooble API credentials. Restart the app after changing keys. Public feeds may work without these keys, subject to provider availability.

## Important limitations
This MVP does not index every job board worldwide. Actual results depend on provider coverage, API access, country support, rate limits and terms. "Worldwide" searches the countries configured in the app, not every country or every vacancy. Match scores are keyword-based estimates, not hiring probabilities. Scanned PDFs require OCR. The app does not automatically apply for jobs. Add authentication, secure hosting and a privacy policy before public deployment.
