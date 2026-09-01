import base64
import os
import time
from playwright.sync_api import sync_playwright

# Защита: если secret SERVER_ID не задан или пустой (""), берем "ba6c4e06"
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
    print("[!] Переход на страницу авторизации OptikLink...")
    try:
        page.goto("https://optiklink.net/auth", wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"[*] Предупреждение при переходе на /auth: {e}")
    page.wait_for_timeout(4000)

    print("[!] Переход в Dashboard и проверка авторизации...")
    try:
        page.goto("https://optiklink.net/dashboard", wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"[*] Предупреждение при переходе на /dashboard: {e}")
    page.wait_for_timeout(3000)

    html_content = page.content()
    if any(term in html_content for term in ["Create Server", "Logout", "Servers", "Dashboard"]):
        print("[+] НАСТОЯЩИЙ УСПЕХ: Авторизация пройдена по кукам, 3-дневный таймер продлен!")
    else:
        print("[-] ОШИБКА: Сессия устарела.")
        browser.close()
        raise Exception("Не удалось зайти в Dashboard OptikLink.")

    # 2. Клик по кнопке START в панели Pterodactyl
    print(f"\n[2/2] Переход в панель управления сервером ({SERVER_ID}) и запуск...")
    server_url = f"https://control.optiklink.net/server/{SERVER_ID}"
    try:
        page.goto(server_url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"[*] Предупреждение при открытии панели сервера: {e}")

    try:
        # Ждём появления кнопки START (до 20 секунд)
        start_btn = page.wait_for_selector('button:has-text("START")', timeout=20000)
        if start_btn:
            print("[!] Кнопка START найдена, отправляем клик...")
            start_btn.click()
            page.wait_for_timeout(5000)
            print("[+] УСПЕХ: Сервер запущен через веб-интерфейс!")
    except Exception as e:
        print(f"[*] Не удалось нажать START (возможно, сервер уже работает или заблокирован): {e}")

    browser.close()
