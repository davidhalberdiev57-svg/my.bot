import os
import threading
import datetime
import subprocess
from flask import Flask
import telebot
from telebot import types
from yt_dlp import YoutubeDL

# Автоматическое обновление yt-dlp при запуске
try:
    subprocess.run(["pip", "install", "--upgrade", "yt-dlp"], check=True)
except Exception as e:
    print(f"Ошибка обновления yt-dlp: {e}")

# 1. Веб-сервер 24/7 для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. Настройки бота
TOKEN = "8863043974:AAFhOR9dwlFrzw_zcvSRnMyk8CM7xDs02aM".strip()
bot = telebot.TeleBot(TOKEN)

BOT_USERNAME = "@saverui_bot"
ADMIN_USERNAME = "@MediaFetch"
ADMIN_PASSWORD = "571634sav"

# Хранилище
admins = set()
all_users = set()
vip_until = {}       # user_id: datetime окончания
referrals = {}       # user_id: set(приглашенных)
user_states = {}     # user_id: состояние

# Промокоды
promocodes = {
    "abdufattoh": "Мамин вечный VIP"
}

# Рекламный модуль
custom_ad_text = "Используй промокод `abdufattoh` для отключения рекламы!"
custom_ad_file_id = None      # ID медиафайла для рекламы
custom_ad_file_type = None    # photo, video, animation

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

# Главная клавиатура
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

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    args = message.text.split()

    # Реферальная система
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if user_id not in all_users and referrer_id != user_id:
            if referrer_id not in referrals:
                referrals[referrer_id] = set()
            referrals[referrer_id].add(user_id)
            add_vip_days(referrer_id, 3)
            try:
                bot.send_message(referrer_id, "🎉 По вашей ссылке зарегистрировался новый пользователь!\n🎁 Вам зачислено **+3 дня VIP**!", parse_mode="Markdown")
            except:
                pass

    all_users.add(user_id)
    user_states.pop(user_id, None)

    welcome_text = (
        f"👋 Привет, **{message.from_user.first_name}**!\n\n"
        f"Я скачиваю видео и фото из **Instagram**, **TikTok** и **Pinterest**.\n\n"
        f"🔗 **Просто отправь мне ссылку!**"
    )
    bot.send_message(user_id, welcome_text, parse_mode="Markdown", reply_markup=main_keyboard(user_id))

