import os
import re
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import pypdf

# 1. Botni sozlash (Tokenni kompyuter/server muhitidan oladi)
TOKEN = "8918984898:AAGftTNoYbl9mrVKjms8uegZsDfePDGbFzc"
"

if not TOKEN:
    raise ValueError("❌ XATOLIK: BOT_TOKEN topilmadi! Iltimos, ekotizim o'zgaruvchisini (Environment Variable) sozlang.")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# 2. PDF fayldan matnni ajratish va testlarni 30 tadan bo'lish funksiyasi
def process_pdf_to_chunks(pdf_path, chunk_size=30):
    reader = pypdf.PdfReader(pdf_path)
    full_text = ""
    
    # PDF sahifalarini ketma-ket matnga aylantiramiz
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
            
    # Savollarni '===' belgisi bo'yicha bo'laklarga ajratamiz
    raw_questions = full_text.split("===")
    cleaned_questions = []
    
    for q in raw_questions:
        q_str = q.strip()
        if not q_str:
            continue
            
        # [AQLLI FILTR]: Savol boshidagi eski chalkash raqamlarni o'chirish
        # Masalan: "115. Bank nima?" bo'lsa, raqamni o'chirib faqat "Bank nima?" qismini qoldiradi
        q_str = re.sub(r'^\d+\.\s*', '', q_str)
        cleaned_questions.append(q_str)
        
    # Savollarni 30 tadan qilib guruhlarga (bloklarga) bo'lib chiqadi
    chunks = [cleaned_questions[i:i + chunk_size] for i in range(0, len(cleaned_questions), chunk_size)]
    return chunks


# 3. /start buyrug'ini tutib olish xendleri
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "👋 Salom! Men testlarni 30 tadan variantlarga ajratib beruvchi aqlli botman.\n\n"
        "📄 Menga testlar yozilgan **PDF faylni** yuboring, men ularni avtomat tozalab, "
        "har bir variantni 1 dan 30 gacha qayta raqamlab beraman!"
    )


# 4. Botga PDF fayl kelganda uni qayta ishlash xendleri
@dp.message(F.document)
async def handle_pdf_document(message: Message):
    # Faqat PDF fayllarni qabul qilamiz
    if not message.document.file_name.endswith('.pdf'):
        await message.answer("Iltimos, faqat PDF formatidagi fayl yuboring! 📄")
        return
        
    waiting_msg = await message.answer("Fayl qabul qilindi. PDF ichidagi testlar qayta ishlanmoqda... ⏳")
    
    # PDF faylni bot serveriga yuklab olish
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    
    # Vaqtinchalik fayl nomi
    local_pdf_name = f"temp_{message.from_user.id}.pdf"
    await bot.download_file(file.file_path, local_pdf_name)
    
    try:
        # PDF ni funksiyaga yuborib, 30 talik bloklarni olamiz
        variant_chunks = process_pdf_to_chunks(local_pdf_name, chunk_size=30)
        
        # Har bir blokni alohida chiroyli xabar qilib chiqaramiz
        for index, chunk in enumerate(variant_chunks, start=1):
            chunk_text = f"📦 **{index}-VARIANT (Blok)**\n\n"
            
            # Savollarni har bir blok ichida 1 dan boshlab qayta chiroyli raqamlaymiz
            for q_index, question in enumerate(chunk, start=1):
                chunk_text += f"{q_index}. {question}\n===\n"
                
            # Oxiridagi ortiqcha === belgisini tozalaymiz
            chunk_text = chunk_text.rstrip("\n===")
            
            # Foydalanuvchiga tayyor variant matnini yuborish
            await message.answer(chunk_text)
            
        await waiting_msg.delete()
        await message.answer("✅ Hamma testlar muvaffaqiyatli 30 tadan bloklarga ajratildi!")
        
    except Exception as e:
        await message.answer(f"❌ Faylni o'qishda xatolik yuz berdi: {e}")
        
    finally:
        # Serverda ortiqcha joy egallamasligi uchun vaqtinchalik PDFni o'chiramiz
        if os.path.exists(local_pdf_name):
            os.remove(local_pdf_name)


# 5. Botni ishga tushirish (Main funksiya)
async def main():
    print("Bot muvaffaqiyatli ishga tushdi... 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
