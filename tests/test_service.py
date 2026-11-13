import os
import sys
import tempfile
import unittest
import sqlite3
import gc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import web_service


class TestWebService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.orig_db_path = web_service.DB_PATH
        cls.orig_uploads_dir = web_service.UPLOADS_DIR

        web_service.DB_PATH = os.path.join(cls.temp_dir.name, "test_videos.db")
        web_service.UPLOADS_DIR = os.path.join(cls.temp_dir.name, "test_uploads")
        web_service.init_db()

        web_service.app.config["TESTING"] = True
        cls.client = web_service.app.test_client()

    @classmethod
    def tearDownClass(cls):
        web_service.DB_PATH = cls.orig_db_path
        web_service.UPLOADS_DIR = cls.orig_uploads_dir
        gc.collect()
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_db_schema(self):
        conn = sqlite3.connect(web_service.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos';")
        self.assertIsNotNone(cursor.fetchone(), "Table 'videos' should exist")

        cursor.execute("PRAGMA table_info(videos);")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        self.assertIn("id", columns)
        self.assertIn("company_name", columns)
        self.assertIn("file_path", columns)
        self.assertIn("video_url", columns)
        self.assertIn("created_at", columns)
        self.assertIn("updated_at", columns)
        conn.close()

    def test_02_upload_and_get(self):
        test_video_content = b"RIFF....WEBM-FAKE-VIDEO-BYTES"
        data = {
            "company_name": "ACME GmbH",
            "file": (tempfile.SpooledTemporaryFile(), "sample.webm")
        }
        data["file"][0].write(test_video_content)
        data["file"][0].seek(0)

        # POST /upload
        res = self.client.post("/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertEqual(res_json["company_name"], "ACME GmbH")
        self.assertTrue(res_json["video_url"].endswith("/media/ACME_GmbH.webm"))

        # Verify isolated DB row
        conn = sqlite3.connect(web_service.DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM videos WHERE company_name = 'ACME GmbH'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["company_name"], "ACME GmbH")
        self.assertTrue(os.path.exists(row["file_path"]))
        self.assertEqual(row["video_url"], res_json["video_url"])
        conn.close()

        # GET /get_video_url (success)
        res_get = self.client.get("/get_video_url?company_name=ACME%20GmbH")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.get_json()["video_url"], res_json["video_url"])

        # GET /get_video_url (not found)
        res_404 = self.client.get("/get_video_url?company_name=NonExistentCorp")
        self.assertEqual(res_404.status_code, 404)

        # GET /media/<filename>
        res_media = self.client.get("/media/ACME_GmbH.webm")
        self.assertEqual(res_media.status_code, 200)
        self.assertEqual(res_media.data, test_video_content)
        res_media.close()

        # GET /videos list
        res_list = self.client.get("/videos")
        self.assertEqual(res_list.status_code, 200)
        videos = res_list.get_json()
        self.assertTrue(len(videos) >= 1)
        self.assertTrue(any(v["company_name"] == "ACME GmbH" for v in videos))

    def test_03_upsert_no_duplicates(self):
        new_content = b"UPDATED-WEBM-BYTES"
        data = {
            "company_name": "ACME GmbH",
            "file": (tempfile.SpooledTemporaryFile(), "sample2.webm")
        }
        data["file"][0].write(new_content)
        data["file"][0].seek(0)

        # Re-upload same company
        res = self.client.post("/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)

        conn = sqlite3.connect(web_service.DB_PATH)
        rows = conn.execute("SELECT * FROM videos WHERE company_name = 'ACME GmbH'").fetchall()
        self.assertEqual(len(rows), 1, "Upsert should maintain exactly 1 row per company_name")
        conn.close()


if __name__ == "__main__":
    unittest.main()
