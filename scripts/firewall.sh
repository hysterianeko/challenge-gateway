#!/bin/sh
set -eu

PORT="${CLOUDFLYER_PORT:-3000}"
ALLOWED_IPS="${ALLOWED_IPS:-}"

if ! command -v iptables >/dev/null 2>&1; then
  echo "iptables not found" >&2
  exit 1
fi

iptables -N DOCKER-USER 2>/dev/null || true

# Drop stale Cloudflyer rules, then re-add.
iptables -S DOCKER-USER | awk -v port="$PORT" '
  $0 ~ "--dport "port {
    sub(/^-A /, "-D ")
    print
  }
' | while IFS= read -r rule; do
  # shellcheck disable=SC2086
  iptables $rule || true
done

iptables -I DOCKER-USER 1 -p tcp --dport "$PORT" -j DROP
iptables -I DOCKER-USER 1 -s 127.0.0.1/32 -p tcp --dport "$PORT" -j ACCEPT

if [ -n "$ALLOWED_IPS" ]; then
  old_ifs=$IFS
  IFS=','
  for ip in $ALLOWED_IPS; do
    ip=$(echo "$ip" | tr -d ' ')
    [ -n "$ip" ] || continue
    iptables -I DOCKER-USER 1 -s "$ip" -p tcp --dport "$PORT" -j ACCEPT
  done
  IFS=$old_ifs
fi

echo "DOCKER-USER rules for tcp/$PORT:"
iptables -S DOCKER-USER
