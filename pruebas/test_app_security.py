"""Pruebas locales de /secret-check: no requieren Azure ni credenciales."""

import io
import json
import threading
import unittest
from contextlib import redirect_stderr
from http.client import HTTPConnection
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from app import app


class RemoteClientHandler(app.Handler):
    def setup(self):
        super().setup()
        self.client_address = ("192.0.2.10", self.client_address[1])


def get(path, handler=app.Handler):
    with app.CaribeShopServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        client = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        try:
            client.request("GET", path)
            response = client.getresponse()
            return response.status, json.load(response)
        finally:
            client.close()
            server.shutdown()
            thread.join()


class AppSecurityTests(unittest.TestCase):
    def test_server_preserves_load_test_backlog(self):
        self.assertEqual(app.CaribeShopServer.request_queue_size, 128)

    def test_local_read_uses_vm_identity_and_never_returns_the_value(self):
        settings = {
            "KEY_VAULT_URI": "https://caribeshop-test.vault.azure.net/",
            "KEY_VAULT_SECRET_NAME": "caribeshop-demo",
        }
        logs = io.StringIO()
        with (
            patch.dict(app.os.environ, settings),
            patch.object(
                app.AZURE_HTTP,
                "open",
                side_effect=[
                    io.BytesIO(b'{"access_token":"test-token"}'),
                    io.BytesIO(b'{"value":"test-secret"}'),
                ],
            ) as azure_http,
            redirect_stderr(logs),
        ):
            self.assertEqual(get("/secret-check"), (200, {"secret_read": True}))

        metadata, vault = (call.args[0] for call in azure_http.call_args_list)
        self.assertEqual(urlsplit(metadata.full_url).hostname, "169.254.169.254")
        self.assertEqual(metadata.get_header("Metadata"), "true")
        self.assertEqual(parse_qs(urlsplit(metadata.full_url).query)["resource"], ["https://vault.azure.net"])
        self.assertEqual(
            vault.full_url,
            "https://caribeshop-test.vault.azure.net/secrets/caribeshop-demo?api-version=7.4",
        )
        self.assertEqual(vault.get_header("Authorization"), "Bearer test-token")
        self.assertNotIn("test-token", logs.getvalue())
        self.assertNotIn("test-secret", logs.getvalue())

    def test_remote_request_does_not_trigger_a_secret_read(self):
        with patch.object(app, "check_secret") as check, redirect_stderr(io.StringIO()):
            self.assertEqual(get("/secret-check", RemoteClientHandler), (404, {"error": "not found"}))
            check.assert_not_called()

    def test_vault_failure_is_generic_and_does_not_affect_health(self):
        logs = io.StringIO()
        with (
            patch.object(app, "check_secret", side_effect=OSError("internal-error")) as check,
            patch.object(app, "FAILURE_FLAG") as flag,
            redirect_stderr(logs),
        ):
            self.assertEqual(get("/secret-check"), (503, {"secret_read": False}))
            flag.exists.return_value = False
            self.assertEqual(get("/health"), (200, {"status": "ok"}))
            flag.exists.return_value = True
            self.assertEqual(get("/health"), (503, {"status": "unhealthy"}))
            check.assert_called_once_with()
        self.assertNotIn("internal-error", logs.getvalue())
