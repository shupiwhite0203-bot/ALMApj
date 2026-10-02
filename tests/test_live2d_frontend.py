from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import urlopen

import mh_live2d_server as overlay


class FrontendTests(unittest.TestCase):
    def test_different_build_names_are_rendered_and_served(self):
        with tempfile.TemporaryDirectory() as directory:
            frontend = Path(directory)
            assets = frontend / "assets"
            assets.mkdir()
            (assets / "main-newbuild.js").write_text("export {};", encoding="utf-8")
            (assets / "main-newbuild.css").write_text("body {}", encoding="utf-8")
            with patch.object(overlay, "OPEN_LLM_FRONTEND", frontend):
                server = ThreadingHTTPServer(("127.0.0.1", 0), overlay.OverlayHandler)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    base = f"http://127.0.0.1:{server.server_port}"
                    with urlopen(base) as response:
                        page = response.read().decode("utf-8")
                    self.assertIn("/openllm-assets/main-newbuild.js", page)
                    self.assertIn("/openllm-assets/main-newbuild.css", page)
                    self.assertNotIn("__ALMA_FRONTEND_", page)
                    with urlopen(base + "/openllm-assets/main-newbuild.js") as response:
                        self.assertEqual(response.read(), b"export {};")
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join()

    def test_missing_or_ambiguous_build_has_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            frontend = Path(directory)
            with self.assertRaisesRegex(ValueError, "frontend-dir"):
                overlay.render_frontend_page(frontend)
            assets = frontend / "assets"
            assets.mkdir()
            for name in ("main-a.js", "main-b.js", "main-a.css"):
                (assets / name).touch()
            with self.assertRaisesRegex(ValueError, "found 2"):
                overlay.render_frontend_page(frontend)


if __name__ == "__main__":
    unittest.main()
