FROM python:3.10-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    CHROME_PATH=/usr/local/bin/chromium-wrapper \
    CLOUDFLYER_URL=http://127.0.0.1:3000 \
    CADDY_VERSION=2.9.1 \
    XDG_CONFIG_HOME=/config \
    XDG_DATA_HOME=/data

RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        xvfb \
        fonts-liberation \
        fonts-noto-cjk \
        ca-certificates \
        tzdata \
        dbus \
        curl \
        supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

RUN curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_amd64.tar.gz" \
        | tar -xz -C /usr/local/bin caddy \
    && chmod +x /usr/local/bin/caddy

COPY docker/cloudflyer/chromium-wrapper.sh /usr/local/bin/chromium-wrapper
RUN chmod +x /usr/local/bin/chromium-wrapper \
    && if [ -x /usr/bin/chromium-browser ]; then \
         sed -i 's|/usr/bin/chromium|/usr/bin/chromium-browser|' /usr/local/bin/chromium-wrapper; \
       fi

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir "cloudflyer==1.0.5" -r /app/requirements.txt

COPY api /app
COPY supervisord.conf /etc/supervisor/conf.d/challenge.conf
COPY docker/all-in-one/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /data /config /etc/caddy

WORKDIR /app
EXPOSE 80 443 3000
VOLUME ["/data", "/config"]
ENTRYPOINT ["/entrypoint.sh"]
