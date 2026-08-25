#!/bin/bash
set -e

# نام ریجن (برای لاگ‌ها) — از Env یا پیش‌فرض
REGION_NAME="${REGION_NAME:-unknown}"

echo "🚀 Starting X-UI + nginx reverse proxy [region: $REGION_NAME]..."

# ── Bootstrap خودکار ─────────────────────────────────────
if [ "${BOOTSTRAP:-0}" = "1" ]; then
    echo "🌍 Bootstrap mode: creating multi-region services..."
    python3 /app/bootstrap.py || echo "⚠️ bootstrap failed (continuing anyway)"
fi

# nginx همیشه روی پورت ثابت 3000 گوش می‌دهد
export NGINX_PORT=3000

cd /usr/local/x-ui

echo "🔧 Applying panel settings via x-ui CLI..."
./x-ui setting -port 2053 -webBasePath /managepanel/ || true

echo "🔧 Building nginx.conf for fixed port: $NGINX_PORT"
envsubst '${NGINX_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

echo "▶️  Starting x-ui in background..."
./x-ui &
X_UI_PID=$!

# آماده‌سازی nginx.conf قبل از تست
nginx -t

# ── Init panels (ساخت اینباند + نود) در background ──────
# فقط زمانی اجرا می‌شود که پنل اصلی (INIT_PANELS=1) باشد؛ نودها و اینباندها
# از راه دور روی همه‌ی پنل‌ها ساخته می‌شوند. init_panels.sh خودش retry دارد.
if [ "${INIT_PANELS:-0}" = "1" ]; then
    echo "⏱ init panels: زمان‌بندی ساخت اینباند+نود (بعد از بالا آمدن nginx)..."
    # بعد از 10 ثانیه (تا nginx بالا بیاید) اجرا کن — ولی nginx را block نکن
    ( sleep 10 && /start_scripts/init_panels.sh > /var/log/x-ui/init-panels.log 2>&1 ) &
fi

# nginx در foreground — ورودی اصلی فرایند را نگه می‌دارد
exec nginx -g "daemon off;"
