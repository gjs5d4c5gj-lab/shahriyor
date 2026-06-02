import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from docx import Document

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8918984898:AAHjfVZd9V0YhLUbHmFqc_KQZJ_ycxoI1PQ"

def parse_questions_from_docx(file_path: str) -> list[dict]:
    doc = Document(file_path)
    full_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())

    questions = []
    blocks = re.split(r'\n(?=\d+[\.\)]\s)', full_text)

    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 5:
            continue

        q_match = re.match(r'^\d+[\.\)]\s*(.*)', lines[0])
        if not q_match:
            continue
        question_text = q_match.group(1)

        options = {}
        correct = None

        for line in lines[1:]:
            opt = re.match(r'^([A-Da-d])[\.\)]\s*(.*)', line)
            if opt:
                options[opt.group(1).upper()] = opt.group(2)
                continue

            ans = re.match(r'^(?:Javob|To\'g\'ri\s*javob)\s*[:=]\s*([A-Da-d])', line, re.IGNORECASE)
            if ans:
                correct = ans.group(1).upper()

        if question_text and len(options) == 4 and correct:
            questions.append({
                "question": question_text,
                "options": options,
                "correct": correct
            })

    return questions


def split_questions(questions: list, parts: int = 5) -> list[list]:
    n = len(questions)
    size = n // parts
    remainder = n % parts
    result = []
    start = 0
    for i in range(parts):
        end = start + size + (1 if i < remainder else 0)
        result.append(questions[start:end])
        start = end
    return result


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men test botiman.\n\n"
        "📄 Menga Word (.docx) fayl yuboring.\n"
        "Fayl ichida A/B/C/D variantli savollar bo'lishi kerak.\n\n"
        "Bot ularni 5 qismga bo'lib yuboradi."
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    if not doc.file_name.endswith(".docx"):
        await update.message.reply_text("❌ Faqat .docx fayl yuboring!")
        return

    await update.message.reply_text("⏳ Fayl o'qilmoqda...")

    file = await doc.get_file()
    file_path = f"/tmp/{doc.file_name}"
    await file.download_to_drive(file_path)

    try:
        questions = parse_questions_from_docx(file_path)
    except Exception as e:
        logger.error(f"Parse error: {e}")
        await update.message.reply_text("❌ Faylni o'qishda xato. Format to'g'riligini tekshiring.")
        return

    if not questions:
        await update.message.reply_text(
            "⚠️ Savollar topilmadi.\n\n"
            "Format shunday bo'lishi kerak:\n"
            "1. Savol matni\n"
            "A) variant\nB) variant\nC) variant\nD) variant\n"
            "Javob: A"
        )
        return

    parts = split_questions(questions, 5)
    context.user_data["parts"] = parts
    context.user_data["total"] = len(questions)

    keyboard = []
    for i, part in enumerate(parts):
        keyboard.append([
            InlineKeyboardButton(
                f"📝 {i+1}-qism ({len(part)} ta savol)",
                callback_data=f"part_{i}"
            )
        ])
    keyboard.append([InlineKeyboardButton("📦 Barcha qismlarni yuborish", callback_data="all_parts")])

    await update.message.reply_text(
        f"✅ Jami {len(questions)} ta savol topildi!\n"
        f"5 qismga bo'lindi. Qaysi qismni yuboray?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def format_part(questions: list[dict], part_num: int, total_start: int) -> str:
    lines = [f"📝 *{part_num}-qism* ({len(questions)} ta savol)\n{'─'*30}\n"]
    for i, q in enumerate(questions, 1):
        num = total_start + i
        lines.append(f"*{num}. {q['question']}*")
        for letter, text in q["options"].items():
            mark = "✅" if letter == q["correct"] else "  "
            lines.append(f"{mark} {letter}) {text}")
        lines.append("")
    return "\n".join(lines)


async def send_part(update: Update, context: ContextTypes.DEFAULT_TYPE, part_index: int):
    parts = context.user_data.get("parts", [])
    if part_index >= len(parts):
        await update.callback_query.message.reply_text("❌ Bu qism mavjud emas.")
        return

    questions = parts[part_index]
    total_start = sum(len(parts[i]) for i in range(part_index))
    text = format_part(questions, part_index + 1, total_start)

    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        await update.callback_query.message.reply_text(chunk, parse_mode="Markdown")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("part_"):
        part_index = int(data.split("_")[1])
        await send_part(update, context, part_index)

    elif data == "all_parts":
        parts = context.user_data.get("parts", [])
        await query.message.reply_text("📤 Barcha qismlar yuborilmoqda...")
        for i in range(len(parts)):
            await send_part(update, context, i)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
