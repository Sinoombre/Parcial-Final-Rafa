#!/usr/bin/env python3
"""
p2_analisis.py - Metricas de P2: tiempo hasta dejar de recibir trafico, % de error
y tiempo hasta recuperar capacidad.

Entradas:
  --locust   <prefijo>_stats_history.csv generado por Locust (--csv)
  --monitor  CSV de p2_monitor.py
  --inicio   hora UTC de la falla (columna utc de evidencias/p2-fallas/eventos.csv)
  --host     hostname de la instancia afectada
  --duracion segundos de la ventana a analizar desde el inicio (por defecto 600)

Ejemplo:
  python3 pruebas/p2_analisis.py \
    --locust evidencias/p2-fallas/logica_stats_history.csv \
    --monitor evidencias/p2-fallas/monitor_logica.csv \
    --inicio 2026-11-24T15:02:10.123Z --host vmsscaribeshop000001 \
    --salida evidencias/graficos/p2_logica.png

Dependencias: pandas (y matplotlib si se quiere el grafico)
"""
import argparse
from datetime import datetime, timedelta, timezone

import pandas as pd


def parse_utc(texto):
    return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone(timezone.utc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locust", required=True)
    ap.add_argument("--monitor", required=True)
    ap.add_argument("--inicio", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--duracion", type=int, default=600)
    ap.add_argument("--salida", help="PNG del grafico (opcional)")
    a = ap.parse_args()

    t0 = parse_utc(a.inicio)
    t1 = t0 + timedelta(seconds=a.duracion)

    # ---- % de error segun Locust (contadores acumulados por segundo)
    L = pd.read_csv(a.locust)
    L = L[L["Name"] == "Aggregated"].copy()
    L["t"] = pd.to_datetime(L["Timestamp"], unit="s", utc=True)
    L["req"] = pd.to_numeric(L["Total Request Count"], errors="coerce")
    L["fail"] = pd.to_numeric(L["Total Failure Count"], errors="coerce")
    antes = L[L["t"] <= t0].iloc[-1] if (L["t"] <= t0).any() else L.iloc[0]
    dentro = L[L["t"] <= t1]
    fin = dentro.iloc[-1]
    peticiones = int(fin["req"] - antes["req"])
    fallos = int(fin["fail"] - antes["fail"])
    pct = 100 * fallos / peticiones if peticiones else float("nan")

    # ---- Sondeo propio (monitor)
    M = pd.read_csv(a.monitor)
    M["t"] = pd.to_datetime(M["utc"], utc=True)
    M["ok"] = M["status"] == 200
    W = M[(M["t"] >= t0) & (M["t"] <= t1)]
    hosts_previos = set(M[(M["t"] < t0) & M["ok"]]["host"])

    afectado = W[(W["host"] == a.host) & W["ok"]]
    t_ultimo = afectado["t"].max() if len(afectado) else None
    sin_trafico_s = (t_ultimo - t0).total_seconds() if t_ultimo is not None else 0.0

    nuevos = W[W["ok"] & ~W["host"].isin(hosts_previos)]
    t_nueva = nuevos["t"].min() if len(nuevos) else None
    recuperacion_s = (t_nueva - t0).total_seconds() if t_nueva is not None else None

    errores_mon = int((~W["ok"]).sum())
    pct_mon = 100 * errores_mon / len(W) if len(W) else float("nan")

    print("=" * 60)
    print(f"Ventana: {t0.isoformat()}  ->  {t1.isoformat()}  ({a.duracion} s)")
    print(f"Instancia afectada: {a.host}")
    print("-" * 60)
    print("LOCUST (contadores acumulados):")
    print(f"  Peticiones en la ventana : {peticiones}")
    print(f"  Fallos en la ventana     : {fallos}")
    print(f"  % de error               : {pct:.2f} %")
    print("MONITOR (sondeo propio cada 0.25 s):")
    print(f"  Sondeos / errores        : {len(W)} / {errores_mon}  ({pct_mon:.2f} %)")
    print(f"  Ultima respuesta OK de la instancia afectada: "
          f"{'+%.1f s' % sin_trafico_s if t_ultimo is not None else 'no respondio en la ventana'}")
    print("  (falla logica: ese valor = tiempo hasta dejar de recibir trafico)")
    if recuperacion_s is not None:
        print(f"  Primera respuesta de una instancia NUEVA: +{recuperacion_s:.1f} s  ({t_nueva.isoformat()})")
    else:
        print("  No aparecio instancia nueva en la ventana (aumenta --duracion).")
    print("=" * 60)

    if a.salida:
        import matplotlib.pyplot as plt
        v = L[(L["t"] >= t0 - timedelta(minutes=2)) & (L["t"] <= t1)].copy()
        v["rps"] = pd.to_numeric(v["Requests/s"], errors="coerce")
        v["fps"] = pd.to_numeric(v["Failures/s"], errors="coerce")
        fig, ax = plt.subplots(figsize=(11, 4.5))
        ax.plot(v["t"], v["rps"], label="RPS", color="tab:blue")
        ax.plot(v["t"], v["fps"], label="Fallos/s", color="tab:red")
        ax.axvline(t0, color="black", ls="--", label="Inicio de la falla")
        if t_nueva is not None:
            ax.axvline(t_nueva, color="green", ls=":", label="Instancia nueva responde")
        ax.set_xlabel("Hora (UTC)")
        ax.set_ylabel("Peticiones por segundo")
        ax.set_title(f"P2 - {a.host}: error {pct:.2f} % en la ventana")
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(a.salida, dpi=150)
        print(f"Grafico guardado en {a.salida}")


if __name__ == "__main__":
    main()
