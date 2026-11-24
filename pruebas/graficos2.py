
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

def _leer_texto(ruta):
    """Lee texto detectando UTF-16 (PowerShell 5.1) o UTF-8 con/sin BOM."""
    datos = Path(ruta).read_bytes()
    if datos.startswith((b"\xff\xfe", b"\xfe\xff")):
        return datos.decode("utf-16")
    return datos.decode("utf-8-sig")

def cargar_instancias(ruta):
    """Lee el JSON de `az monitor metrics list` (ObservedCapacity)."""
    datos = json.loads(_leer_texto(ruta))
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
    loc = loc.assign(tiempo=loc["tiempo"].dt.tz_convert(tz))

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 8), sharex=True,
        gridspec_kw={"height_ratios": [3, 3]},
    )

    # 1) RPS, fallos y usuarios
    ax1.plot(loc["tiempo"], loc["rps"], label="RPS")
    ax1.plot(loc["tiempo"], loc["fallos_s"], label="Fallos/s")
    ax1.set_ylabel("Peticiones por segundo")

    ax1b = ax1.twinx()
    ax1b.plot(
        loc["tiempo"], loc["usuarios"],
        color="gray", linestyle=":", label="Usuarios"
    )
    ax1b.set_ylabel("Usuarios")

    l1, n1 = ax1.get_legend_handles_labels()
    l2, n2 = ax1b.get_legend_handles_labels()
    ax1.legend(l1 + l2, n1 + n2, loc="upper left")
    ax1.set_title(titulo)
    ax1.grid(alpha=0.3)

    # 2) Latencia p95
    ax2.plot(loc["tiempo"], loc["p95"], label="p95 (ms)")
    ax2.axhline(
        UMBRAL_P95_MS, color="red",
        linestyle="--", label="Umbral 1 s"
    )
    ax2.set_ylabel("Latencia p95 (ms)")
    ax2.set_xlabel(f"Hora ({tz})")
    ax2.legend(loc="upper left")
    ax2.grid(alpha=0.3)

    ax2.xaxis.set_major_formatter(
        mdates.DateFormatter("%H:%M", tz=loc["tiempo"].dt.tz)
    )

    fig.tight_layout()
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=150)
    plt.close(fig)

    print(f"Gráfico guardado en {salida}")


def main():
    ap = argparse.ArgumentParser(
        description="Graficos de rendimiento de Locust"
    )
    ap.add_argument(
        "--locust", required=True,
        help="*_stats_history.csv de Locust"
    )
    ap.add_argument(
        "--salida",
        default="evidencias/graficos/p1_escalonada.png"
    )
    ap.add_argument("--tz", default="America/Bogota")
    ap.add_argument(
        "--titulo",
        default="P1.2 - Prueba escalonada: carga y latencia"
    )
    args = ap.parse_args()

    loc, resumen = cargar_locust(args.locust)

    graficar(loc, None, args.salida, args.tz, args.titulo)

    pct = 100 * resumen["fallos"] / max(resumen["peticiones"], 1)

    print(f"RPS maximo: {loc['rps'].max():.1f}")
    print(f"p95 maximo: {loc['p95'].max():.0f} ms")
    print(
        f"Peticiones: {resumen['peticiones']}  "
        f"Fallos: {resumen['fallos']} ({pct:.2f} %)"
    )


if __name__ == "__main__":
    main()
