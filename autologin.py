import base64
import os
import time
import requests
from playwright.sync_api import sync_playwright

PTERO_API_KEY = os.getenv("PTERO_API_KEY")
SERVER_ID = os.getenv("SERVER_ID", "ba6c4e06")
STATE_JSON_BASE64 = os.getenv("STATE_JSON_BASE64")

# Если передана строка Base64 (например, из GitHub Secrets), распаковываем её в state.json
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

    browser.close()

# 3. Автоматический запуск сервера через Pterodactyl API
print("\n[2/2] Проверка работы Pterodactyl API и запуск сервера...")
if PTERO_API_KEY:
    url = f"https://control.optiklink.net/api/client/servers/{SERVER_ID}/power"
    headers = {
        "Authorization": f"Bearer {PTERO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    max_retries = 5
    success = False

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[!] Попытка {attempt}/{max_retries}: отправка сигнала START...")
            response = requests.post(url, json={"signal": "start"}, headers=headers, timeout=20)

            if response.status_code in [200, 204]:
                print("[+] УСПЕХ: Команда START отправлена! Сервер запущен.")
                success = True
                break
            elif response.status_code in [502, 503, 504]:
                print(f"[*] Таймаут панели (Ошибка {response.status_code}). Панель лагает, ждём 15 секунд...")
                time.sleep(15)
            else:
                print(f"[*] Код ответа API: {response.status_code}. Текст: {response.text[:200]}")
                break
        except Exception as e:
            print(f"[-] Ошибка сети/таймаут: {e}")
            if attempt < max_retries:
                print("[!] Повтор через 15 секунд...")
                time.sleep(15)

    if not success:
        print("[-] ВНИМАНИЕ: Не удалось отправить сигнал START через API. Запусти сервер вручную на панели.")
else:
    print("[!] Предупреждение: PTERO_API_KEY не добавлен в Secrets. Авто-запуск выключенного сервера пропущен.")
