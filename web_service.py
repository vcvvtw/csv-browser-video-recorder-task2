import os
import re
import sqlite3
from flask import Flask, request, jsonify, send_from_directory, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "videos.db")

app = Flask(__name__)


def safe_company_filename(company_name: str, original_filename: str = "") -> str:
    ext = os.path.splitext(original_filename)[1] if original_filename else ".webm"
    if not ext:
        ext = ".webm"
    safe = re.sub(r'[^\w\d\-_]', '_', company_name.strip()).strip('_')
    if not safe:
        safe = "video"
    return f"{safe}{ext}"


def get_db():
    if "db" not in g:
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH, timeout=10.0)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL;")
        g.db.execute("PRAGMA busy_timeout=5000;")
        g.db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL UNIQUE,
                file_path TEXT NOT NULL,
                video_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL UNIQUE,
                file_path TEXT NOT NULL,
                video_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
    finally:
        conn.close()


@app.route("/upload", methods=["POST"])
def upload_video():
    if "file" not in request.files:
        return jsonify({"error": "Missing 'file' field in multipart form"}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return jsonify({"error": "Empty filename provided"}), 400

    company_name = request.form.get("company_name", "").strip()
    if not company_name:
        return jsonify({"error": "Missing 'company_name' parameter"}), 400

    filename = safe_company_filename(company_name, uploaded_file.filename)
    dest_path = os.path.join(UPLOADS_DIR, filename)
    uploaded_file.save(dest_path)

    abs_file_path = os.path.abspath(dest_path)
    video_url = f"{request.host_url.rstrip('/')}/media/{filename}"

    db = get_db()
    db.execute("""
        INSERT INTO videos (company_name, file_path, video_url, created_at, updated_at)
        VALUES (?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(company_name) DO UPDATE SET
            file_path = excluded.file_path,
            video_url = excluded.video_url,
            updated_at = datetime('now');
    """, (company_name, abs_file_path, video_url))
    db.commit()

    return jsonify({
        "company_name": company_name,
        "video_url": video_url
    }), 200


@app.route("/get_video_url", methods=["GET"])
def get_video_url():
    company_name = request.args.get("company_name", "").strip()
    if not company_name:
        return jsonify({"error": "Missing 'company_name' query parameter"}), 400

    db = get_db()
    row = db.execute(
        "SELECT company_name, video_url FROM videos WHERE company_name = ?",
        (company_name,)
    ).fetchone()

    if row is None:
        return jsonify({"error": f"No video found for company '{company_name}'"}), 404

    return jsonify({
        "company_name": row["company_name"],
        "video_url": row["video_url"]
    }), 200


@app.route("/media/<path:filename>", methods=["GET"])
def serve_media(filename):
    return send_from_directory(UPLOADS_DIR, filename, mimetype="video/webm")


@app.route("/videos", methods=["GET"])
def list_videos():
    db = get_db()
    rows = db.execute(
        "SELECT id, company_name, file_path, video_url, created_at, updated_at FROM videos ORDER BY id ASC"
    ).fetchall()
    return jsonify([dict(row) for row in rows]), 200


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 8000))
    init_db()
    app.run(host=host, port=port, threaded=True)
