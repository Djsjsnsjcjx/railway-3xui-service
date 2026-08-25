FROM alpine:3.20

RUN apk add --no-cache \
    curl \
    bash \
    python3 \
    py3-pip \
    ca-certificates \
    socat \
    tzdata \
    sqlite \
    nginx \
    gettext \
    && ln -sf /usr/share/zoneinfo/Asia/Tehran /etc/localtime

# دانلود و نصب 3x-ui (آخرین نسخه پایدار v3.6.0)
ARG XUI_VERSION=v3.6.0
RUN curl -L https://github.com/mhsanaei/3x-ui/releases/download/${XUI_VERSION}/x-ui-linux-amd64.tar.gz -o /tmp/x-ui.tar.gz \
    && tar -xzf /tmp/x-ui.tar.gz -C /usr/local/ \
    && rm /tmp/x-ui.tar.gz \
    && chmod +x /usr/local/x-ui/x-ui

RUN mkdir -p /etc/x-ui /var/log/x-ui /start_scripts

# وابستگی python برای ساخت اینباند Reality (X25519 keypair)
RUN pip3 install --no-cache-dir cryptography || true

COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY start.sh /start.sh
COPY bootstrap.py /app/bootstrap.py

# اسکریپت‌های ساخت/مدیریت اینباند و نود
COPY railway_gql.py /start_scripts/railway_gql.py
COPY railway_gql.py /app/railway_gql.py   # bootstrap.py از این import می‌کند
COPY xui-reality-inbound.py /start_scripts/xui-reality-inbound.py
COPY xui-node-connector.py /start_scripts/xui-node-connector.py
COPY xui-link-maker.py /start_scripts/xui-link-maker.py
COPY xui-tcp-proxy-setup.py /start_scripts/xui-tcp-proxy-setup.py
COPY init_panels.sh /start_scripts/init_panels.sh

RUN chmod +x /start.sh /start_scripts/init_panels.sh /start_scripts/*.py

# Railway پورت رو از طریق متغیر $PORT تزریق می‌کند
CMD ["/start.sh"]
