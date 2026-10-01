#!/bin/sh
set -e

if [ -z "${CLIENTT_KEY}" ]; then
  echo "CLIENTT_KEY is required for Cloudflyer" >&2
  exit 1
fi

if [ -z "${CHROME_PATH}" ]; then
  for candidate in /usr/bin/chromium /usr/bin/chromium-browser /usr/bin/google-chrome; do
    if [ -x "${candidate}" ]; then
      CHROME_PATH="${candidate}"
      break
    fi
  done
  export CHROME_PATH
fi

exec cloudflyer \
  -K "${CLIENTT_KEY}" \
  -H "${CLOUDFLYER_HOST:-0.0.0.0}" \
  -P "${CLOUDFLYER_PORT:-3000}" \
  -M "${CLOUDFLYER_MAX_TASKS:-1}" \
  -T "${CLOUDFLYER_TIMEOUT:-120}" \
  -L
