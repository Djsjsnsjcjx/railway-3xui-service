#!/bin/bash
# ============================================================
# init_panels.sh — ساخته‌ی خودکار اینباند + اتصال نودها
# ============================================================
# فقط روی سرویس اصلی (MAIN_PANEL) اجرا می‌شود، فقط یک‌بار (marker روی ولوم).
#
# انتظار می‌رود این ENV ها ست شده باشند (توسط bootstrap.py):
#   PANELS           e.g. "xui-nl=https://...;xui-sg=https://...;..."
#   BOOTSTRAP_READY  1
#   MAIN_PANEL       نام پنل اصلی (پیش‌فرض xui-nl)
#   REMOTE_NODES     نودهای ریموت (پیش‌فرض xui-sg,xui-us-va,xui-us-ca)
#
# retry می‌کند تا همه‌ی پنل‌ها بالا بیایند و درباند/نود ساخته شود.
# ============================================================
set -e

MAIN_PANEL="${MAIN_PANEL:-xui-nl}"
REMOTE_NODES="${REMOTE_NODES:-xui-sg,xui-us-va,xui-us-ca}"
XUI_USERNAME="${XUI_USERNAME:-admin}"
XUI_PASSWORD="${XUI_PASSWORD:-admin}"
PANELS="${PANELS:-}"

# marker روی ولوم — تا فقط یک‌بار اجرا شود
MARKER="/etc/x-ui/.panels-setup-done"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$MARKER" ]; then
    echo "⏭️  init panels: از قبل انجام شده (marker موجود) — رد شد"
    exit 0
fi

if [ -z "$PANELS" ]; then
    echo "⚠️ init panels: PANELS ست نشده — رد شد (bootstrap هنوز ثبت نکرده)"
    exit 0
fi

if [ "${BOOTSTRAP_READY:-0}" != "1" ]; then
    echo "⚠️ init panels: BOOTSTRAP_READY!=1 — رد شد"
    exit 0
fi

# فقط پنل اصلی (INIT_PANELS=1) این فاز را اجرا می‌کند — جلوگیری از race
if [ "${INIT_PANELS:-0}" != "1" ]; then
    echo "⏭️ init panels: INIT_PANELS!=1 (این سرویس پنل اصلی نیست) — رد شد"
    exit 0
fi

echo "🛠 init panels: ساخت اینباند + اتصال نودها (MAIN_PANEL=$MAIN_PANEL)..."

export PANELS MAIN_PANEL REMOTE_NODES XUI_USERNAME XUI_PASSWORD

MAX_ATTEMPTS=30        # هر 20 ثانیه → حداکثر 10 دقیقه
ATTEMPT=0
while [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "▶  تلاش $ATTEMPT/$MAX_ATTEMPTS برای ساخت اینباند + نود..."

    # ۱) اتصال نودها
    echo "  ── xui-node-connector.py ──"
    if python3 "$SCRIPT_DIR/xui-node-connector.py"; then
        echo "  ✅ node-connector موفق"
    else
        echo "  ⚠️ node-connector خطا داد (ادامه می‌دهم)"
    fi

    # ۲) ساخت اینباند Reality
    echo "  ── xui-reality-inbound.py ──"
    if python3 "$SCRIPT_DIR/xui-reality-inbound.py"; then
        echo "  ✅ اینباند ساخته شد"
        # موفق → mark کن و تمام
        mkdir -p /etc/x-ui && touch "$MARKER"
        echo "🎉 init panels کامل شد!"
        exit 0
    else
        echo "  ⚠️ اینباند خطا داد — شاید همه‌ی پنل‌ها بالا نیامده‌اند"
    fi

    sleep 20
done

echo "❌ init panels: بعد از $MAX_ATTEMPTS تلاش موفق نشد — continue در لاگ‌ها را ببین"
exit 1
