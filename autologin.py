import base64
import os
import re
import time
from playwright.sync_api import sync_playwright

SERVER_ID = os.getenv("SERVER_ID")
if not SERVER_ID:
    SERVER_ID = "ba6c4e06"

STATE_JSON_BASE64 = os.getenv("STATE_JSON_BASE64")

if STATE_JSON_BASE64:
    with open("state.json", "wb") as f:
        f.write(base64.b64decode(STATE_JSON_BASE64))

if not os.path.exists("state.json"):
    print("[-] КРИТИЧЕСКАЯ ОШИБКА: Файл state.json не найден!")
    exit(1)

print("[1/2] Запуск браузера с сохраненной сессией для продления 3-дневного таймера...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    context = browser.new_context(
        storage_state="state.json",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # 1. Продление таймера на OptikLink
    print("[!] Переход в Dashboard OptikLink...")
    try:
        page.goto("https://optiklink.net/dashboard", wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"[*] Предупреждение при переходе на /dashboard: {e}")

    page.wait_for_timeout(5000)

    is_authenticated = False
    for selector in ["text=Logout", "text=Dashboard", "text=Create Server", "text=Servers"]:
        try:
            if page.is_visible(selector, timeout=3000):
                is_authenticated = True
                break
        except Exception:
            pass

    if is_authenticated:
        print("[+] НАСТОЯЩИЙ УСПЕХ: Авторизация пройдена по кукам, 3-дневный таймер продлен!")
    else:
        print("[-] ОШИБКА: Сессия устарела или страница не загрузилась.")
        page.screenshot(path="error_auth.png")
        browser.close()
        raise Exception("Не удалось зайти в Dashboard OptikLink. Пересоздайте state.json.")

    # 2. Переход в панель управления сервером и запуск
    print(f"\n[2/2] Переход в панель управления сервером ({SERVER_ID}) и запуск...")
    server_url = f"https://control.optiklink.net/server/{SERVER_ID}"
    try:
        page.goto(server_url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"[*] Предупреждение при открытии панели сервера: {e}")

    page.wait_for_timeout(4000)

    # Если редиректнуло на логин поддомена control.optiklink.net
    if "auth/login" in page.url or "login" in page.url:
        print("[!] Требуется авторизация в control.optiklink.net. Нажимаем кнопку входа...")
        login_btn = page.locator('a[href*="login"], button:has-text("Login"), a:has-text("Login"), button:has-text("Sign in"), button:has-text("Discord")').first
        if login_btn.is_visible(timeout=5000):
            login_btn.click()
            page.wait_for_timeout(5000)
            # Возвращаемся на страницу сервера после авторизации
            page.goto(server_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

    # Ждем подгрузки консоли и кнопок Pterodactyl
    page.wait_for_timeout(6000)

    try:
        # Регистронезависимый поиск кнопки START
        start_btn = page.locator('button').filter(has_text=re.compile(r"^start$", re.IGNORECASE)).first
        
        if not start_btn.is_visible():
            start_btn = page.locator('button:has-text("START"), button:has-text("Start")').first

        if start_btn.is_visible(timeout=10000):
            print("[!] Кнопка START найдена, отправляем клик...")
            start_btn.click()
            page.wait_for_timeout(5000)
            print("[+] УСПЕХ: Сервер запущен через веб-интерфейс!")
        else:
            page.screenshot(path="error_start_button.png")
            print("[-] Кнопка START не найдена на странице. Скриншот сохраняется в Artifacts.")
            print(f"[*] Текущий URL: {page.url}")
    except Exception as e:
        page.screenshot(path="error_start_button.png")
        print(f"[*] Не удалось нажать START: {e}")

    browser.close()
