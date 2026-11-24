#!/usr/bin/env python3
"""
sla_compuesto.py - Calculo del SLA compuesto de CaribeShop (informe, punto 3).

IMPORTANTE: los porcentajes de abajo son valores de partida. Verifica cada uno en
la documentacion oficial de SLA de Azure (azure.microsoft.com/support/legal/sla)
antes de ponerlos en el informe, y ajusta la lista a tu arquitectura final.

Componentes en SERIE (si falla uno, cae la tienda): SLA = producto de todos.
Componentes REDUNDANTES (n copias independientes): 1 - (1 - SLA)^n
"""
import math

# nombre: SLA en % (VERIFICAR en la documentacion oficial)
SERIE = {
    "IP publica Standard": 99.99,
    "Load Balancer Standard": 99.99,
    "VM Scale Set (2+ instancias en 2+ zonas)": 99.99,
    "Key Vault": 99.99,
    "Storage (LRS)": 99.9,
    "Log Analytics / Monitor (no afecta la disponibilidad de la tienda)": None,
}

producto = 1.0
print(f"{'Componente':<70}{'SLA %':>8}")
for nombre, sla in SERIE.items():
    if sla is None:
        print(f"{nombre:<70}{'excluido':>8}")
        continue
    print(f"{nombre:<70}{sla:>8.2f}")
    producto *= sla / 100

total = producto * 100
min_mes = (1 - producto) * 30 * 24 * 60
print("-" * 78)
print(f"SLA compuesto: {total:.4f} %  ->  caida maxima ~ {min_mes:.0f} min/mes")


def redundante(sla_pct, n):
    return (1 - (1 - sla_pct / 100) ** n) * 100


# Ejemplo para la pregunta 3: dos regiones independientes con el mismo SLA
print(f"Con 2 regiones independientes (hipotetico): {redundante(total, 2):.6f} %")
