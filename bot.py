import os
import asyncio
import logging
import docx
import io
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Server maxfiy qutisidan (Variables) tokenni oladi
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Savollarni quiz formatiga o'tkazuvchi asosiy funksiya
async def process_quiz_text(message: types.Message, text: str):
    try:
        # Savollarni '===' belgisi orqali ajratamiz
        savollar = text.strip().split("===")
        quiz_set = []

        for s in savollar:
            lines = [line.strip() for line in s.strip().split("\n") if line.strip()]
            if len(lines) < 2:
                continue

            question_text = lines[0]
            options = []
            correct_option_id = 0

            for idx, line in enumerate(lines[1:]):
                if line.startswith("*"):
                    correct_option_id = idx
                    options.append(line.replace("*", "").strip())
                else:
                    options.append(line)

            if options:
                quiz_set.append({
                    'question': question_text,
                    'options': options,
                    'correct_option_id': correct_option_id
                })

        if not quiz_set:
            await message.answer("❌ Fayl ichida testlar topilmadi yoki formati noto'g'ri.")
            return

        # Testlarni Telegram Quiz formatida ketma-ket yuborish
        for q_num, q in enumerate(quiz_set, 1):
            await bot.send_poll(
                chat_id=message.chat.id,
                question=f"{q_num}. {q['question']}",
                options=q['options'],
                type="quiz",
                correct_option_id=q['correct_option_id'],
                is_anonymous=False
            )
            # Telegram bloklab qo'ymasligi uchun 2 soniya kutadi
            await asyncio.sleep(2)

        await message.answer("🎉 Hamma testlar yuborildi! Omad tilayman!")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.answer("❌ Testlarni qayta ishlashda xatolik yuz berdi.")

# /start buyrug'i kelganda
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\nMenga ichida to'g'ri javoblari `*` bilan belgilangan `.txt` yoki `.docx` (Word) faylini tashlang. "
        "Men sizga savollarni **Telegram Quiz (so'rovnoma)** shaklida ketma-ket chiqarib beraman."
    )

# Oddiy matn ko'rinishida test tashlanganda
@dp.message(lambda message: message.text is not None)
async def handle_text_message(message: types.Message):
    await process_quiz_text(message, message.text)

# Fayl (.txt yoki .docx) ko'rinishida test tashlanganda
@dp.message(lambda message: message.document is not None)
async def handle_document_message(message: types.Message):
    document = message.document
    file_id = document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    downloaded_file = await bot.download_file(file_path)
    
    # Agar Word (.docx) fayl bo'lsa
    if document.file_name.endswith('.docx'):
        doc = docx.Document(io.BytesIO(downloaded_file.read()))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        text = "\n".join(full_text)
        await process_quiz_text(message, text)
        
    # Agar oddiy (.txt) fayl bo'lsa
    elif document.file_name.endswith('.txt'):
        text = downloaded_file.read().decode('utf-8')
        await process_quiz_text(message, text)
        
    else:
        await message.answer("❌ Iltimos, testlarni faqat .txt yoki .docx formatida yuboring.")

# Botni yondirish (Asosiy qism)
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
