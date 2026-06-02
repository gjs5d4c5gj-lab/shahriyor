import asyncio
import logging
import os
import re
import fitz  # PyMuPDF kutubxonasi (PDF o'qish uchun)
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8918984898:AAGftTNoYbl9mrVKjms8uegZsDfePDGbFzc")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Foydalanuvchilarning yuklangan testlarini va holatlarini xotirada saqlash
# (Katta loyihalar uchun ma'lumotlar bazasi tavsiya etiladi, hozircha operativ xotirada)
USER_TESTS = {}

def parse_pdf_tests(file_path):
    """PDF fayldan testlarni ajratib olish funksiyasi"""
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    
    # Savollarni ajratish (Savol:, A), B), C), D) formatlari bo'yicha)
    # Bu yerda har bir savol "Savol:" yoki variant boshlanishi bilan ajratiladi
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    
    tests = []
    current_question = None
    current_options = []
    correct_option_idx = None
    
    # Variantlarni aniqlash uchun muntazam ifoda (A), B), C), D))
    option_pattern = re.compile(r'^([A-D])\)\s*(.*)')
    
    for line in lines:
        match = option_pattern.match(line)
        if match:
            option_letter = match.group(1)
            option_text = match.group(2).strip()
            
            # Agar variantda # belgisi bo'lsa, uni to'g'ri javob deb belgilaymiz va # ni o'chiramiz
            if option_text.startswith('#'):
                option_text = option_text.replace('#', '').strip()
                correct_option_idx = len(current_options)
                
            current_options.append(option_text)
        else:
            # Agar yangi savol boshlansa va eski savol to'liq bo'lsa, uni saqlaymiz
            if current_question and len(current_options) >= 2:
                tests.append({
                    "question": current_question,
                    "options": current_options[:4], # Maksimal 4 ta variant
                    "correct_idx": correct_option_idx if correct_option_idx is not None else 0
                })
            
            # Yangi savolni boshlaymiz
            current_question = line
            current_options = []
            correct_option_idx = None
            
    # Oxirgi savolni ham qo'shib qo'yamiz
    if current_question and len(current_options) >= 2:
        tests.append({
            "question": current_question,
            "options": current_options[:4],
            "correct_idx": correct_option_idx if correct_option_idx is not None else 0
        })
        
    return tests

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalomu alaykum! Menga ichida testlari bor **PDF fayl** yuboring.\n"
        "Format quyidagicha bo'lishi kerak:\n\n"
        "Savol matni?\n"
        "A) Variant\n"
        "B) Variant\n"
        "C) #To'g'ri javob\n"
        "D) Variant"
    )

@dp.message(lambda message: message.document and message.document.file_name.endswith('.pdf'))
async def handle_pdf(message: types.Message):
    await message.answer("PDF qabul qilindi. Testlar o'qilmoqda, iltimos kuting... ⏳")
    
    # Faylni yuklab olish
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    local_filename = f"downloads/{file_id}.pdf"
    os.makedirs("downloads", exist_ok=True)
    await bot.download_file(file_path, local_filename)
    
    try:
        # Testlarni parse qilish
        parsed_tests = parse_pdf_tests(local_filename)
        
        if not parsed_tests:
            await message.answer("Xatolik: PDF ichidan testlar topilmadi. Format to'g'ri ekanligini tekshiring.")
            return
            
        # Savollarni 30 tadan bloklarga bo'lish (Chunking)
        chunk_size = 30
        chunks = [parsed_tests[i:i + chunk_size] for i in range(0, len(parsed_tests), chunk_size)]
        
        USER_TESTS[message.from_user.id] = chunks
        
        # Bloklar uchun tugmalar yaratish
        builder = InlineKeyboardBuilder()
        for idx, chunk in enumerate(chunks):
            # Agar oxirgi blok bo'lsa va 30 tadan kam bo'lsa, qoldiq savollar sonini ko'rsatadi
            savollar_soni = len(chunk)
            builder.button(
                text=f"Blok №{idx+1} ({savollar_soni} ta savol)", 
                callback_data=f"start_block_{idx}"
            )
        builder.adjust(1)
        
        await message.answer(
            f"Muvaffaqiyatli yuklandi! Jami {len(parsed_tests)} ta savol topildi.\n"
            f"Savollar {len(chunks)} ta blokka ajratildi. Quyidan blokni tanlang va testni boshlang:",
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await message.answer("Faylni qayta ishlashda xatolik yuz berdi. Ssenariy tuzilishini tekshiring.")
    finally:
        if os.path.exists(local_filename):
            os.remove(local_filename)

@dp.callback_query(lambda c: c.data.startswith('start_block_'))
async def start_quiz_block(callback_query: types.CallbackQuery):
    block_idx = int(callback_query.data.split('_')[2])
    user_id = callback_query.from_user.id
    
    if user_id not in USER_TESTS or block_idx >= len(USER_TESTS[user_id]):
        await callback_query.answer("Eski test ma'lumotlari. Iltimos PDF-ni qayta yuklang.", show_alert=True)
        return
        
    block_tests = USER_TESTS[user_id][block_idx]
    await callback_query.message.answer(f"🚀 №{block_idx+1}-blok boshlandi! Ketma-ket testlar yuborilmoqda...")
    
    # Telegram so'rovnomalarini (Quiz) ketma-ket yuborish
    for test in block_tests:
        try:
            await bot.send_poll(
                chat_id=user_id,
                question=test["question"][:300], # Telegram cheklovi sababli max 300 belgi
                options=[opt[:100] for opt in test["options"]], # Variantlar max 100 belgi
                type="quiz",
                correct_option_id=test["correct_idx"],
                is_anonymous=False
            )
            await asyncio.sleep(0.5) # Telegram spam himoyasi uchun qisqa pauza
        except Exception as e:
            logging.error(f"Poll yuborishda xato: {e}")
            continue
            
    await callback_query.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
