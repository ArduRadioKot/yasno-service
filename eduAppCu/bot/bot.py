import os
import sys
from pathlib import Path

import telebot
from telebot import types
from dotenv import load_dotenv

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from services.db import create_premium_key, init_db, list_premium_keys


def load_bot_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        return token

    keys_file = Path(__file__).parent / "keys.txt"
    if keys_file.exists():
        with keys_file.open("r", encoding="utf-8") as file:
            for line in file:
                value = line.strip()
                if value:
                    return value

    raise RuntimeError(
        "Telegram bot token not found. Set TELEGRAM_BOT_TOKEN in backend/.env "
        "or put the token on the first line of bot/keys.txt"
    )


def load_admin_ids() -> list[int]:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "").strip()
    if not raw:
        return []
    return [int(item.strip()) for item in raw.split(",") if item.strip().isdigit()]


BOT_TOKEN = load_bot_token()
ADMIN_IDS = load_admin_ids()
bot = telebot.TeleBot(BOT_TOKEN)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            text="💳 Оплатить подписку",
            callback_data="pay",
        )
    )

    bot.send_message(
        message.from_user.id,
        "👋 Привет! Я бот для активации премиум подписки в сервисе yasnenko.ru!\n\n"
        "Этот сервис предназначен для подготовки к экзаменам с персональным ИИ-ментором.\n\n"
        "Нажмите кнопку ниже для оплаты подписки или используйте команду /help для справки.",
        reply_markup=markup,
    )


@bot.message_handler(commands=["help"])
def send_help(message):
    help_text = """
/start - Начало работы
/help - Справка по командам
/generate - Сгенерировать ключ (только для администратора)
/keys - Показать список ключей (только для администратора)
/pay - Оплатить подписку
"""

    if is_admin(message.from_user.id):
        bot.send_message(message.from_user.id, help_text)
    else:
        bot.send_message(
            message.from_user.id,
            "/start - Начало работы\n/help - Справка по командам\n/pay - Оплатить подписку",
        )


@bot.message_handler(commands=["generate"])
def generate_premium_key_cmd(message):
    if not is_admin(message.from_user.id):
        bot.send_message(
            message.from_user.id,
            "❌ Эта команда доступна только администраторам",
        )
        return

    try:
        key = create_premium_key(duration_days=30)
        bot.send_message(
            message.from_user.id,
            "✅ Ключ премиум подписки создан!\n\n"
            f"🔑 Ключ: `{key}`\n\n"
            "Срок: 30 дней после активации в приложении\n\n"
            "Пользователь может активировать этот ключ в профиле.",
            parse_mode="Markdown",
        )
    except Exception as error:
        bot.send_message(
            message.from_user.id,
            f"❌ Ошибка при создании ключа: {error}",
        )


@bot.message_handler(commands=["keys"])
def list_keys_cmd(message):
    if not is_admin(message.from_user.id):
        bot.send_message(
            message.from_user.id,
            "❌ Эта команда доступна только администраторам",
        )
        return

    try:
        keys = list_premium_keys(limit=10)

        if not keys:
            bot.send_message(message.from_user.id, "📭 Нет созданных ключей")
            return

        response = "📋 Последние 10 ключей:\n\n"
        for key_data in keys:
            status = "✅ Активен" if key_data["is_active"] else "❌ Деактивирован"
            used = "✔️ Использован" if key_data["is_used"] else "⏳ Доступен"
            expires = key_data.get("expires_at") or "после активации"

            response += (
                f"🔑 {key_data['key']}\n"
                f"   Статус: {status}\n"
                f"   Используется: {used}\n"
                f"   Истекает: {expires}\n"
                f"   Создан: {key_data.get('created_at', 'N/A')}\n\n"
            )

        bot.send_message(message.from_user.id, response)
    except Exception as error:
        bot.send_message(
            message.from_user.id,
            f"❌ Ошибка при получении ключей: {error}",
        )


@bot.callback_query_handler(func=lambda call: call.data == "pay")
def handle_payment(call):
    try:
        prices = [types.LabeledPrice(label="Премиум подписка", amount=10000)]

        bot.send_invoice(
            call.from_user.id,
            title="Премиум подписка yasnenko.ru",
            description="Доступ к ИИ-ментору для подготовки к экзаменам на 30 дней",
            invoice_payload="premium_subscription",
            provider_token="",
            currency="XTR",
            prices=prices,
            is_flexible=False,
        )
    except Exception as error:
        bot.send_message(
            call.from_user.id,
            f"❌ Ошибка при инициации платежа: {error}",
        )


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def handle_successful_payment(message):
    try:
        key = create_premium_key(duration_days=30)

        bot.send_message(
            message.from_user.id,
            "✅ Спасибо за оплату!\n\n"
            "🎉 Ваш ключ премиум подписки готов!\n\n"
            f"🔑 Ваш ключ активации:\n`{key}`\n\n"
            "📝 Как активировать:\n"
            "1. Откройте приложение yasnenko.ru\n"
            "2. Перейдите в профиль\n"
            "3. Вставьте ключ в раздел «Премиум подписка»\n"
            "4. Нажмите «Активировать»\n\n"
            "✨ После активации откроется доступ к ИИ-ментору!",
            parse_mode="Markdown",
        )
    except Exception as error:
        bot.send_message(
            message.from_user.id,
            f"❌ Ошибка при генерации ключа: {error}\n\n"
            "Пожалуйста, обратитесь в поддержку.",
        )


@bot.message_handler(commands=["pay"])
def pay_command(message):
    handle_payment(
        types.CallbackQuery(
            id="0",
            from_user=message.from_user,
            chat_instance="0",
            data="pay",
        )
    )


if __name__ == "__main__":
    init_db()
    print("🤖 Бот запущен и готов к работе...")
    bot.infinity_polling()
