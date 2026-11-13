# Test Task 2: Web Service, Database & Video Upload + Preview

An extension of the browser automation recorder featuring a lightweight Flask web service, an SQLite database layer, client functions for automated video uploads, and on-screen playback preview using Playwright.

---

## Deliverables & Project Structure

```text
task2/
├── web_service.py         # Flask REST API and SQLite database layer
├── video_client.py        # Client functions: UploadVideo and GetVideoURL
├── capture_video.py       # Main entry point with --server, --view-seconds, and --video-dir
├── qscript.py             # Automation recorder module (clean Playwright interaction)
├── input.csv              # Input dataset (UTF-8, delimiter ';', quotechar '"')
├── requirements.txt       # Dependencies: flask, requests, playwright
├── .gitignore             # Standard Python / SQLite / OS ignore rules
├── README.md              # Documentation and execution guide
├── tests/                 # Isolated test suite
│   ├── test_service.py    # Schema, upload, query, upsert, and media delivery tests
│   └── test_live_client.py# Live server thread integration tests on dynamic ports
└── video/                 # Local video storage from recorder
```

---

## Requirements & Constraints

- **Python**: 3.9+
- **Allowed Dependencies**: strictly `flask`, `requests`, `playwright` (in `requirements.txt`).
- **Database**: SQLite (`videos.db`) managed via Python stdlib `sqlite3`.
- **Browser Preview**: Playwright (sync API) + Chromium (`headless=False`).

---

## Quick Start

### 1. Environment Setup

```bash
# Navigate to task directory
cd task2

# Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

---

## Running the Web Service

Start the server:
```bash
python web_service.py
```

- Binds to `0.0.0.0:8000` by default.
- Host and port can be configured via environment variables `FLASK_HOST` and `FLASK_PORT`.
- Automatically initializes `videos.db` and the `uploads/` directory on server startup.

### Web Service Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Accepts multipart form with `file` and `company_name`. Stores file in `uploads/`, records entry in database, and returns JSON with `company_name` and `video_url`. Supports upsert (no duplicate rows). |
| `GET` | `/get_video_url?company_name=<name>` | Looks up record by company name. Returns HTTP 200 JSON with `video_url`, or HTTP 404 if not found. |
| `GET` | `/media/<filename>` | Serves the uploaded video file directly with `video/webm` MIME type for browser playback. |
| `GET` | `/videos` | (Optional) Lists all stored video records in JSON format. |

---

## Running the Recorder with Upload & Preview

### Mode A: Record + Upload + Preview (Full Pipeline)

With the web service running:
```bash
# Preview each video for 5 seconds after upload
python capture_video.py --server http://127.0.0.1:8000 --view-seconds 5

# Interactive preview: keeps the browser open until Enter is pressed
python capture_video.py --server http://127.0.0.1:8000 --view-seconds 0
```

### Mode B: Standalone Recorder (No Server)

When `--server` is omitted, the script runs the recording loop as in Task 1 without invoking the HTTP client (requests is imported lazily):
```bash
python capture_video.py
```

---

## Architecture Notes

1. **Clean Browser Automation (`qscript.py`)**:
   - Strictly implements the visual requirements from the specification: custom SVG cursor, yellow highlight circle, click ripple wave, and floating callout notifications.
   - Removed artificial DOM overlays and polling loops in favor of native Playwright interaction, ensuring long-term resilience against search engine frontend updates.
   - Accurate callout timing matching specification (2.0s fade transitions).

2. **Database Architecture (`videos.db`)**:
   - Uses Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and busy timeouts (`PRAGMA busy_timeout=5000;`) to safely handle concurrent read/write operations without database lock errors.
   - Per-request database connections are opened via `flask.g` and closed during request teardown (`@app.teardown_appcontext`).
   - Clean module scope: importing `web_service` never modifies disk state; initialization occurs only on explicit server run or test setup.

3. **CSV Resilience & Encoding**:
   - `capture_video.py` utilizes `utf-8-sig` encoding, transparently supporting standard UTF-8 as well as Windows/Excel UTF-8 files containing Byte Order Marks (`\ufeff`).

4. **Isolated Test Suite (`tests/`)**:
   - Tests execute against ephemeral temporary directories (`tempfile.TemporaryDirectory`) and bind to OS-allocated dynamic ports (`port=0`), guaranteeing zero project directory pollution and zero port collisions with running servers.

---

## Running Automated Tests

To run the test suite:
```bash
python -m unittest discover -s tests
```
