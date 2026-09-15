import datetime
import os
import threading
from flask import Flask
import telebot
from telebot import types
from yt_dlp import YoutubeDL

# Веб-сервер для Render
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is active!"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# Конфигурация
TOKEN = "8559877177:AAEunCisHcxHZLYiN74i9zLA63L49GT-xQ0"
bot = telebot.TeleBot(TOKEN)

BOT_USERNAME = "@fozis_bot"
ADMIN_USERNAME = "@MediaFetch"
ADMIN_PASSWORD = "571634sav"

admins = set()
all_users = set()
vip_until = {}
referrals = {}
user_states = {}
promocodes = {"abdufattoh": "Вечный VIP"}

# Настройки рекламы
custom_ad_text = ""
custom_ad_file_id = None
custom_ad_file_type = None

# Настройки обязательной подписки (ОП)
required_channel_id = None  # Например: "@my_channel" или ID -100xxx
required_channel_url = None  # Ссылка на канал


def is_vip(user_id):
    return (
        user_id in vip_until and vip_until[user_id] > datetime.datetime.now()
    )


def add_vip_days(user_id, days):
    now = datetime.datetime.now()
    if is_vip(user_id):
        vip_until[user_id] += datetime.timedelta(days=days)
    else:
        vip_until[user_id] = now + datetime.timedelta(days=days)


def check_subscription(user_id):
    if not required_channel_id:
        return True
    try:
        member = bot.get_chat_member(required_channel_id, user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return True


def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("👑 VIP"))
    markup.add(
        types.KeyboardButton("🟩 👥 Рефералы"),
        types.KeyboardButton("🟩 🎟 Ввести промокод"),
    )
    markup.add(types.KeyboardButton("📢 Заказать рекламу"))
    if user_id in admins:
        markup.add(types.KeyboardButton("⚙️ Админ-панель"))
    return markup


@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if user_id not in all_users and ref_id != user_id:
            referrals.setdefault(ref_id, set()).add(user_id)
            add_vip_days(ref_id, 3)
            try:
                bot.send_message(
                    ref_id,
                    "🎉 По вашей ссылке зарегистрировался друг!\n🟢 Вам зачислено +3 дня VIP!",
                )
            except Exception:
                pass

    all_users.add(user_id)
    user_states.pop(user_id, None)
    bot.send_message(
        user_id,
        f"👋 Привет, {message.from_user.first_name}!\n\nОтправь мне ссылку на видео или фото из Instagram, TikTok или Pinterest!",
        reply_markup=main_keyboard(user_id),
    )


@bot.message_handler(commands=["admin"])
def admin_login(message):
    args = message.text.split(maxsplit=1)
    if len(args) >= 2 and args[1] == ADMIN_PASSWORD:
        admins.add(message.chat.id)
        bot.reply_to(
            message,
            "⚙️ Успешный вход в Админ-панель!\n\n"
            "Команды админа:\n"
            "• /setsub @channel_username link - поставить обязательную подписку\n"
            "• /removesub - убрать обязательную подписку\n"
            "• /broadcast текст - рассылка текста всем юзерам\n"
            "• /setad текст - установить рекламу под медиа\n"
            "• /delad - удалить рекламу",
            reply_markup=main_keyboard(message.chat.id),
        )
    else:
        bot.reply_to(message, "⛔️ Неверный пароль!")


# Управление обязательной подпиской
@bot.message_handler(commands=["setsub"])
def set_subscription(message):
    global required_channel_id, required_channel_url
    if message.chat.id not in admins:
        return
    args = message.text.split(maxsplit=2)
    if len(args) >= 3:
        required_channel_id = args[1]
        required_channel_url = args[2]
        bot.reply_to(
            message,
            f"✅ Обязательная подписка установлена на {required_channel_id}!",
        )
    else:
        bot.reply_to(
            message, "⚠️ Использование: `/setsub @username_канала https://t.me/link`"
        )


@bot.message_handler(commands=["removesub"])
def remove_subscription(message):
    global required_channel_id, required_channel_url
    if message.chat.id not in admins:
        return
    required_channel_id = None
    required_channel_url = None
    bot.reply_to(message, "✅ Обязательная подписка отключена!")


# Управление рекламой и рассылкой
@bot.message_handler(commands=["setad"])
def set_ad(message):
    global custom_ad_text
    if message.chat.id not in admins:
        return
    args = message.text.split(maxsplit=1)
    if len(args) >= 2:
        custom_ad_text = args[1]
        bot.reply_to(message, "✅ Текст рекламы сохранён!")


@bot.message_handler(commands=["delad"])
def del_ad(message):
    global custom_ad_text
    if message.chat.id not in admins:
        return
    custom_ad_text = ""
    bot.reply_to(message, "✅ Реклама удалена!")


@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if message.chat.id not in admins:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Использование: `/broadcast Текст рассылки`")
        return
    text = args[1]
    count = 0
    for u in all_users:
        try:
            bot.send_message(u, text)
            count += 1
        except Exception:
            pass
    bot.reply_to(message, f"📢 Рассылка завершена. Успешно отправлено: {count}")