# Вход в админку (/admin 571634sav)
@bot.message_handler(commands=['admin'])
def admin_login(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or args[1] != ADMIN_PASSWORD:
        bot.reply_to(message, "⛔️ Неверный пароль!")
        return

    admins.add(message.chat.id)
    bot.reply_to(message, "⚙️ **Вы успешно вошли в Админ-панель!**", parse_mode="Markdown", reply_markup=main_keyboard(message.chat.id))

# Текстовая реклама
@bot.message_handler(commands=['setad'])
def set_ad(message):
    global custom_ad_text, custom_ad_file_id, custom_ad_file_type
    if message.chat.id not in admins:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Напиши: `/setad Текст твоей рекламы`", parse_mode="Markdown")
        return
    custom_ad_text = args[1].strip()
    custom_ad_file_id = None
    custom_ad_file_type = None
    bot.reply_to(message, f"✅ **Текстовая реклама обновлена:**\n\n{custom_ad_text}", parse_mode="Markdown")

# Медиа-реклама (отправляется РЕПЛАЕМ на видео/фото)
@bot.message_handler(commands=['setad_media'])
def set_ad_media(message):
    global custom_ad_text, custom_ad_file_id, custom_ad_file_type
    if message.chat.id not in admins:
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Отправь медиафайл (видео/фото/гиф), а затем ответь на него командой `/setad_media Текст рекламы`")
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
        bot.reply_to(message, "⚠️ Пожалуйста, ответьте на фото, видео или гифку.")
        return

    custom_ad_text = text
    bot.reply_to(message, "✅ **Медиа-реклама успешно установлена!**", parse_mode="Markdown")

@bot.message_handler(commands=['delad'])
def del_ad(message):
    global custom_ad_text, custom_ad_file_id, custom_ad_file_type
    if message.chat.id not in admins:
        return
    custom_ad_text = ""
    custom_ad_file_id = None
    custom_ad_file_type = None
    bot.reply_to(message, "✅ Реклама удалена.")

# Рассылки
@bot.message_handler(commands=['broadcast_media'])
def broadcast_media(message):
    if message.chat.id not in admins:
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Ответь командой `/broadcast_media Текст` на сообщение с видео/фото.")
        return

    reply = message.reply_to_message
    args = message.text.split(maxsplit=1)
    caption = args[1].strip() if len(args) > 1 else reply.caption or ""

    count = 0
    for u in list(all_users):
        try:
            if reply.photo:
                bot.send_photo(u, reply.photo[-1].file_id, caption=caption, parse_mode="Markdown")
            elif reply.video:
                bot.send_video(u, reply.video.file_id, caption=caption, parse_mode="Markdown")
            elif reply.animation:
                bot.send_animation(u, reply.animation.file_id, caption=caption, parse_mode="Markdown")
            count += 1
        except:
            pass
    bot.reply_to(message, f"📢 Медиа-рассылка завершена! Отправлено {count} пользователям.")

@bot.message_handler(commands=['broadcast'])
def broadcast_msg(message):
    if message.chat.id not in admins:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Напиши: `/broadcast Текст рассылки`", parse_mode="Markdown")
        return
    
    msg_text = args[1].strip()
    count = 0
    for u in list(all_users):
        try:
            bot.send_message(u, msg_text, parse_mode="Markdown")
            count += 1
        except:
            pass
    bot.reply_to(message, f"📢 Рассылка завершена! Отправлено {count} пользователям.")

@bot.message_handler(commands=['addpromo'])
def add_promo(message):
    if message.chat.id not in admins:
        return
    args = message.text.split(maxsplit=3)
    if len(args) < 4 or not args[2].isdigit():
        bot.reply_to(message, "⚠️ Используй: `/addpromo КОД ДНИ Описание`", parse_mode="Markdown")
        return
    code, days, desc = args[1].strip(), int(args[2]), args[3].strip()
    promocodes[code] = f"+{days} дней VIP ({desc})"
    bot.reply_to(message, f"✅ Промокод `{code}` создан!", parse_mode="Markdown")

# Обработка меню
@bot.message_handler(func=lambda m: m.text in ["📥 Как скачивать", "👑 VIP и Промокоды", "👥 Рефералы", "🎟 Ввести промокод", "📢 Заказать рекламу", "⚙️ Админ-панель"])
def handle_menu(message):
    user_id = message.chat.id
    user_states.pop(user_id, None)

    if message.text == "📥 Как скачивать":
        bot.send_message(user_id, "📌 **Инструкция:**\n\n1. Скопируй ссылку из Instagram, TikTok или Pinterest.\n2. Отправь её в чат.\n3. Получи чистый файл!", parse_mode="Markdown")

    elif message.text == "👑 VIP и Промокоды":
        status = f"✅ **АКТИВЕН (до {vip_until[user_id].strftime('%d.%m.%Y')})**" if is_vip(user_id) else "❌ **Не активен**"
        text = (
            f"👑 **Ваш VIP-Статус:** {status}\n\n"
            "**Преимущества VIP:**\n• Без рекламы ✨\n• Максимальная скорость 🚀\n\n"
            "🎁 Приглашай друзей через раздел «👥 Рефералы» и получай +3 дня VIP за каждого!"
        )
        bot.send_message(user_id, text, parse_mode="Markdown")

    elif message.text == "👥 Рефералы":
        ref_count = len(referrals.get(user_id, []))
        ref_link = f"https://t.me/saverui_bot?start={user_id}"
        bot.send_message(user_id, f"👥 Приглашено друзей: **{ref_count}**\nНаграда: **+3 дня VIP** за каждого! 🎁\n\n🔗 **Ваша ссылка:**\n`{ref_link}`", parse_mode="Markdown")

    elif message.text == "🎟 Ввести промокод":
        user_states[user_id] = "WAITING_PROMO"
        bot.send_message(user_id, "✏️ **Отправь промокод ответным сообщением:**", parse_mode="Markdown")

    elif message.text == "📢 Заказать рекламу":
        text = (
            "📢 **Размещение рекламы в боте**\n\n"
            "Хотите привлечь новых клиентов или подписчиков?\n"
            "Ваш рекламный пост увидят все пользователи при скачивании видео!\n\n"
            f"📩 **По вопросам сотрудничества пишите админу:** {ADMIN_USERNAME}"
        )
        bot.send_message(user_id, text, parse_mode="Markdown")

    elif message.text == "⚙️ Админ-панель":
        if user_id not in admins:
            return
        text = (
            "⚙️ **АДМИН-ПАНЕЛЬ**\n\n"
            f"👥 Всего пользователей: **{len(all_users)}**\n"
            f"👑 VIP-пользователей: **{sum(1 for u in all_users if is_vip(u))}**\n\n"
            f"📢 **Текущая реклама:**\n_{custom_ad_text if custom_ad_text else 'Отсутствует'}_ "
            f"({'С медиафайлом' if custom_ad_file_id else 'Только текст'})\n\n"
            "🛠 **Управление рекламой:**\n"
            "• `/setad Текст` — Текстовая реклама\n"
            "• `/setad_media Текст` — Медиа-реклама (ответом на видео/фото)\n"
            "• `/delad` — Удалить рекламу\n"
            "• `/broadcast Текст` — Рассылка текста\n"
            "• `/broadcast_media Текст` — Рассылка медиа (ответом на видео/фото)\n"
            "• `/addpromo КОД ДНИ Описание` — Создать промокод"
        )
        bot.send_message(user_id, text, parse_mode="Markdown")

# Скачивание
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.chat.id
    text = message.text.strip() if message.text else ""

    # Ввод промокода
    if user_states.get(user_id) == "WAITING_PROMO":
        user_states.pop(user_id, None)
        if text in promocodes or text == "abdufattoh":
            days = 36500 if text == "abdufattoh" else 30
            add_vip_days(user_id, days)
            bot.reply_to(message, f"🎉 **Промокод `{text}` активирован!**\n👑 Вам зачислен VIP-доступ!", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Неверный промокод.", parse_mode="Markdown")
        return

    # Скачивание
    valid_platforms = ['instagram.com', 'tiktok.com', 'pinterest.com', 'pin.it', 'vt.tiktok.com']
    if not any(p in text.lower() for p in valid_platforms):
        bot.reply_to(message, f"⚠️ Отправь ссылку на **Instagram**, **TikTok** или **Pinterest**.")
        return

    status_msg = bot.reply_to(message, "⏳ *Загрузка...*", parse_mode="Markdown")

    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(text, download=True)
            filename = ydl.prepare_filename(info)

        vip = is_vip(user_id)
        
        # Подпись к медиа
        if vip:
            caption_text = f"✅ **Скачано через {BOT_USERNAME}**"
        else:
            ad_part = f"\n\n📢 _{custom_ad_text}_" if custom_ad_text else ""
            caption_text = f"✅ **Скачано через {BOT_USERNAME}**{ad_part}"

        with open(filename, 'rb') as file:
            bot.send_document(user_id, file, caption=caption_text, parse_mode="Markdown")

        # Если есть рекламное видео/картинка и пользователь НЕ VIP
        if not vip and custom_ad_file_id:
            try:
                if custom_ad_file_type == "photo":
                    bot.send_photo(user_id, custom_ad_file_id)
                elif custom_ad_file_type == "video":
                    bot.send_video(user_id, custom_ad_file_id)
                elif custom_ad_file_type == "animation":
                    bot.send_animation(user_id, custom_ad_file_id)
            except:
                pass

        if os.path.exists(filename):
            os.remove(filename)

        bot.delete_message(user_id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text("❌ Ошибка скачивания. Проверь доступность ссылки.", chat_id=user_id, message_id=status_msg.message_id)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling(non_stop=True)
