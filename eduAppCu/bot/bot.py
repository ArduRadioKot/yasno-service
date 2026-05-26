import telebot
from telebot import types
file_name = 'keys.txt'
import secrets

alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

def generate_key():
    parts = []
    for _ in range(4):
        parts.append(
            ''.join(secrets.choice(alphabet) for _ in range(5))
        )
    return '-'.join(parts)

with open(file_name, 'r') as f:
    for i, line in enumerate(f):
        if i == 0:
            tg_key = line.strip()
            break
    
bot = telebot.TeleBot(tg_key);

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text == "/start":
        markup = types.InlineKeyboardMarkup()
        pay_button = types.InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="pay")
        markup.add(pay_button)
        bot.send_message(message.from_user.id, "Привет! Я бот для оплаты премиум подписки в сервисе yasnenko.ru! Этот сервис предназначен для подготовки к экзаменам с персональным ИИ-ментором. Нажмите на кнопку ниже для оплаты подписки.", reply_markup=markup)
    elif message.text == "/generate":
        key = generate_key()
        bot.send_message(message.from_user.id, "Твой ключ для подписки готов! Вставь его в личном кабинете в поле с подпиской!" + " " + key)
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю( Напиши /start")

@bot.callback_query_handler(func=lambda call: call.data == "pay")
def handle_payment(call):
    prices = [types.LabeledPrice(label="Премиум подписка", amount=100)]  # 1 XTR (Telegram Stars)
    bot.send_invoice(
        call.from_user.id,
        title="Премиум подписка yasnenko.ru",
        description="Доступ к ИИ-ментору для подготовки к экзаменам",
        invoice_payload="premium_subscription",
        provider_token="", 
        currency="XTR", 
        prices=prices,
        is_flexible=False
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    key = generate_key()
    bot.send_message(message.from_user.id, f"✅ Оплата прошла успешно!\n\nТвой ключ для подписки готов! Вставь его в личном кабинете в поле с подпиской:\n\n{key}")

bot.polling(none_stop=True, interval=0)