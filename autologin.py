import os
import time
import requests
from playwright.sync_api import sync_playwright

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PTERO_API_KEY = os.getenv("PTERO_API_KEY")
SERVER_ID = os.getenv("SERVER_ID", "ba6c4e06") # ID сервера из URL control.optiklink.net

if not DISCORD_TOKEN:
    print("[-] КРИТИЧЕСКАЯ ОШИБКА: DISCORD_TOKEN не найден в GitHub Secrets!")
    exit(1)

print("[1/2] Запуск браузера для продления 3-дневного таймера...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # 1. Авторизация в Discord через токен
    print("[!] Авторизация в Discord...")
    page.goto("https://discord.com/login")
    page.wait_for_timeout(2000)

    page.evaluate("""(token) => {
        setInterval(() => {
            document.body.appendChild(document.createElement('iframe')).contentWindow.localStorage.token = `"${token}"`;
        }, 50);
        setTimeout(() => { location.reload(); }, 2500);
    }""", DISCORD_TOKEN)

    page.wait_for_timeout(5000)

    # 2. Переход на страницу OAuth OptikLink
    print("[!] Переход на страницу авторизации OptikLink...")
    page.goto("https://optiklink.net/auth")
    page.wait_for_timeout(4000)

    # Кликом подтверждаем OAuth, если появляется кнопка Discord
    try:
        auth_button = page.query_selector('button:has-text("Authorize")') or page.query_selector('button:has-text("Авторизовать")')
        if auth_button:
            print("[!] Нажатие кнопки 'Authorize'...")
            auth_button.click()
            page.wait_for_timeout(5000)
    except Exception as e:
        print(f"[*] Информация об OAuth: {e}")

    # 3. Переход в Dashboard и Настоящая проверка элемента
    print("[!] Переход в Dashboard и проверка авторизации...")
    page.goto("https://optiklink.net/dashboard")
    page.wait_for_timeout(4000)

    html_content = page.content()

    # Проверяем не по URL, а по наличию элементов авторизованного пользователя
    if "Create Server" in html_content or "Logout" in html_content or "Servers" in html_content:
        print("[+] НАСТОЯЩИЙ УСПЕХ: Авторизация пройдена, 3-дневный таймер продлен!")
    else:
        print("[-] ОШИБКА: Авторизация НЕ прошла. Скрипт попал на незалогиненную страницу.")
        browser.close()
        raise Exception("Не удалось зайти в Dashboard OptikLink. Проверь DISCORD_TOKEN.")

    browser.close()

# 4. Автоматический запуск сервера через Pterodactyl API (с повторами при 504 ошибках)
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
        print("[-] ВНИМАНИЕ: Не удалось отправить сигнал START через API. Запусти сервер вручную на панеле.")
else:
    print("[!] Предупреждение: PTERO_API_KEY не добавлен в Secrets. Авто-запуск выключенного сервера пропущен.")
