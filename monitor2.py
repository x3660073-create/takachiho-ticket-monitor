import os
import re
import sys
from datetime import datetime, timezone, timedelta

import requests
from playwright.sync_api import sync_playwright


TARGET_DATE = "2026/9/10"
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


def click_next_week(page):
    print("尋找下一週按鈕...")

    buttons = page.locator("button")

    count = buttons.count()

    print("找到 button 數量:", count)

    for i in range(count):

        try:
            button = buttons.nth(i)

            if not button.is_visible():
                continue

            text = button.inner_text().strip()

            aria = button.get_attribute("aria-label") or ""
            title = button.get_attribute("title") or ""

            print(
                "Button:",
                i,
                "text=",
                repr(text),
                "aria=",
                repr(aria),
                "title=",
                repr(title),
            )

            if (
                text in [">", "＞", "〉", "→"]
                or "next" in aria.lower()
                or "next" in title.lower()
                or "次" in aria
                or "次" in title
            ):

                button.click()

                page.wait_for_timeout(4000)

                print("✅ 已切換到下一週")

                return True

        except Exception as e:
            print("按鈕檢查錯誤:", repr(e))

    # 第二種方法：尋找文字 ＞
    try:

        candidates = page.get_by_text("＞")

        count = candidates.count()

        print("找到 ＞ 數量:", count)

        for i in range(count):

            try:

                element = candidates.nth(i)

                if element.is_visible():

                    element.click()

                    page.wait_for_timeout(4000)

                    print("✅ 已點擊 ＞")

                    return True

            except Exception:
                pass

    except Exception:
        pass

    print("❌ 找不到下一週按鈕")

    return False


def find_ticket_slots(page):

    body_text = page.locator("body").inner_text()

    print("=" * 60)
    print("切換後頁面文字")
    print("=" * 60)

    print(body_text[:15000])

    print("=" * 60)

    # 檢查是否進入 9/7～9/13
    if (
        "2026/09/07" in body_text
        or "2026/9/7" in body_text
        or "2026/09/13" in body_text
        or "2026/9/13" in body_text
    ):

        print("✅ 已進入 9/7～9/13 週")

    else:

        print("⚠️ 尚未確認 9/7～9/13")

    # 找所有「残X艇」
    pattern = re.compile(r"残\s*(\d+)\s*艇")

    matches = pattern.findall(body_text)

    print("找到「残X艇」數量:", len(matches))

    for match in matches:

        print("可用船位:", match, "艇")

    return matches


def main():

    print("=" * 60)

    print("🎫 高千穗峽貸船監控")

    print("目標日期:", TARGET_DATE)

    print(
        "執行時間:",
        datetime.now(JST).strftime(
            "%Y-%m-%d %H:%M:%S JST"
        )
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

        print("開啟高千穗預約網站...")

        page.goto(
            TARGET_URL,
            wait_until="networkidle",
            timeout=60000,
        )

        page.wait_for_timeout(5000)

        print("目前網址:", page.url)

        print("目前日期畫面:")

        first_text = page.locator(
            "body"
        ).inner_text()

        print(first_text[:3000])

        # 自動切換到下一週
        clicked = click_next_week(page)

        if not clicked:

            page.screenshot(
                path="takachiho_debug.png",
                full_page=True,
            )

            with open(
                "takachiho_debug.html",
                "w",
                encoding="utf-8"
            ) as f:

                f.write(page.content())

            browser.close()

            return

        # 分析下一週
        matches = find_ticket_slots(page)

        # 儲存 debug
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

        # 目前先只在真的抓到「残X艇」時通知
        if matches:

            message = (
                "🎫 高千穗峽貸船有票！\n\n"
                "📅 日期：2026/9/10\n\n"
            )

            for remaining in matches:

                message += (
                    f"🚤 剩餘 {remaining} 艘\n"
                )

            message += (
                "\n🚨 請立即預約：\n"
                f"{TARGET_URL}"
            )

            print(message)

            send_line(message)

        else:

            print(
                "❌ 目前沒有偵測到「残X艇」。"
            )


if __name__ == "__main__":

    try:

        main()

    except Exception as e:

        print("❌ 發生錯誤:", repr(e))

        sys.exit(1)
