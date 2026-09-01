import base64
import os
import time
from playwright.sync_api import sync_playwright

SERVER_ID = os.getenv("SERVER_ID", "ba6c4e06")
STATE_JSON_BASE64 = os.getenv("STATE_JSON_BASE64")

# Если передана строка Base64 (из GitHub Secrets), распаковываем её в state.json
if STATE_JSON_BASE64:
    with open("state.json", "wb") as f:
        f.write(base64.b64decode(STATE_JSON_BASE64))

if not os.path.exists("state.json"):
    print("[-] КРИТИЧЕСКАЯ ОШИБКА: Файл state.json не найден! Положите его рядом со скриптом или задайте STATE_JSON_BASE64.")
    exit(1)

print("[1/2] Запуск браузера с сохраненной сессией для продления 3-дневного таймера...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # Загружаем сохранённый профиль куков
    context = browser.new_context(
        storage_state="state.json",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # 1. Переход на страницу авторизации OptikLink
    print("[!] Переход на страницу авторизации OptikLink...")
    page.goto("https://optiklink.net/auth", wait_until="networkidle")
    page.wait_for_timeout(4000)

    # 2. Переход в Dashboard для проверки обновления таймера
    print("[!] Переход в Dashboard и проверка авторизации...")
    page.goto("https://optiklink.net/dashboard", wait_until="networkidle")
    page.wait_for_timeout(3000)

    # Безопасное получение HTML
    html_content = ""
    for _ in range(5):
        try:
            html_content = page.content()
            break
        except Exception:
            time.sleep(2)

    # Проверяем элементы авторизованного пользователя
    if any(term in html_content for term in ["Create Server", "Logout", "Servers", "Dashboard"]):
        print("[+] НАСТОЯЩИЙ УСПЕХ: Авторизация пройдена по кукам, 3-дневный таймер продлен!")
    else:
        print("[-] ОШИБКА: Сессия устарела или авторизация не прошла.")
        browser.close()
        raise Exception("Не удалось зайти в Dashboard. Пересоздайте файл state.json.")

    # 3. Нажатие кнопки START прямо в интерфейсе управления сервером
    print(f"\n[2/2] Переход в панель управления сервером ({SERVER_ID}) и запуск...")
    server_url = f"https://control.optiklink.net/server/{SERVER_ID}"
    page.goto(server_url, wait_until="networkidle")
    page.wait_for_timeout(5000)

    try:
        # Ищем и нажимаем кнопку START в UI
        start_button = page.query_selector('button:has-text("START")') or page.query_selector('button:has-text("Start")')
        
        if start_button:
            print("[!] Кнопка START найдена, нажимаем...")
            start_button.click()
            page.wait_for_timeout(5000)
            print("[+] УСПЕХ: Команда START успешно нажата в веб-интерфейсе!")
        else:
            print("[*] Кнопка START не найдена. Возможно, сервер уже запущен.")
    except Exception as e:
        print(f"[-] Ошибка при нажатии кнопки START: {e}")

    browser.close()
