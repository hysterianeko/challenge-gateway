FROM python:3.10-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    CHROME_PATH=/usr/local/bin/chromium-wrapper

RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        xvfb \
        fonts-liberation \
        fonts-noto-cjk \
        ca-certificates \
        tzdata \
        dbus \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

RUN pip install --no-cache-dir "cloudflyer==1.0.5"

COPY chromium-wrapper.sh /usr/local/bin/chromium-wrapper
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /usr/local/bin/chromium-wrapper /entrypoint.sh \
    && if [ -x /usr/bin/chromium ]; then \
         sed -i 's|/usr/bin/chromium|/usr/bin/chromium|' /usr/local/bin/chromium-wrapper; \
       elif [ -x /usr/bin/chromium-browser ]; then \
         sed -i 's|/usr/bin/chromium|/usr/bin/chromium-browser|' /usr/local/bin/chromium-wrapper; \
       fi

EXPOSE 3000
ENTRYPOINT ["/entrypoint.sh"]
