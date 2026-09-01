import base64
import os
import re
import time
from playwright.sync_api import sync_playwright

SERVER_ID = os.getenv("SERVER_ID", "ba6c4e06")
PANEL_USER = os.getenv("PANEL_USER")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")

STATE_JSON_BASE64 = os.getenv("STATE_JSON_BASE64")

if STATE_JSON_BASE64:
    with open("state.json", "wb") as f:
        f.write(base64.b64decode(STATE_JSON_BASE64))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    context_kwargs = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    if os.path.exists("state.json"):
        context_kwargs["storage_state"] = "state.json"
        
    context = browser.new_context(**context_kwargs)
    page = context.new_page()

    # 1. Продление таймера на OptikLink
    print("[1/2] Запуск браузера для продления 3-дневного таймера...")
    try:
        page.goto("https://optiklink.net/auth", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        print("[+] Авторизация на OptikLink пройдена, 3-дневный таймер продлен!")
    except Exception as e:
        print(f"[*] Предупреждение при заходе на optiklink.net: {e}")

    # 2. Переход в панель управления сервером
    server_url = f"https://control.optiklink.net/server/{SERVER_ID}"
    print(f"\n[2/2] Переход на страницу сервера ({server_url})...")
    
    try:
        page.goto(server_url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"[*] Ошибка загрузки страницы: {e}")

    page.wait_for_timeout(4000)

    # 3. Если открылась форма входа /auth/login
    if "login" in page.url or page.locator('input[type="password"]').is_visible():
        print("[!] Обнаружена форма входа. Заполняем логин и пароль...")
        
        if not PANEL_USER or not PANEL_PASSWORD:
            print("[-] ОШИБКА: Не заданы переменные PANEL_USER или PANEL_PASSWORD в GitHub Secrets!")
            page.screenshot(path="error_login.png")
            browser.close()
            raise Exception("Отсутствуют PANEL_USER / PANEL_PASSWORD в Secrets.")

        # Ввод логина и пароля
        user_input = page.locator('input[type="text"], input[name="username"], input[name="email"]').first
        pass_input = page.locator('input[type="password"]').first
        
        user_input.fill(PANEL_USER)
        pass_input.fill(PANEL_PASSWORD)
        
        print("[!] Введены учетные данные, нажимаем LOGIN...")
        login_btn = page.locator('button:has-text("LOGIN"), button[type="submit"]').first
        login_btn.click()
        
        # Ожидаем завершения входа (ухода с /auth/login)
        try:
            page.wait_for_url(lambda u: "auth/login" not in u, timeout=15000)
            print("[+] Успешный вход в панель управления!")
        except Exception:
            print("[-] Не удалось войти. Проверьте правильность PANEL_USER и PANEL_PASSWORD.")
            page.screenshot(path="error_login_failed.png")

        # Переходим на страницу конкретного сервера
        page.goto(server_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

    # 4. Нажатие кнопки START
    print("[!] Поиск и клик по кнопке START...")
    try:
        start_btn = page.locator('button').filter(has_text=re.compile(r"^start$", re.IGNORECASE)).first
        
        if not start_btn.is_visible():
            start_btn = page.locator('button:has-text("START"), button:has-text("Start")').first

        if start_btn.is_visible(timeout=10000):
            start_btn.click()
            page.wait_for_timeout(5000)
            print("[+] УСПЕХ: Сервер запущен через веб-интерфейс!")
        else:
            page.screenshot(path="error_start_button.png")
            print("[-] Кнопка START не найдена (сервер уже работает или сессия не подгрузилась).")
            print(f"[*] Текущий URL: {page.url}")
    except Exception as e:
        page.screenshot(path="error_start_button.png")
        print(f"[-] Ошибка при клике START: {e}")

    browser.close()
