"""
graficos.py - Grafico alineado de P1.3: RPS, p95 e instancias en el tiempo.

Entradas:
  1) El CSV <prefijo>_stats_history.csv que genera Locust con --csv.
  2) Un JSON con la metrica ObservedCapacity del autoscale, exportado con:

     az monitor metrics list `
        --resource <ID_DEL_AUTOSCALE_SETTING> `
        --metric ObservedCapacity `
        --interval PT1M --aggregation Maximum `
        --start-time <INICIO_UTC> --end-time <FIN_UTC> `
        -o json > evidencias/p1-escalonada/instancias.json

Uso:
  python graficos.py `
     --locust evidencias/p1-escalonada/run_stats_history.csv `
     --azure evidencias/p1-escalonada/instancias.json `
     --salida evidencias/graficos/p1_escalonada.png

Dependencias: pip install pandas matplotlib
"""

import argparse
import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

UMBRAL_P95_MS = 1000  # umbral de P1.1: p95 > 1 s


def cargar_locust(ruta):
    """Lee el historial de Locust y deja solo la fila agregada por segundo."""
    df = pd.read_csv(ruta)
    df = df[df["Name"] == "Aggregated"].copy()

    # Timestamp viene en segundos Unix (UTC).
    df["tiempo"] = pd.to_datetime(df["Timestamp"], unit="s", utc=True)
    df["usuarios"] = pd.to_numeric(df["User Count"], errors="coerce")
    df["rps"] = pd.to_numeric(df["Requests/s"], errors="coerce")
    df["fallos_s"] = pd.to_numeric(df["Failures/s"], errors="coerce")
    # Al inicio p95 puede venir como "N/A": se convierte en NaN.
    df["p95"] = pd.to_numeric(df["95%"], errors="coerce")

    # Los totales son acumulados, así que el último valor es el total de la prueba
    resumen = {
        "peticiones": int(df["Total Request Count"].iloc[-1]),
        "fallos": int(df["Total Failure Count"].iloc[-1]),
    }
    # Devuelve la tabla limpia y un diccionario con peticiones y fallos totales
    return df[["tiempo", "usuarios", "rps", "fallos_s", "p95"]], resumen


def cargar_instancias(ruta):
    """Lee el JSON de `az monitor metrics list` (ObservedCapacity)."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    puntos = datos["value"][0]["timeseries"][0]["data"]

    filas = [
        {"tiempo": p["timeStamp"], "instancias": p["maximum"]}
        for p in puntos
        if p.get("maximum") is not None
    ]
    df = pd.DataFrame(filas)
    df["tiempo"] = pd.to_datetime(df["tiempo"], utc=True)
    return df.sort_values("tiempo")


def recortar(df, inicio, fin, margen_min=2):
    """Deja solo el tramo de la prueba (con un pequeno margen)."""
    margen = pd.Timedelta(minutes=margen_min)
    return df[(df["tiempo"] >= inicio - margen) & (df["tiempo"] <= fin + margen)]


def eventos_autoscale(inst, inicio):
    """Primer scale-out y primer scale-in, en minutos desde el inicio."""
    cambios = inst["instancias"].diff()
    out = inst[cambios > 0]
    inn = inst[cambios < 0]
    texto = []
    if not out.empty:
        t = out.iloc[0]["tiempo"]
        texto.append(
            f"Primer scale-out: {t:%H:%M} (min {(t - inicio).total_seconds() / 60:.1f}), "
            f"a {int(out.iloc[0]['instancias'])} instancias"
        )
    if not inn.empty:
        t = inn.iloc[0]["tiempo"]
        texto.append(
            f"Primer scale-in: {t:%H:%M} (min {(t - inicio).total_seconds() / 60:.1f}), "
            f"a {int(inn.iloc[0]['instancias'])} instancias"
        )
    return texto


def graficar(loc, inst, salida, tz, titulo):
    # Convierte todo a la zona horaria de visualizacion.
    loc = loc.assign(tiempo=loc["tiempo"].dt.tz_convert(tz))
    inst = inst.assign(tiempo=inst["tiempo"].dt.tz_convert(tz))

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(12, 9), sharex=True,
        gridspec_kw={"height_ratios": [3, 3, 2]},
    )

    # 1) RPS y usuarios
    ax1.plot(loc["tiempo"], loc["rps"], color="tab:blue", label="RPS")
    ax1.plot(loc["tiempo"], loc["fallos_s"], color="tab:red", label="Fallos/s")
    ax1.set_ylabel("Peticiones por segundo")
    ax1b = ax1.twinx()
    ax1b.plot(loc["tiempo"], loc["usuarios"], color="gray", linestyle=":", label="Usuarios")
    ax1b.set_ylabel("Usuarios")
    l1, n1 = ax1.get_legend_handles_labels()
    l2, n2 = ax1b.get_legend_handles_labels()
    ax1.legend(l1 + l2, n1 + n2, loc="upper left")
    ax1.set_title(titulo)
    ax1.grid(alpha=0.3)

    # 2) p95 con el umbral de 1 s
    ax2.plot(loc["tiempo"], loc["p95"], color="tab:orange", label="p95 (ms)")
    ax2.axhline(UMBRAL_P95_MS, color="red", linestyle="--", label="Umbral 1 s")
    ax2.set_ylabel("Latencia p95 (ms)")
    ax2.legend(loc="upper left")
    ax2.grid(alpha=0.3)

    # 3) Instancias (escalonado: el valor se mantiene hasta el siguiente cambio)
    ax3.step(inst["tiempo"], inst["instancias"], where="post", color="tab:green")
    ax3.set_ylabel("Instancias")
    ax3.set_xlabel(f"Hora ({tz})")
    ax3.set_ylim(0, max(inst["instancias"].max() + 1, 3))
    ax3.yaxis.get_major_locator().set_params(integer=True)
    ax3.grid(alpha=0.3)

    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=loc["tiempo"].dt.tz))

    fig.tight_layout()
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=150)
    print(f"Grafico guardado en {salida}")


def main():
    ap = argparse.ArgumentParser(description="Grafico alineado Locust + autoscale")
    ap.add_argument("--locust", required=True, help="*_stats_history.csv de Locust")
    ap.add_argument("--azure", required=True, help="JSON de ObservedCapacity")
    ap.add_argument("--salida", default="evidencias/graficos/p1_escalonada.png")
    ap.add_argument("--tz", default="America/Bogota")
    ap.add_argument("--titulo", default="P1.2 - Prueba escalonada: carga, latencia e instancias")
    args = ap.parse_args()

    loc, resumen = cargar_locust(args.locust)
    inst = cargar_instancias(args.azure)

    inicio, fin = loc["tiempo"].min(), loc["tiempo"].max()
    inst = recortar(inst, inicio, fin)

    graficar(loc, inst, args.salida, args.tz, args.titulo)

    # Resumen util para el informe
    pct = 100 * resumen["fallos"] / max(resumen["peticiones"], 1)
    print(f"RPS maximo: {loc['rps'].max():.1f}")
    print(f"p95 maximo: {loc['p95'].max():.0f} ms")
    print(f"Peticiones: {resumen['peticiones']}  Fallos: {resumen['fallos']} ({pct:.2f} %)")
    print(f"Instancias (min-max): {int(inst['instancias'].min())}-{int(inst['instancias'].max())}")
    for linea in eventos_autoscale(inst, inicio):
        print(linea)


if __name__ == "__main__":
    main()