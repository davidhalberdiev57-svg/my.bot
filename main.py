import os
import telebot
from yt_dlp import YoutubeDL

TOKEN = "8863043974:AAGzQ2NmtxHa1MjS2AmTCYX1epmmrq4Bpv0"
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Привет! Отправь мне ссылку на видео или фото из Instagram или Pinterest, и я его скачаю!",
    )


@bot.message_handler(func=lambda message: True)
def download_media(message):
    url = message.text.strip()

    if not (
        url.startswith("http://")
        or url.startswith("https://")
        or "instagram.com" in url
        or "pinterest" in url
    ):
        bot.reply_to(message, "Пожалуйста, отправь корректную ссылку.")
        return

    status_msg = bot.reply_to(message, "⏳ Скачиваю медиа, подожди немного...")

    ydl_opts = {
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        with open(filename, "rb") as file:
            bot.send_document(message.chat.id, file)

        if os.path.exists(filename):
            os.remove(filename)

        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Не удалось скачать. Ошибка: {str(e)[:100]}",
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
        )


if __name__ == "__main__":
    bot.polling(non_stop=True)
