import os
import sys
from datetime import datetime, timezone, timedelta

import requests
from playwright.sync_api import sync_playwright


TARGET_DATE = "2026-09-10"
TARGET_URL = "https://eipro.jp/takachiho1/eventCalendars/index"

LINE_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]

JST = timezone(timedelta(hours=9))


def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}",
    }

    data = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message,
            }
        ],
    }

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=30,
    )

    print("LINE:", response.status_code)
    print(response.text)

    response.raise_for_status()


def check_ticket():
    print("=" * 60)
    print("高千穗峽貸船票況監控")
    print("目標日期:", TARGET_DATE)
    print(
        "開始時間:",
        datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    )
    print("=" * 60)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            viewport={
                "width": 1440,
                "height": 1200,
            },
        )

        print("開啟預約網站...")

        page.goto(
            TARGET_URL,
            wait_until="networkidle",
            timeout=60000,
        )

        page.wait_for_timeout(5000)

        print("目前網址:", page.url)

        text = page.locator("body").inner_text()

        print("頁面文字前 5000 字:")
        print(text[:5000])

        if (
            TARGET_DATE in text
            or "9月10日" in text
            or "9/10" in text
        ):
            print("找到 9/10 日期資訊")
        else:
            print("目前頁面文字中尚未找到 9/10")

        with open(
            "takachiho_debug.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(page.content())

        page.screenshot(
            path="takachiho_debug.png",
            full_page=True,
        )

        browser.close()

    return False


if __name__ == "__main__":

    try:

        has_ticket = check_ticket()

        if has_ticket:

            send_line(
                "🎫 高千穗峽貸船有票！\n\n"
                f"📅 日期：{TARGET_DATE}\n"
                "🚨 請立即進入官方網站預約：\n"
                f"{TARGET_URL}"
            )

        else:

            print("目前沒有確認到可預約時段。")

    except Exception as e:

        print("發生錯誤:", repr(e))
        sys.exit(1)
