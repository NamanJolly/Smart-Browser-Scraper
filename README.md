# Smart Scraper — Browser AI Agent

A compact Streamlit app that uses Playwright to capture web pages and an LLM (OpenAI) to extract structured article data (title, URL, image, excerpt). This project is intended as a starter for building AI-assisted web scraping and structured extraction pipelines.

**Status:** Working prototype

**Key features**
- Headless browsing and screenshot capture with Playwright
- LLM-powered extraction with robust fallback HTML parsing
- Pydantic models for validated structured output
- Streamlit UI for quick iterative testing and results display

**Table of Contents**
- Overview
- Requirements
- Installation
- Playwright browser install
- Configuration (.env)
- Running the app
- Usage
- Troubleshooting
- Development notes
- Contributing
- License

## Overview

`smart_scraper` loads a target page in Playwright, captures the DOM and a screenshot, and sends a cleaned HTML snapshot to an LLM for structured extraction. When the LLM output is sparse, a deterministic fallback scans anchor tags for article-like links and merges results to produce a robust article list.

Core files
- `smart_scraper/app.py` — Streamlit frontend
- `smart_scraper/smart_scraper_main.py` — orchestration (Playwright <> LLM)
- `smart_scraper/utils/browser_agent.py` — Playwright helper (async)
- `smart_scraper/utils/llm_extractor.py` — LLM prompt + fallback HTML parsing
- `smart_scraper/schemas/article_schema.py` — Pydantic models

## Requirements
- Python 3.10+ (project tested with Python 3.12)
- A virtual environment (highly recommended)
- An OpenAI API key (or a compatible OpenAI client key)

Requirements file

This repository includes a `requirements.txt` with pinned minimum versions for a reproducible environment. Install dependencies with:

```bash
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```
streamlit>=1.25.0
playwright>=1.40.0
openai>=1.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pandas>=2.0.0
tabulate>=0.9.0
```

## Installation

1. Create and activate a virtual environment

```bash
python -m venv venv
# Windows PowerShell
venv\Scripts\Activate.ps1
# Windows cmd
venv\Scripts\activate.bat
# macOS / Linux
source venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
# or individually
pip install streamlit playwright openai python-dotenv pydantic pandas tabulate
```

3. Install Playwright browser binaries (required)

```bash
# Using the current Python interpreter
python -m playwright install
# Or, to install only chromium
python -m playwright install chromium
```

Note: If you see an error like "Executable doesn't exist" or a Playwright prompt complaining about browser installs, run the above `playwright install` command in the same virtual environment you use to run the app.

## Configuration (.env)

Create a `.env` file in the project root containing your OpenAI API key:

```
OPENAI_API_KEY=sk-...
```

The code uses `python-dotenv` to read this key and instantiate the OpenAI client.

## Running the app

Start the Streamlit app from the project root:

```bash
streamlit run smart_scraper/app.py
```

Open the provided Local URL (default `http://localhost:8501`) in a browser to access the UI.

## Usage

1. Enter a URL into the input field (e.g., `https://www.bbc.com/news`).
2. Edit the extraction instructions if you want to tune what the LLM should look for.
3. Click "Run Scraper". The app will load the page headlessly, show a screenshot, and display a table of extracted articles.

Tips
- Use precise extraction instructions for niche sites.
- If the LLM returns few items, the deterministic anchor fallback helps, but you can tune `max_items` in the extractor.

## Troubleshooting

- Playwright missing browser binary error:

  - Error: "BrowserType.launch: Executable doesn't exist..."
  - Fix: Run `python -m playwright install` in the same environment.

- Import errors in Streamlit: Ensure Streamlit runs with the same `PYTHONPATH` and virtual environment. Start Streamlit from the project root and activate the venv first.

- LLM returns invalid JSON or fails validation: The code attempts to extract JSON blocks from model output and falls back to deterministic anchors. If you need site-specific accuracy, consider increasing `truncate=False` to send more HTML or customizing the prompt in `utils/llm_extractor.py`.

## Development notes

- The core extraction flow is in `utils/llm_extractor.py`. It first asks the LLM for a structured JSON response; if the response is sparse, it scans anchors for article-like paths and merges results.
- Playwright usage is async — `smart_scraper_main.py` orchestrates the async flow using `asyncio.run` from Streamlit.

## Contributing

Contributions are welcome. Suggested directions:
- Add site-specific extraction rules or adapter modules
- Improve image and excerpt scraping heuristics
- Add tests for the extraction logic and model output handling

Please open an issue or PR with a clear description of your changes.

## License

This project is provided as-is. Add a license (e.g., MIT) as needed.

---
If you want, I can also add a `requirements.txt` file, a small `Makefile`/taskfile for common commands, or an interactive `max_articles` UI control in Streamlit. Which would you like next?
