import datetime
import os
import threading
from flask import Flask
import telebot
from telebot import types
from yt_dlp import YoutubeDL

# 1. Веб-сервер 24/7 для Render
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is active 24/7!"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# 2. Настройки бота
TOKEN = "8863043974:AAFhOR9dwlFrzw_zcvSRnMyk8CM7xDs02aM".strip()
bot = telebot.TeleBot(TOKEN)

BOT_USERNAME = "@saverui_bot"
ADMIN_USERNAME = "@MediaFetch"
ADMIN_PASSWORD = "571634sav"

# Данные администраторов
admins = set()

# Хранилище данных
all_users = set()
vip_until = {}  # user_id: datetime окончания VIP
referrals = {}  # user_id: set(приглашенных_user_id)
user_states = {}  # user_id: текущее состояние ввода

# Промокоды по умолчанию
promocodes = {"abdufattoh": "Мамин вечный VIP (Без рекламы)"}

# Рекламный модуль (по умолчанию пустой)
custom_ad_text = ""
custom_ad_file_id = None
custom_ad_file_type = None


def is_vip(user_id):
    if user_id not in vip_until:
        return False
    return vip_until[user_id] > datetime.datetime.now()


def add_vip_days(user_id, days):
    now = datetime.datetime.now()
    if is_vip(user_id):
        vip_until[user_id] += datetime.timedelta(days=days)
    else:
        vip_until[user_id] = now + datetime.timedelta(days=days)


# Главное меню
def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📥 Как скачивать")
    btn2 = types.KeyboardButton("👑 VIP и Промокоды")
    btn3 = types.KeyboardButton("👥 Рефералы")
    btn4 = types.KeyboardButton("🎟 Ввести промокод")
    btn5 = types.KeyboardButton("📢 Заказать рекламу")

    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)

    if user_id in admins:
        markup.add(types.KeyboardButton("⚙️ Админ-панель"))

    return markup


# Старт
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    args = message.text.split()

    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if user_id not in all_users and referrer_id != user_id:
            if referrer_id not in referrals:
                referrals[referrer_id] = set()
            referrals[referrer_id].add(user_id)
            add_vip_days(referrer_id, 3)
            try:
                bot.send_message(
                    referrer_id,
                    "🎉 По вашей ссылке зарегистрировался новый пользователь!\n🎁 Вам зачислено +3 дня VIP!",
                )
            except Exception:
                pass

    all_users.add(user_id)
    user_states.pop(user_id, None)

    welcome_text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"Я скачиваю медиа из Instagram, TikTok и Pinterest.\n\n"
        f"🔗 Просто отправь мне ссылку на фото или видео!"
    )
    bot.send_message(
        user_id,
        welcome_text,
        reply_markup=main_keyboard(user_id),
    )


