import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

# Bot tokeningizni yozing
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def parse_quiz_file(file_path):
    """Faylni o'qib, savol, variantlar va to'g'ri javob indeksini ajratuvchi funksiya"""
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Savollarni '===' orqali ajratamiz
    raw_questions = [q.strip() for q in text.split('===') if q.strip()]
    parsed_questions = []
    
    for raw_q in raw_questions:
        lines = [line.strip() for line in raw_q.split('\n') if line.strip()]
        if len(lines) < 2:
            continue
        
        question_text = lines[0] # Birinchi qator - savol matni
        options = lines[1:]      # Qolgan qatorlar - variantlar
        
        correct_index = 0
        cleaned_options = []
        
        for index, option in enumerate(options):
            # Agar variant `*` bilan boshlansa, bu to'g'ri javob
            if option.startswith('*'):
                correct_index = index
                # Yulduzchani olib tashlaymiz (foydalanuvchi ko'rmasligi uchun)
                cleaned_options.append(option.replace('*', '', 1))
            else:
                cleaned_options.append(option)
                
        # Telegram bitta testda ko'pi bilan 10 ta variant qabul qiladi, odatda 4 ta bo'ladi
        if cleaned_options:
            parsed_questions.append({
                "question": question_text,
                "options": cleaned_options,
                "correct_id": correct_index
            })
            
    return parsed_questions

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "Menga ichida to'g'ri javoblari `*` bilan belgilangan `.txt` faylini tashlang. "
        "Men sizga savollarni **Telegram Quiz (so'rovnoma)** shaklida ketma-ket chiqarib beraman.\n\n"
        "📝 **Fayl formati xuddi shunday bo'lsin:**\n"
        "O'zbekiston poytaxti qaysi shahar?\n"
        "*A) Toshkent\n"
        "B) Samarqand\n"
        "C) Buxoro\n"
        "D) Xiva\n"
        "===\n"
        "2+2 nechaga teng?\n"
        "A) 3\n"
        "*B) 4\n"
        "C) 5\n"
        "D) 6"
    )

@dp.message(F.document)
async def handle_document(message: types.Message):
    if not message.document.file_name.endswith('.txt'):
        await message.answer("❌ Iltimos, faqat `.txt` formatidagi fayl yuboring.")
        return

    status_message = await message.answer("⏳ Fayl o'qilmoqda...")
    
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    
    input_filename = f"quiz_{message.from_user.id}.txt"
    await bot.download_file(file.file_path, input_filename)
    
    try:
        # Faylni parslash
        questions = parse_quiz_file(input_filename)
        
        if not questions:
            await status_message.edit_text("❌ Fayl formatida xatolik yoki savollar topilmadi.")
            os.remove(input_filename)
            return
            
        total_questions = len(questions)
        # Savollar sonini 30 taga cheklaymiz (agar ko'p bo'lsa ham dastlabki 30 tasini oladi)
        # Agar hammasini chiqarmoqchi bo'lsangiz `[:30]` qismini olib tashlang
        quiz_set = questions[:30] 
        
        await status_message.edit_text(f"✅ Jami {total_questions} ta savoldan dastlabki 30 tasi uchun Quiz boshlanmoqda...\n"
                                       f"Spam bo'lmasligi uchun savollar 2 soniya oraliq bilan tashlanadi.")
        
        # Ketma-ket testlarni yuborish
        for q_num, q in enumerate(quiz_set, start=1):
            await bot.send_poll(
                chat_id=message.chat.id,
                question=f"{q_num}. {q['question']}",
                options=q['options'],
                type="quiz",                  # Telegram'ning to'g'ri/noto'g'ri ko'rsatadigan rejimi
                correct_option_id=q['correct_id'],
                is_anonymous=False            # Kim qanday javob berganini ko'rish uchun (ixtiyoriy)
            )
            # Telegram bloklab qo'ymasligi uchun ozgina pauza (anti-flood)
            await asyncio.sleep(2)
            
        await message.answer("🎉 30 talik test yakunlandi!")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.answer("❌ Testlarni shakllantirishda xatolik yuz berdi.")
    
    finally:
        if os.path.exists(input_filename):
            os.remove(input_filename)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
