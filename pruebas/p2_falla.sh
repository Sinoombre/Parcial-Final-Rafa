#!/usr/bin/env bash
# p2_falla.sh - Provoca y registra las fallas de P2 (macOS/Linux, requiere az CLI logueado).
#
# Uso:
#   ./pruebas/p2_falla.sh instancias              # lista instancias, hostname y zona
#   ./pruebas/p2_falla.sh logica   <instance-id>  # crea la bandera -> /health responde 503
#   ./pruebas/p2_falla.sh restaurar <instance-id> # borra la bandera (por si no se reemplaza sola)
#   ./pruebas/p2_falla.sh abrupta  <instance-id>  # elimina la instancia del VMSS
#
# Variables opcionales: RG, VMSS (por defecto rg-caribeshop / vmss-caribeshop)
set -euo pipefail

RG="${RG:-rg-caribeshop}"
VMSS="${VMSS:-vmss-caribeshop}"
EVENTOS="evidencias/p2-fallas/eventos.csv"
mkdir -p evidencias/p2-fallas
[ -f "$EVENTOS" ] || echo "utc,evento,instancia,hostname,detalle" > "$EVENTOS"

ahora() { python3 -c "from datetime import datetime,timezone;print(datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z'))"; }
hostname_de() { az vmss list-instances -g "$RG" -n "$VMSS" --query "[?instanceId=='$1'].osProfile.computerName | [0]" -o tsv; }
registrar() { echo "$1,$2,$3,$4,$5" >> "$EVENTOS"; echo "[$1] $2 instancia=$3 host=$4 $5"; }

cmd="${1:-}"; id="${2:-}"

case "$cmd" in
  instancias)
    az vmss list-instances -g "$RG" -n "$VMSS" \
      --query "[].{id:instanceId, host:osProfile.computerName, zona:zones[0], estado:provisioningState}" -o table
    ;;
  logica)
    [ -n "$id" ] || { echo "Falta instance-id"; exit 1; }
    host="$(hostname_de "$id")"
    registrar "$(ahora)" "FALLA_LOGICA_ORDEN" "$id" "$host" "antes de ejecutar run-command"
    # La hora dentro de la VM es la que mejor marca el instante real de la falla
    salida="$(az vmss run-command invoke -g "$RG" -n "$VMSS" --instance-id "$id" \
      --command-id RunShellScript \
      --scripts "touch /var/lib/caribeshop/unhealthy && date -u +%Y-%m-%dT%H:%M:%S.%NZ" \
      --query "value[0].message" -o tsv)"
    echo "$salida"
    hora_vm="$(echo "$salida" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z' | head -1 || true)"
    registrar "${hora_vm:-$(ahora)}" "FALLA_LOGICA_ACTIVA" "$id" "$host" "bandera creada: /health responde 503"
    ;;
  restaurar)
    [ -n "$id" ] || { echo "Falta instance-id"; exit 1; }
    host="$(hostname_de "$id")"
    az vmss run-command invoke -g "$RG" -n "$VMSS" --instance-id "$id" \
      --command-id RunShellScript --scripts "rm -f /var/lib/caribeshop/unhealthy" -o none
    registrar "$(ahora)" "RESTAURADA" "$id" "$host" "bandera eliminada"
    ;;
  abrupta)
    [ -n "$id" ] || { echo "Falta instance-id"; exit 1; }
    host="$(hostname_de "$id")"
    registrar "$(ahora)" "FALLA_ABRUPTA_INICIO" "$id" "$host" "delete-instances"
    az vmss delete-instances -g "$RG" -n "$VMSS" --instance-ids "$id" --no-wait
    echo "Eliminacion enviada. Mira el estado con: $0 instancias"
    ;;
  *)
    sed -n '2,12p' "$0"; exit 1 ;;
esac
