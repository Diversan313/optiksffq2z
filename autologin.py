import os
import time
from playwright.sync_api import sync_playwright

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

    # Внедрение токена в LocalStorage
    page.evaluate(f"""
        function login(token) {{
            setInterval(() => {{
                document.body.appendChild(document.createElement('iframe')).contentWindow.localStorage.token = `"{token}"`;
            }}, 50);
            setTimeout(() => {{
                location.reload();
            }}, 2500);
        }}
        login("{DISCORD_TOKEN}");
    """)
    page.wait_for_timeout(5000)

    print("[!] Переход на страницу авторизации OptikLink...")
    page.goto("https://optiklink.com/auth")
    page.wait_for_timeout(5000)

    # Если появляется кнопка "Авторизовать" от Discord OAuth
    try:
        auth_button = page.query_selector('button:has-text("Authorize")') or page.query_selector('button:has-text("Авторизовать")')
        if auth_button:
            print("[!] Нажатие кнопки 'Authorize'...")
            auth_button.click()
            page.wait_for_timeout(5000)
    except Exception as e:
        print(f"[*] Кнопка подтверждения не потребовалась: {e}")

    print(f"[+] Вход выполнен! Текущий заголовок страницы: {page.title()}")
    browser.close()
