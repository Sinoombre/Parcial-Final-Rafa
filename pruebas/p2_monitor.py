#!/usr/bin/env python3
"""
p2_monitor.py - Sondeo continuo del balanceador durante las pruebas P2.

Hace GET a http://<IP_LB>/ cada 0.25 s y guarda en CSV: hora UTC, codigo HTTP,
hostname de la instancia que respondio, zona y latencia. Con eso se mide:
  - cuanto tarda una instancia en dejar de recibir trafico (falla logica)
  - cuando aparece una instancia nueva (recuperacion de capacidad)

Uso (dejarlo corriendo en otra terminal, junto a Locust):
  python3 pruebas/p2_monitor.py --ip <IP_LB> --salida evidencias/p2-fallas/monitor_logica.csv
Detener con Ctrl+C. Solo usa la libreria estandar.
"""
import argparse
import csv
import json
import time
import urllib.request
from datetime import datetime, timezone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--intervalo", type=float, default=0.25)
    ap.add_argument("--timeout", type=float, default=2.0)
    a = ap.parse_args()

    url = f"http://{a.ip}/"
    with open(a.salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["utc", "status", "host", "zona", "latencia_ms"])
        print(f"Sondeando {url} -> {a.salida} (Ctrl+C para detener)")
        try:
            while True:
                t0 = time.time()
                status, host, zona = 0, "", ""
                try:
                    with urllib.request.urlopen(url, timeout=a.timeout) as r:
                        status = r.status
                        data = json.loads(r.read().decode("utf-8"))
                        host, zona = data.get("hostname", ""), data.get("zone", "")
                except urllib.error.HTTPError as e:
                    status = e.code
                except Exception:
                    status = 0  # timeout o conexion rechazada = fallo
                lat = (time.time() - t0) * 1000
                ts = datetime.fromtimestamp(t0, timezone.utc).isoformat(timespec="milliseconds")
                w.writerow([ts, status, host, zona, f"{lat:.0f}"])
                f.flush()
                time.sleep(max(0, a.intervalo - (time.time() - t0)))
        except KeyboardInterrupt:
            print("\nDetenido.")


if __name__ == "__main__":
    main()
