import os
from playwright.sync_api import sync_playwright

# Получаем токен из переменных окружения GitHub Secrets
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    print("[-] Ошибка: DISCORD_TOKEN не найден в Secrets!")
    exit(1)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    print("[!] Авторизация в Discord через токен...")
    page.goto("https://discord.com/login")
    page.wait_for_timeout(2000)

    # Безопасная инъекция токена в LocalStorage
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

    # Нажатие кнопки подтверждения Discord OAuth (если появляется)
    try:
        auth_button = page.query_selector('button:has-text("Authorize")') or page.query_selector('button:has-text("Авторизовать")')
        if auth_button:
            print("[!] Нажатие кнопки 'Authorize'...")
            auth_button.click()
            page.wait_for_timeout(4000)
    except Exception as e:
        print(f"[*] Перенаправление прошло автоматически: {e}")

    # Переход в Dashboard и жесткая проверка успешности
    print("[!] Проверка доступа к Dashboard...")
    page.goto("https://optiklink.com/dashboard")
    page.wait_for_timeout(3000)

    current_url = page.url
    if "dashboard" in current_url:
        print(f"[+] УСПЕХ: Вход выполнен, 3-дневный таймер OptikLink сброшен! URL: {current_url}")
    else:
        print(f"[-] ОШИБКА: Не удалось зайти в Dashboard. Текущий URL: {current_url}")
        browser.close()
        # Вызов ошибки окрасит запуск в GitHub Actions в красный цвет
        raise Exception("Авторизация не удалась. Проверьте актуальность DISCORD_TOKEN.")

    browser.close()
