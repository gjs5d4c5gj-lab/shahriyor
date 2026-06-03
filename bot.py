
import telebot
from telebot import types

# Bu yerga o'zingizning BotFather'dan olgan tokeningizni qo'ying
API_TOKEN = '8918984898:AAGftTNoYbl9mrVKjms8uegZsDfePDGbFzc'
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Salom! Menga ichida testlari bor .txt faylni yuboring, men ularni Quiz (viktorina) qilib beraman.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        # Faylni yuklab olish
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Fayl ichidagi matnni o'qish (UTF-8 formatida)
        text = downloaded_file.decode('utf-8')
        
        # Testlarni ajratib olish (savollar o'rtasida *** ajratuvchi belgi bo'lsa)
        blocks = text.strip().split('***')
        
        if not blocks or len(blocks) == 0:
            bot.reply_to(message, "Xatolik: Fayl ichidan testlar topilmadi. Formatni tekshiring.")
            return

        bot.reply_to(message, f"PDF/TXT qabul qilindi. {len(blocks)} ta test o'qilmoqda, iltimos kuting... ⏳")

        for block in blocks:
            lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
            if len(lines) < 2:
                continue  # Agar savol yoki variantlar yetarli bo'lmasa, o'tkazib yuboriladi

            question = lines[0] # Birinchi qator - savol
            raw_options = lines[1:] # Qolgan qatorlar - variantlar
            
            options = []
            correct_option_id = None

            # Variantlarni bittalab tekshiramiz va to'g'ri indeksni aniqlaymiz
            for index, option in enumerate(raw_options):
                if option.startswith('#'):
                    correct_option_id = index # To'g'ri javob indeksini saqlaymiz (0, 1, 2 yoki 3)
                    options.append(option[1:].strip()) # '#' belgisini o'chirib matnni qo'shamiz
                else:
                    options.append(option)

            # Agar matnda to'g'ri javob (#) topilmagan bo'lsa, avtomatik 0-indeks (A variant) olinadi
            if correct_option_id is None:
                correct_option_id = 0

            # Telegramga rasmiy Quiz (Poll) ko'rinishida yuborish
            bot.send_poll(
                chat_id=message.chat.id,
                question=question,
                options=options,
                type='quiz',
                correct_option_id=correct_option_id, # Aynan mana shu parametr javobni to'g'rilaydi!
                is_anonymous=False
            )

    except Exception as e:
        bot.reply_to(message, f"Xatolik yuz berdi: {str(e)}")

# Botni uzluksiz ishga tushirish
print("Bot muvaffaqiyatli ishga tushdi...")
bot.infinity_polling()
