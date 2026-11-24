#!/bin/sh
# Ejecutar dentro de una instancia del VMSS. No modifica su configuración.
printf 'utc=%s host=%s\n' "$(date -u +%FT%TZ)" "$(hostname)"
timeout 10 getent ahostsv4 example.com
printf 'dns_exit=%s\n' "$?"
curl -4 --noproxy '*' --connect-timeout 5 --max-time 12 --silent --show-error \
  --output /dev/null --write-out 'http_status=%{http_code}\n' https://example.com/
printf 'curl_exit=%s\n' "$?"
