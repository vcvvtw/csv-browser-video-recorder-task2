import os
import sys
import time
import threading
import tempfile
import unittest
import gc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import web_service
from video_client import UploadVideo, GetVideoURL
from werkzeug.serving import make_server


class ServerThread(threading.Thread):
    def __init__(self, app, host="127.0.0.1"):
        super().__init__()
        # Use port 0 so the OS assigns an ephemeral free port dynamically
        self.server = make_server(host, 0, app)
        self.server_port = self.server.server_port
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class TestLiveClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.orig_db_path = web_service.DB_PATH
        cls.orig_uploads_dir = web_service.UPLOADS_DIR

        web_service.DB_PATH = os.path.join(cls.temp_dir.name, "test_live.db")
        web_service.UPLOADS_DIR = os.path.join(cls.temp_dir.name, "test_live_uploads")
        web_service.init_db()

        cls.server_thread = ServerThread(web_service.app, host="127.0.0.1")
        cls.server_thread.start()
        time.sleep(0.2)
        cls.base_url = f"http://127.0.0.1:{cls.server_thread.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server_thread.shutdown()
        web_service.DB_PATH = cls.orig_db_path
        web_service.UPLOADS_DIR = cls.orig_uploads_dir
        gc.collect()
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_upload_and_get_client(self):
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(b"SAMPLE-LIVE-CLIENT-TEST-PAYLOAD")
            temp_video_path = f.name

        try:
            company = "Test Live Corp"
            # 1. UploadVideo
            video_url = UploadVideo(self.base_url, temp_video_path, company)
            self.assertTrue(video_url.startswith(self.base_url))
            self.assertTrue(video_url.endswith(".webm"))

            # 2. GetVideoURL
            retrieved_url = GetVideoURL(self.base_url, company)
            self.assertEqual(retrieved_url, video_url)

        finally:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)


if __name__ == "__main__":
    unittest.main()
