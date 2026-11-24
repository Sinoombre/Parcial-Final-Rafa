import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

FAILURE_FLAG = Path("/var/lib/caribeshop/unhealthy")
HOSTNAME = socket.gethostname()
ZONE = "unknown"
IMDS_URL = "http://169.254.169.254/metadata"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# IMDS debe consultarse directamente. Ninguna petición reenvía el token
# de Key Vault a un destino indicado por una redirección.
AZURE_HTTP = build_opener(ProxyHandler({}), NoRedirect())


def get_zone():
    request = Request(
        f"{IMDS_URL}/instance/compute/zone?api-version=2021-02-01&format=text",
        headers={"Metadata": "true"},
    )
    try:
        with AZURE_HTTP.open(request, timeout=1) as response:
            return response.read().decode("utf-8").strip() or "unknown"
    except (OSError, UnicodeError):
        return "unknown"


def check_secret():
    vault_uri = os.environ["KEY_VAULT_URI"].rstrip("/")
    secret_name = os.environ["KEY_VAULT_SECRET_NAME"]
    query = urlencode({"api-version": "2018-02-01", "resource": "https://vault.azure.net"})
    token_request = Request(
        f"{IMDS_URL}/identity/oauth2/token?{query}",
        headers={"Metadata": "true"},
    )
    with AZURE_HTTP.open(token_request, timeout=2) as response:
        token = json.load(response)["access_token"]
    if not isinstance(token, str) or not token:
        return False

    secret_request = Request(
        f"{vault_uri}/secrets/{secret_name}?api-version=7.4",
        headers={"Authorization": f"Bearer {token}"},
    )
    with AZURE_HTTP.open(secret_request, timeout=3) as response:
        # Solo comprobamos que el valor se recibió; no se devuelve ni registra.
        return isinstance(json.load(response)["value"], str)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            healthy = not FAILURE_FLAG.exists()
            status = 200 if healthy else 503
            payload = {"status": "ok" if healthy else "unhealthy"}
        elif path == "/":
            status = 200
            payload = {
                "service": "CaribeShop",
                "message": "Demo HTTP activa",
                "hostname": HOSTNAME,
                "zone": ZONE,
            }
        elif path == "/secret-check" and self.client_address[0] == "127.0.0.1":
            try:
                readable = check_secret()
            except (OSError, ValueError, KeyError, TypeError):
                # No enviar al cliente ni a los logs detalles de IMDS o Key Vault.
                readable = False
            status = 200 if readable else 503
            payload = {"secret_read": readable}
        else:
            status = 404
            payload = {"error": "not found"}

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Evita que cada sondeo de salud genere un log.
        if urlsplit(self.path).path != "/health":
            super().log_message(format, *args)


class CaribeShopServer(ThreadingHTTPServer):
    request_queue_size = 128


if __name__ == "__main__":
    ZONE = get_zone()
    CaribeShopServer(("0.0.0.0", 80), Handler).serve_forever()