# Админка
@bot.message_handler(commands=["admin"])
def admin_login(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or args[1] != ADMIN_PASSWORD:
        bot.reply_to(message, "⛔️ Неверный пароль!")
        return

    admins.add(message.chat.id)
    bot.reply_to(
        message,
        "⚙️ Успешный вход в Админ-панель!",
        reply_markup=main_keyboard(message.chat.id),
    )


# Управление рекламой
@bot.message_handler(commands=["setad"])
def set_ad(message):
    global custom_ad_text, custom_ad_file_id, custom_ad_file_type
    if message.chat.id not in admins:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Напиши: /setad Текст твоей рекламы")
        return
    custom_ad_text = args[1].strip()
    custom_ad_file_id = None
    custom_ad_file_type = None
    bot.reply_to(
        message,
        f"✅ Текстовая реклама установлена:\n\n{custom_ad_text}",
    )


@bot.message_handler(commands=["setad_media"])
def set_ad_media(message):
    global custom_ad_text, custom_ad_file_id, custom_ad_file_type
    if message.chat.id not in admins:
        return

    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Ответь командой /setad_media Текст на фото/видео.")
        return

    reply = message.reply_to_message
    args = message.text.split(maxsplit=1)
    text = args[1].strip() if len(args) > 1 else ""

    if reply.photo:
        custom_ad_file_id = reply.photo[-1].file_id
        custom_ad_file_type = "photo"
    elif reply.video:
        custom_ad_file_id = reply.video.file_id
        custom_ad_file_type = "video"
    elif reply.animation:
        custom_ad_file_id = reply.animation.file_id
        custom_ad_file_type = "animation"
    else:
        bot.reply_to(message, "⚠️ Ответь на фото, видео или гифку.")
        return

    custom_ad_text = text
    bot.reply_to(message, "✅ Медиа-реклама установлена!")


@bot.message_handler(commands=["delad"])
def del_ad(message):
    global custom_ad_text, custom_ad_file_id, custom_ad_file_type
    if message.chat.id not in admins:
        return
    custom_ad_text = ""
    custom_ad_file_id = None
    custom_ad_file_type = None
    bot.reply_to(message, "✅ Реклама удалена.")


# Рассылки
@bot.message_handler(commands=["broadcast"])
def broadcast_msg(message):
    if message.chat.id not in admins:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Напиши: /broadcast Текст рассылки")
        return

    msg_text = args[1].strip()
    count = 0
    for u in list(all_users):
        try:
            bot.send_message(u, msg_text)
            count += 1
        except Exception:
            pass
    bot.reply_to(message, f"📢 Рассылка завершена! Отправлено {count} пользователям.")


# Создание промокодов
@bot.message_handler(commands=["addpromo"])
def add_promo(message):
    if message.chat.id not in admins:
        return

    args = message.text.split(maxsplit=3)
    if len(args) < 4 or not args[2].isdigit():
        bot.reply_to(message, "⚠️ Использование: /addpromo КОД ДНИ Описание")
        return

    code = args[1].strip()
    days = int(args[2])
    desc = args[3].strip()

    promocodes[code] = f"+{days} дней VIP ({desc})"
    bot.reply_to(message, f"✅ Промокод {code} на {days} дней успешно создан!")


# Кнопки меню
@bot.message_handler(
    func=lambda m: m.text
    in [
        "📥 Как скачивать",
        "👑 VIP и Промокоды",
        "👥 Рефералы",
        "🎟 Ввести промокод",
        "📢 Заказать рекламу",
        "⚙️ Админ-панель",
    ]
)
def handle_menu(message):
    user_id = message.chat.id
    user_states.pop(user_id, None)

    if message.text == "📥 Как скачивать":
        text = (
            "📌 Инструкция:\n\n"
            "1. Скопируй ссылку из Instagram, TikTok или Pinterest.\n"
            "2. Отправь её в этот чат.\n"
            "3. Получи файл в оригинальном качестве!"
        )
        bot.send_message(user_id, text)

    elif message.text == "👑 VIP и Промокоды":
        vip_active = is_vip(user_id)
        if vip_active:
            until_date = vip_until[user_id].strftime("%d.%m.%Y %H:%M")
            status = f"✅ АКТИВЕН (до {until_date})"
        else:
            status = "❌ Не активен"

        text = (
            f"👑 Ваш VIP-Статус: {status}\n\n"
            "Возможности VIP:\n"
            "• Без рекламы ✨\n"
            "• Максимальная скорость скачивания 🚀\n"
            "• Безлимитная загрузка ⚡️\n\n"
            "🎁 Как получить VIP бесплатно?\n"
            "• Приглашай друзей по своей ссылке (+3 дня за человека)\n"
            "• Активируй промокод кнопкой «🎟 Ввести промокод»"
        )
        bot.send_message(user_id, text)

    elif message.text == "👥 Рефералы":
        ref_count = len(referrals.get(user_id, []))
        ref_link = f"https://t.me/saverui_bot?start={user_id}"

        text = (
            "👥 Реферальная программа\n\n"
            f"Приглашено пользователей: {ref_count}\n"
            "Награда: +3 дня VIP за каждого друга! 🎁\n\n"
            "🔗 Ваша уникальная ссылка:\n"
            f"{ref_link}"
        )
        bot.send_message(user_id, text)

    elif message.text == "🎟 Ввести промокод":
        user_states[user_id] = "WAITING_PROMO"
        bot.send_message(user_id, "✏️ Отправь промокод ответным сообщением:")

    elif message.text == "📢 Заказать рекламу":
        text = (
            "📢 Размещение рекламы в боте\n\n"
            "Хотите привлечь новых клиентов или подписчиков?\n"
            "Ваш рекламный пост увидят все пользователи при скачивании медиа!\n\n"
            f"📩 По вопросам сотрудничества пишите админу: {ADMIN_USERNAME}"
        )
        bot.send_message(user_id, text)

    elif message.text == "⚙️ Админ-панель":
        if user_id not in admins:
            bot.send_message(user_id, "⛔️ Доступ запрещен.")
            return

        promo_list = "\n".join([f"• {code} — {desc}" for code, desc in promocodes.items()])
        text = (
            "⚙️ АДМИН-ПАНЕЛЬ\n\n"
            f"👥 Всего пользователей: {len(all_users)}\n"
            f"👑 VIP-пользователей: {sum(1 for u in all_users if is_vip(u))}\n\n"
            f"📢 Текущая реклама:\n{custom_ad_text if custom_ad_text else 'Отсутствует'}\n\n"
            f"🎟 Действующие промокоды:\n{promo_list}\n\n"
            "🛠 Команды админа:\n"
            "• /setad Текст — Установить текст рекламы\n"
            "• /setad_media Текст — Медиа-реклама (ответом на фото/видео)\n"
            "• /delad — Удалить рекламу\n"
            "• /broadcast Текст — Рассылка всем\n"
            "• /addpromo КОД ДНИ Описание — Создать промокод"
        )
        bot.send_message(user_id, text)


# Скачивание медиа и обработка промокодов
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.chat.id
    text = message.text.strip()

    # Ввод промокода
    if user_states.get(user_id) == "WAITING_PROMO":
        user_states.pop(user_id, None)

        if text in promocodes or text == "abdufattoh":
            if text == "abdufattoh":
                add_vip_days(user_id, 36500)
            else:
                add_vip_days(user_id, 30)

            bot.reply_to(
                message,
                f"🎉 Промокод {text} активирован!\n👑 Вам зачислен VIP-доступ!",
            )
        else:
            bot.reply_to(message, "❌ Неверный промокод.")
        return

    # Проверка ссылок
    valid_platforms = [
        "instagram.com",
        "tiktok.com",
        "pinterest.com",
        "pin.it",
        "vt.tiktok.com",
    ]
    if not any(p in text.lower() for p in valid_platforms):
        bot.reply_to(
            message,
            "⚠️ Отправь корректную ссылку на Instagram, TikTok или Pinterest.",
        )
        return

    status_msg = bot.reply_to(message, "⏳ Загрузка...")

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    ydl_opts = {
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(text, download=True)
            filename = ydl.prepare_filename(info)

        # Строго только эта надпись под медиафайлом!
        caption_text = f"Скачано через {BOT_USERNAME}"

        # 1. Отправляем сам файл
        ext = os.path.splitext(filename)[1].lower()
        with open(filename, "rb") as file:
            if ext in [".mp4", ".mov", ".avi", ".webm"]:
                bot.send_video(user_id, file, caption=caption_text)
            elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
                bot.send_photo(user_id, file, caption=caption_text)
            else:
                bot.send_document(user_id, file, caption=caption_text)

        # 2. Если у пользователя НЕТ VIP и реклама была задана админом — отправляем РЕКЛАМУ ОТДЕЛЬНО
        vip = is_vip(user_id)
        if not vip:
            if custom_ad_file_id:
                try:
                    if custom_ad_file_type == "photo":
                        bot.send_photo(user_id, custom_ad_file_id, caption=custom_ad_text)
                    elif custom_ad_file_type == "video":
                        bot.send_video(user_id, custom_ad_file_id, caption=custom_ad_text)
                    elif custom_ad_file_type == "animation":
                        bot.send_animation(user_id, custom_ad_file_id, caption=custom_ad_text)
                except Exception:
                    pass
            elif custom_ad_text:
                try:
                    bot.send_message(user_id, custom_ad_text)
                except Exception:
                    pass

        if os.path.exists(filename):
            os.remove(filename)

        bot.delete_message(user_id, status_msg.message_id)

    except Exception as e:
        err_text = str(e)[:150]
        bot.edit_message_text(
            f"❌ Ошибка скачивания:\n{err_text}",
            chat_id=user_id,
            message_id=status_msg.message_id,
        )


if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling(non_stop=True)