@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    if check_subscription(call.message.chat.id):
        bot.answer_callback_query(
            call.id, "✅ Подписка подтверждена! Теперь можно скачивать."
        )
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Вы всё ещё не подписались!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_vip_"))
def handle_vip_buy(call):
    plan = call.data.split("_")[2]

    if plan == "free":
        ref_link = f"https://t.me/fozis_bot?start={call.message.chat.id}"
        bot.send_message(
            call.message.chat.id,
            f"🎁 **Бесплатный VIP-тариф:**\n\nПриглашай друзей по своей ссылке и получай **+3 дня VIP** за каждого!\n\n🔗 Твоя ссылка:\n`{ref_link}`",
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id)
        return

    plans = {
        "1m": ("VIP Доступ — 1 Месяц", "vip_1m", 10),
        "1y": ("VIP Доступ — 1 Год", "vip_1y", 100),
        "forever": ("VIP Доступ — Навсегда", "vip_forever", 250),
    }
    if plan in plans:
        title, payload, price = plans[plan]
        bot.send_invoice(
            call.message.chat.id,
            title=title,
            description="VIP Подписка в Saver UI",
            invoice_payload=payload,
            provider_token="",
            currency="XTR",
            prices=[types.LabeledPrice(label=title, amount=price)],
            start_parameter="buy_vip",
        )
    bot.answer_callback_query(call.id)


@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.successful_payment_handler(func=lambda message: True)
def process_successful_payment(message):
    user_id = message.chat.id
    p = message.successful_payment.invoice_payload
    days = 30 if p == "vip_1m" else (365 if p == "vip_1y" else 36500)
    add_vip_days(user_id, days)
    bot.send_message(
        user_id, "🎉 Спасибо за покупку! VIP-статус успешно активирован."
    )


@bot.message_handler(
    func=lambda m: m.text
    in [
        "👑 VIP",
        "🟩 👥 Рефералы",
        "🟩 🎟 Ввести промокод",
        "📢 Заказать рекламу",
        "⚙️ Админ-панель",
    ]
)
def handle_menu(message):
    user_id = message.chat.id
    user_states.pop(user_id, None)

    if message.text == "👑 VIP":
        status = (
            f"✅ АКТИВЕН (до {vip_until[user_id].strftime('%d.%m.%Y')})"
            if is_vip(user_id)
            else "❌ Не активен"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "🟢 3 дня VIP — БЕСПЛАТНО (за 1 реферала)",
                callback_data="buy_vip_free",
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "⭐ 1 месяц (10 ⭐️)", callback_data="buy_vip_1m"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "⭐ 1 год (100 ⭐️)", callback_data="buy_vip_1y"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "⭐ Навсегда (250 ⭐️)", callback_data="buy_vip_forever"
            )
        )
        bot.send_message(
            user_id,
            f"👑 **Ваш VIP-Статус:** {status}\n\nВыберите подходящий тариф:",
            parse_mode="Markdown",
            reply_markup=markup,
        )
    elif message.text == "🟩 👥 Рефералы":
        bot.send_message(
            user_id,
            f"👥 **Реферальная программа**\n\nТвоя ссылка:\nhttps://t.me/fozis_bot?start={user_id}\n\n🟢 За каждого перешедшего друга ты получишь **+3 дня VIP**!",
        )
    elif message.text == "🟩 🎟 Ввести промокод":
        user_states[user_id] = "WAITING_PROMO"
        bot.send_message(user_id, "✏️ Отправь промокод ответным сообщением:")
    elif message.text == "📢 Заказать рекламу":
        bot.send_message(user_id, f"📩 Пиши админу: {ADMIN_USERNAME}")
    elif message.text == "⚙️ Админ-панель" and user_id in admins:
        bot.send_message(
            user_id,
            f"⚙️ АДМИНКА\nЮзеров: {len(all_users)}\nVIP: {sum(1 for u in all_users if is_vip(u))}\nОП Подписка: {'Включена' if required_channel_id else 'Выключена'}",
        )


@bot.message_handler(func=lambda message: True)
def handle_download(message):
    user_id = message.chat.id
    text = message.text.strip() if message.text else ""

    if user_states.get(user_id) == "WAITING_PROMO":
        user_states.pop(user_id, None)
        if text in promocodes or text == "abdufattoh":
            add_vip_days(user_id, 36500 if text == "abdufattoh" else 30)
            bot.reply_to(message, "🎉 VIP успешно активирован!")
        else:
            bot.reply_to(message, "❌ Неверный промокод.")
        return

    # Проверка обязательной подписки
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        if required_channel_url:
            markup.add(
                types.InlineKeyboardButton(
                    "📢 Подписаться на канал", url=required_channel_url
                )
            )
        markup.add(
            types.InlineKeyboardButton(
                "✅ Я подписался", callback_data="check_sub"
            )
        )
        bot.reply_to(
            message,
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=markup,
        )
        return

    if not any(
        p in text.lower()
        for p in [
            "instagram.com",
            "tiktok.com",
            "pinterest.com",
            "pin.it",
            "vt.tiktok.com",
        ]
    ):
        bot.reply_to(
            message, "⚠️ Отправь ссылку на Instagram, TikTok или Pinterest."
        )
        return

    status_msg = bot.reply_to(message, "⏳ Загрузка...")
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # Ускоренные опции скачивания через yt-dlp
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 10,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(text, download=True)
            filename = ydl.prepare_filename(info)

        caption_text = f"✅ Скачано через {BOT_USERNAME}"
        if custom_ad_text and not is_vip(user_id):
            caption_text += f"\n\n📢 {custom_ad_text}"

        ext = os.path.splitext(filename)[1].lower()
        with open(filename, "rb") as file:
            if ext in [".mp4", ".mov", ".avi", ".webm"]:
                bot.send_video(user_id, file, caption=caption_text)
            else:
                bot.send_photo(user_id, file, caption=caption_text)

        if os.path.exists(filename):
            os.remove(filename)
        bot.delete_message(user_id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка загрузки: {str(e)[:100]}",
            chat_id=user_id,
            message_id=status_msg.message_id,
        )


if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling(non_stop=True)
