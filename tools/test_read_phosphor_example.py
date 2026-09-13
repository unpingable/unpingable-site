import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).parent.parent / "constellation/examples/read_phosphor.py"
SPEC = importlib.util.spec_from_file_location("read_phosphor", PATH)
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class Response:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, limit: int) -> bytes:
        return self._body[:limit]


class Opener:
    def __init__(self, response: Response):
        self.response = response

    def open(self, request, timeout: int):
        self.request = request
        self.timeout = timeout
        return self.response


class ReaderExample(unittest.TestCase):
    def test_preserves_independent_source_availability(self):
        value = {"schema": MODULE.SCHEMA, "campaigns": [{"locator_token": "aa",
            "inspect": {"availability": "available"}, "history": {"availability": "unavailable", "error_kind": "timeout"},
            "refusals": {"availability": "available"}}]}
        source = MODULE.summarize(value)["campaigns"][0]["sources"]["history"]
        self.assertEqual(source, {"availability": "unavailable", "error_kind": "timeout"})

    def test_refuses_foreign_shape(self):
        with self.assertRaises(ValueError): MODULE.summarize({"schema": "other", "campaigns": []})

    def test_refuses_unavailable_source_without_its_error_kind(self):
        value = {"schema": MODULE.SCHEMA, "campaigns": [{"locator_token": "aa",
            "inspect": {"availability": "available"}, "history": {"availability": "unavailable"},
            "refusals": {"availability": "available"}}]}
        with self.assertRaises(ValueError): MODULE.summarize(value)

    def test_accepts_only_the_exact_literal_loopback_index(self):
        self.assertEqual(MODULE.checked_url("http://127.0.0.1:8417/api/v1/campaigns"),
                         "http://127.0.0.1:8417/api/v1/campaigns")
        for value in ("http://localhost:8417/api/v1/campaigns",
                      "http://127.0.0.1:8418/api/v1/campaigns",
                      "http://127.0.0.1:8417/api/v1/campaigns?next=x",
                      "http://127.0.0.1:8417/api/v1/campaigns/extra",
                      "https://127.0.0.1:8417/api/v1/campaigns"):
            with self.assertRaises(ValueError): MODULE.checked_url(value)

    def test_refuses_http_failure_and_oversize_without_parsing(self):
        url = "http://127.0.0.1:8417/api/v1/campaigns"
        with patch.object(MODULE, "build_opener", return_value=Opener(Response(503, b"error"))):
            with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                MODULE.fetch(url)
        with patch.object(MODULE, "build_opener", return_value=Opener(Response(200, b"x" * (MODULE.MAX_BYTES + 1)))):
            with self.assertRaisesRegex(RuntimeError, "exceeds"):
                MODULE.fetch(url)


if __name__ == "__main__": unittest.main()
