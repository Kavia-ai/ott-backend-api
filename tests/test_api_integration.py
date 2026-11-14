"""Exercise the HTTP flows against an isolated temporary database."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class ApiIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = os.environ.copy()
        database_path = (Path(self.temp_dir.name) / "test.db").as_posix()
        self.env.update(
            DATABASE_URL=f"sqlite+aiosqlite:///{database_path}",
            JWT_SECRET_KEY="isolated-integration-test-secret-not-for-production",
            CORS_ORIGINS="http://localhost:5173",
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.process = None
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(self.stop_server)
        self.start_server()

    def start_server(self):
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=BACKEND_ROOT,
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            if self.process.poll() is not None:
                self.fail("Test API exited before becoming ready")
            try:
                if self.request("GET", "/health")[0] == 200:
                    return
            except (URLError, OSError):
                time.sleep(0.1)
        self.fail("Test API did not become ready")

    def stop_server(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
            self.process = None

    def request(self, method, path, payload=None, token=None):
        headers = {}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            with error:
                return error.code, json.load(error)

    def test_auth_and_pricing_persist_across_restart(self):
        prefix = "/api/v1"
        credentials = {"email": "viewer@example.com", "password": "password123"}
        code, plans = self.request("GET", prefix + "/plans")
        self.assertEqual(code, 200)
        self.assertIn("basic", [plan["slug"] for plan in plans])
        self.assertEqual(self.request("GET", prefix + "/me")[0], 401)
        self.assertEqual(
            self.request("POST", prefix + "/auth/register", {**credentials, "display_name": "   "})[0],
            422,
        )
        code, result = self.request(
            "POST", prefix + "/auth/register", {**credentials, "display_name": " Viewer "}
        )
        self.assertEqual(code, 201)
        token = result["access_token"]
        self.assertEqual(
            self.request("POST", prefix + "/auth/register", {**credentials, "display_name": "Other"})[0],
            409,
        )
        self.assertEqual(
            self.request("POST", prefix + "/auth/login", {**credentials, "password": "wrongpassword"})[0],
            401,
        )
        code, profile = self.request("GET", prefix + "/me", token=token)
        self.assertEqual(code, 200)
        self.assertEqual(profile["display_name"], "Viewer")
        self.assertIsNone(profile["subscription"])
        code, subscription = self.request(
            "POST", prefix + "/subscriptions/checkout",
            {"plan_slug": "basic", "start_trial": True}, token,
        )
        self.assertEqual(code, 200)
        self.assertTrue(subscription["is_trial"])
        self.stop_server()
        self.start_server()
        code, result = self.request("POST", prefix + "/auth/login", credentials)
        self.assertEqual(code, 200)
        code, profile = self.request("GET", prefix + "/me", token=result["access_token"])
        self.assertEqual(code, 200)
        self.assertEqual(profile["email"], credentials["email"])
        self.assertEqual(profile["subscription"]["plan_slug"], "basic")
        self.assertTrue(profile["subscription"]["is_trial"])


if __name__ == "__main__":
    unittest.main()
