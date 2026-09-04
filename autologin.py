import base64
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


SERVER_ID = os.getenv("SERVER_ID")
PANEL_USER = os.getenv("PANEL_USER")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
STATE_JSON_BASE64 = os.getenv("STATE_JSON_BASE64")
ENABLE_SCREENSHOTS = os.getenv("ENABLE_SCREENSHOTS", "false").lower() in ("1", "true", "yes")

OPTIKLINK_AUTH_URL = "https://optiklink.net/auth"
PANEL_BASE = "https://control.optiklink.net"


def die(message: str, code: int = 1):
    print(f"[ОШИБКА] {message}")
    sys.exit(code)


def take_screenshot(page, name: str):
    if not ENABLE_SCREENSHOTS:
        return
    try:
        page.screenshot(path=f"{name}.png", full_page=True)
        print(f"[*] Скриншот сохранён: {name}.png")
    except Exception as e:
        print(f"[*] Не удалось сохранить скриншот {name}: {e}")


def main():
    if not SERVER_ID:
        die("Не задан секрет SERVER_ID")

    if STATE_JSON_BASE64:
        try:
            Path("state.json").write_bytes(base64.b64decode(STATE_JSON_BASE64))
            print("[+] Сессия успешно восстановлена из STATE_JSON_BASE64")
        except Exception as e:
            print(f"[!] Не удалось восстановить сессию: {e}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context_options = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        if Path("state.json").exists():
            context_options["storage_state"] = "state.json"

        context = browser.new_context(**context_options)
        page = context.new_page()

        # 1. Продление таймера
        print("[1/2] Переход на OptikLink для продления таймера...")
        try:
            page.goto(OPTIKLINK_AUTH_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            print("[+] Таймер успешно продлён (или уже был активен)")
        except Exception as e:
            print(f"[*] Предупреждение при обращении к optiklink.net: {e}")
            take_screenshot(page, "error_optiklink")

        # 2. Страница сервера
        server_url = f"{PANEL_BASE}/server/{SERVER_ID}"
        print(f"[2/2] Переход на страницу сервера: {server_url}")

        try:
            page.goto(server_url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[*] Ошибка загрузки страницы сервера: {e}")
            take_screenshot(page, "error_server_page")

        page.wait_for_timeout(4000)

        # 3. Авторизация при необходимости
        if "login" in page.url or page.locator('input[type="password"]').is_visible():
            print("[!] Обнаружена форма входа. Выполняется авторизация...")

            if not PANEL_USER or not PANEL_PASSWORD:
                take_screenshot(page, "error_no_credentials")
                die("Не заданы секреты PANEL_USER и/или PANEL_PASSWORD")

            user_input = page.locator(
                'input[type="text"], input[name="username"], input[name="email"]'
            ).first
            pass_input = page.locator('input[type="password"]').first

            user_input.fill(PANEL_USER)
            pass_input.fill(PANEL_PASSWORD)

            login_btn = page.locator(
                'button:has-text("LOGIN"), button[type="submit"]'
            ).first
            login_btn.click()

            try:
                page.wait_for_url(lambda url: "auth/login" not in url, timeout=15000)
                print("[+] Авторизация в панели выполнена успешно")
            except PlaywrightTimeout:
                take_screenshot(page, "error_login_failed")
                die("Не удалось войти в панель. Проверьте PANEL_USER и PANEL_PASSWORD")

            page.goto(server_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

        # 4. Запуск сервера
        print("[!] Поиск кнопки START...")
        try:
            start_btn = page.locator("button").filter(
                has_text=re.compile(r"^start$", re.IGNORECASE)
            ).first

            if not start_btn.is_visible():
                start_btn = page.locator(
                    'button:has-text("START"), button:has-text("Start")'
                ).first

            if start_btn.is_visible(timeout=10000):
                start_btn.click()
                page.wait_for_timeout(5000)
                print("[+] Сервер успешно запущен через веб-интерфейс")
            else:
                print("[-] Кнопка START не найдена (возможно, сервер уже запущен)")
                print(f"[*] Текущий URL: {page.url}")
                take_screenshot(page, "error_start_button")
        except Exception as e:
            print(f"[-] Ошибка при попытке нажать START: {e}")
            take_screenshot(page, "error_start_button")

        browser.close()
        print("[+] Работа скрипта завершена")


if __name__ == "__main__":
    main()
