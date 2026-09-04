from playwright.sync_api import sync_playwright
import base64
from pathlib import Path


def main():
    print("=" * 60)
    print("  Мастер создания сессии для панели OptikLink")
    print("=" * 60)
    print()
    print("Данный скрипт формирует файл состояния браузера (storage state),")
    print("который в дальнейшем используется в GitHub Actions для")
    print("автоматического продления доступа и запуска сервера.")
    print()

    # --- Вопрос про прокси ---
    use_proxy = input(
        "Требуется ли использовать прокси? (если сайт недоступен напрямую). [y/N]: "
    ).strip().lower()

    proxy_config = None
    if use_proxy in ("y", "yes", "д", "да"):
        port = input(
            "Укажите порт локального прокси-сервера (например, 10808 или 7890): "
        ).strip()
        if not port.isdigit():
            print("Ошибка: порт должен быть указан числом. Выполнение прервано.")
            return

        proxy_config = {"server": f"http://127.0.0.1:{port}"}
        print(f"\nПрокси успешно настроен: http://127.0.0.1:{port}")
    else:
        print("\nПрокси использоваться не будет.")

    print()
    print("-" * 60)
    print("Порядок действий:")
    print("1. Сейчас будет открыто окно браузера.")
    print("2. Пройдите авторизацию на сайте control.optiklink.net.")
    print("3. После успешного входа в панель управления вернитесь")
    print("   в это окно терминала и нажмите Enter для продолжения.")
    print("-" * 60)
    print()
    input("Нажмите Enter, чтобы открыть браузер...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context_options = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        if proxy_config:
            context_options["proxy"] = proxy_config

        context = browser.new_context(**context_options)
        page = context.new_page()

        try:
            page.goto("https://control.optiklink.net", timeout=60000)
        except Exception as e:
            print(f"\nПредупреждение: страницу не удалось загрузить автоматически ({e}).")
            print("Пожалуйста, обновите страницу вручную в открытом окне браузера.")

        input("\n>>> После успешного входа в панель нажмите Enter... ")

        # Сохраняем состояние сессии
        context.storage_state(path="state.json")
        browser.close()

    # Формируем строку в формате base64
    state_bytes = Path("state.json").read_bytes()
    b64 = base64.b64encode(state_bytes).decode("ascii")

    print()
    print("=" * 60)
    print("  Сессия успешно сохранена")
    print("=" * 60)
    print()
    print("Скопируйте приведённую ниже строку целиком и добавьте её")
    print("в GitHub Secrets репозитория под именем:  STATE_JSON_BASE64")
    print()
    print("-" * 60)
    print(b64)
    print("-" * 60)
    print()
    print("Файл state.json также сохранён в текущей рабочей папке — на случай,")
    print("если он понадобится повторно.")
    print()


if __name__ == "__main__":
    main()
