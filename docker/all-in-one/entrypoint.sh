#!/bin/sh
set -e

if [ -z "${CLIENTT_KEY}" ]; then
  echo "CLIENTT_KEY is required" >&2
  exit 1
fi

export CLOUDFLYER_MAX_TASKS="${CLOUDFLYER_MAX_TASKS:-1}"
export CLOUDFLYER_TIMEOUT="${CLOUDFLYER_TIMEOUT:-120}"
export CLOUDFLYER_URL="${CLOUDFLYER_URL:-http://127.0.0.1:3000}"
export DOMAIN="${DOMAIN:-challenge.cool.pp.ua}"
export ACME_EMAIL="${ACME_EMAIL:-admin@${DOMAIN}}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-/config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-/data}"

if [ -z "${CHROME_PATH}" ]; then
  for candidate in /usr/bin/chromium /usr/bin/chromium-browser /usr/bin/google-chrome; do
    if [ -x "${candidate}" ]; then
      export CHROME_PATH="${candidate}"
      break
    fi
  done
fi

mkdir -p /data /config /etc/caddy

if [ "${ENABLE_TLS:-true}" = "true" ] && [ -n "${DOMAIN}" ]; then
  cat > /etc/caddy/Caddyfile <<EOF
{
  email ${ACME_EMAIL}
}

${DOMAIN} {
  encode gzip
  @blocked {
    path /
    path /docs
    path /docs/*
    path /redoc
    path /redoc/*
    path /openapi.json
  }
  handle @blocked {
    respond 404
  }
  reverse_proxy 127.0.0.1:8080
}
EOF
else
  cat > /etc/caddy/Caddyfile <<EOF
:80 {
  reverse_proxy 127.0.0.1:8080
}
EOF
fi

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/challenge.conf
