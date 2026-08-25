import os
import requests
from playwright.sync_api import sync_playwright

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PTERO_API_KEY = os.getenv("PTERO_API_KEY")
SERVER_ID = "ba6c4e06"  # ID контейнера из ссылки control.optiklink.net

if not DISCORD_TOKEN:
    print("[-] Ошибка: DISCORD_TOKEN не найден в Secrets!")
    exit(1)

# 1. Веб-авторизация для сброса 3-дневного таймера удаления
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    print("[!] Авторизация в Discord через токен...")
    page.goto("https://discord.com/login")
    page.wait_for_timeout(2000)

    # Внедрение токена в LocalStorage
    page.evaluate("""(token) => {
        setInterval(() => {
            document.body.appendChild(document.createElement('iframe')).contentWindow.localStorage.token = `"${token}"`;
        }, 50);
        setTimeout(() => {
            location.reload();
        }, 2500);
    }""", DISCORD_TOKEN)

    page.wait_for_timeout(4000)

    print("[!] Переход на страницу авторизации OptikLink...")
    page.goto("https://optiklink.com/auth")
    page.wait_for_timeout(4000)

    # Нажатие кнопки подтверждения Discord OAuth (если требуется)
    try:
        auth_button = page.query_selector('button:has-text("Authorize")') or page.query_selector('button:has-text("Авторизовать")')
        if auth_button:
            print("[!] Нажатие кнопки 'Authorize'...")
            auth_button.click()
            page.wait_for_timeout(4000)
    except Exception as e:
        print(f"[*] Перенаправление прошло автоматически: {e}")

    # Проверка захода на Dashboard (.com или .net)
    print("[!] Проверка доступа к Dashboard...")
    page.goto("https://optiklink.net/dashboard")
    page.wait_for_timeout(3000)

    current_url = page.url
    if "dashboard" in current_url or "optiklink" in current_url:
        print(f"[+] УСПЕХ: Вход выполнен, 3-дневный таймер OptikLink сброшен! URL: {current_url}")
    else:
        print(f"[-] ОШИБКА: Не удалось зайти в Dashboard. Текущий URL: {current_url}")
        browser.close()
        raise Exception("Авторизация не удалась. Проверьте актуальность DISCORD_TOKEN.")

    browser.close()

# 2. Автоматический запуск сервера через Pterodactyl API (если сервер перешёл в OFFLINE)
if PTERO_API_KEY:
    print("[!] Отправка сигнала START в Pterodactyl Panel...")
    url = f"https://control.optiklink.net/api/client/servers/{SERVER_ID}/power"
    headers = {
        "Authorization": f"Bearer {PTERO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        response = requests.post(url, json={"signal": "start"}, headers=headers)
        if response.status_code in [204, 200]:
            print("[+] УСПЕХ: Команда START отправлена! Сервер запускается.")
        else:
            print(f"[*] Ответ API ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[-] Ошибка отправки запроса к API: {e}")
else:
    print("[!] Предупреждение: PTERO_API_KEY не задан в Secrets, авто-старт пропущен.")
