"""
✦ TESTIFY BY AARAV — TELEGRAM POLL QUIZ BOT ✦
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Native Telegram Quiz Polls + Complex MCQ Parser + Live Leaderboard
"""

import os, re, asyncio, signal, sys
from typing import Dict, List, Optional

from telegram import Update, Poll
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters, PollAnswerHandler, PollHandler
)
from telegram.constants import ParseMode

# ═══════════════════════════════════════════════════════════════
# CONFIG & STATE
# ═══════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL = "@sjvbots"

group_questions: Dict[int, List[dict]] = {}     # chat_id -> questions
group_config: Dict[int, dict] = {}              # chat_id -> {marks, neg}
setup_mode: Dict[int, bool] = {}                # chat_id -> bool
active_quizzes: Dict[int, dict] = {}            # chat_id -> quiz state
poll_map: Dict[str, int] = {}                   # poll_id -> chat_id
last_results: Dict[int, dict] = {}              # chat_id -> final scores

LETTERS = "ABCDEFGHIJ"

# ═══════════════════════════════════════════════════════════════
# COMPLEX MCQ PARSER (Statements + 👉 + Options + ✅ + Ex:)
# ═══════════════════════════════════════════════════════════════
def parse_questions(text: str) -> List[dict]:
    questions = []
    blocks = re.split(r'(?=Q\s*\d+[\.\)])', text, flags=re.IGNORECASE)

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if not re.match(r'Q\s*\d+[\.\)]', block, re.IGNORECASE):
            continue

        lines = block.split('\n')
        statements, question_text, options, answer, explanation = [], "", {}, None, ""
        in_options, in_expl = False, False

        for idx, line in enumerate(lines):
            ls = line.strip()
            if not ls:
                continue

            # Q number line
            if idx == 0:
                rest = re.sub(r'^Q\s*\d+[\.\)]\s*', '', ls)
                if rest:
                    statements.append(rest)
                continue

            # 👉 main question
            if ls.startswith("👉"):
                question_text = ls.replace("👉", "").strip()
                in_options = False
                continue

            # options (a)-(j)
            m = re.match(r'^\(?([a-jA-J])[\.\)]\s*(.+)', ls)
            if m:
                key = m.group(1).upper()
                val = m.group(2).strip()
                if "✅" in val:
                    answer = key
                    val = val.replace("✅", "").strip()
                options[key] = val
                in_options, in_expl = True, False
                continue

            # explanation
            if ls.lower().startswith(("ex:", "explanation:")):
                explanation = ls.split(":", 1)[1].strip()
                in_expl, in_options = True, False
                continue

            if in_expl:
                explanation += " " + ls
            elif not in_options:
                statements.append(ls)

        if options and len(options) >= 2:
            full_q = "\n".join(statements)
            if question_text:
                full_q += (("\n\n" if full_q else "") + "👉 " + question_text)
            questions.append({
                "question": full_q.strip(),
                "options": options,
                "answer": answer,
                "explanation": explanation.strip()
            })
    return questions


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
async def is_admin(update: Update) -> bool:
    """Check karta hai user group admin hai ya nahi."""
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in ("creator", "administrator")
    except Exception:
        return False


def get_cfg(chat_id: int) -> dict:
    if chat_id not in group_config:
        group_config[chat_id] = {"marks": 4, "neg": 0}
    return group_config[chat_id]


def leaderboard_text(scores: dict, title: str = "📊 *Leaderboard*") -> str:
    if not scores:
        return title + "\n\nKoi score nahi hai abhi tak."
    txt = title + "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    for rank, (uid, d) in enumerate(ranked[:10], 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "🏅")
        txt += f"{medal} *{rank}. {d['name']}* — {d['score']} pts\n"
    return txt


# ═══════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ("group", "supergroup"):
        txt = (
            "✦ *TESTIFY BY AARAV — POLL QUIZ BOT* ✦\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 Native Telegram Quiz Polls se live quiz!\n\n"
            "*Admin Commands:*\n"
            "/setup — Questions paste/upload karein\n"
            "/startquiz 30 — Quiz shuru (30 sec/question)\n"
            "/stopquiz — Quiz rokein\n"
            "/setmarks 4 — Marks per question\n"
            "/setneg 1 — Negative marking\n"
            "/leaderboard — Scores dekhein\n"
            "/quizhelp — Full guide\n\n"
            f"📢 {CHANNEL}"
        )
    else:
        txt = (
            "✦ *TESTIFY BY AARAV* ✦\n\n"
            "Mujhe apne *Group* mein add karein aur admin banayein.\n"
            "Phir /setup se questions load karke /startquiz dabayein! 🚀\n\n"
            f"📢 {CHANNEL}"
        )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)


async def quiz_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = (
        "📖 *Poll Quiz Guide*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*1️⃣ Questions Format:*\n"
        "`Q1. Statement 1`\n"
        "`Statement 2 (assertion/reason/matching)`\n"
        "`👉 Question?`\n"
        "`(a) Option 1`\n"
        "`(b) Option 2 ✅`\n"
        "`(c) Option 3`\n"
        "`(d) Option 4`\n"
        "`Ex: Explanation here`\n\n"
        "*2️⃣ Quiz Flow:*\n"
        "• Har question ek *Telegram Quiz Poll* banegi\n"
        "• Lambi questions pehle message mein, poll upar refer karegi\n"
        "• Timer khatam → poll auto-close → result + explanation\n"
        "• Sahi answer = +marks, galat = −negative\n\n"
        "*3️⃣ Notes:*\n"
        "• BotFather mein Privacy Mode *DISABLE* karein\n"
        "• Sirf admins quiz control kar sakte hain\n"
        "• Max 10 options, complex statements supported"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)


async def setup_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Sirf groups mein use karein.")
        return
    if not await is_admin(update):
        await update.message.reply_text("❌ Sirf admins questions setup kar sakte hain.")
        return
    setup_mode[update.effective_chat.id] = True
    await update.message.reply_text(
        "📝 *Setup Mode ON*\n\n"
        "Ab formatted questions *paste* karein ya *.txt file* upload karein.\n"
        "(Complex MCQs: statements + 👉 + options + ✅ + Ex:)\n\n"
        "❌ Cancel: /cancelsetup",
        parse_mode=ParseMode.MARKDOWN
    )


async def cancel_setup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    setup_mode.pop(update.effective_chat.id, None)
    await update.message.reply_text("✅ Setup mode band.")


async def handle_group_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not setup_mode.get(chat_id):
        return
    qs = parse_questions(update.message.text)
    if not qs:
        await update.message.reply_text("❌ Koi valid question nahi mila. /quizhelp dekhein.")
        return
    group_questions[chat_id] = qs
    setup_mode[chat_id] = False
    await update.message.reply_text(
        f"✅ *{len(qs)} complex questions load ho gaye!*\n\n"
        f"Ab `/startquiz 30` se quiz shuru karein (30 = seconds per question).",
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_group_doc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not setup_mode.get(chat_id):
        return
    doc = update.message.document
    if not doc.file_name.lower().endswith(".txt"):
        await update.message.reply_text("❌ Sirf .txt files.")
        return
    await update.message.reply_text("⏳ File padhi ja rahi hai...")
    try:
        file = await ctx.bot.get_file(doc.file_id)
        path = f"tmp_{chat_id}.txt"
        await file.download_to_drive(path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        os.remove(path)
        qs = parse_questions(content)
        if not qs:
            await update.message.reply_text("❌ File mein valid questions nahi mile.")
            return
        group_questions[chat_id] = qs
        setup_mode[chat_id] = False
        await update.message.reply_text(f"✅ *{len(qs)} questions file se load!*\n\n`/startquiz 30` se shuru karein.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def set_marks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        await update.message.reply_text("❌ Admin only.")
        return
    try:
        get_cfg(update.effective_chat.id)["marks"] = float(update.message.text.split()[1])
        await update.message.reply_text(f"✅ Marks/Q = {get_cfg(update.effective_chat.id)['marks']}")
    except Exception:
        await update.message.reply_text("Usage: /setmarks 4")


async def set_neg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        await update.message.reply_text("❌ Admin only.")
        return
    try:
        get_cfg(update.effective_chat.id)["neg"] = float(update.message.text.split()[1])
        await update.message.reply_text(f"✅ Negative = -{get_cfg(update.effective_chat.id)['neg']}")
    except Exception:
        await update.message.reply_text("Usage: /setneg 1")


async def start_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Sirf groups mein.")
        return
    if not await is_admin(update):
        await update.message.reply_text("❌ Sirf admins quiz start kar sakte hain.")
        return
    qs = group_questions.get(chat_id)
    if not qs:
        await update.message.reply_text("❌ Pehle /setup se questions load karein!")
        return
    if chat_id in active_quizzes and active_quizzes[chat_id]["active"]:
        await update.message.reply_text("⚠️ Quiz pehle se chal raha hai! /stopquiz karein.")
        return

    # time per question
    try:
        t = int(update.message.text.split()[1])
        t = max(5, min(600, t))
    except Exception:
        t = 30

    cfg = get_cfg(chat_id)
    active_quizzes[chat_id] = {
        "questions": qs,
        "index": 0,
        "scores": {},
        "answers": {},
        "active": True,
        "time": t,
        "marks": cfg["marks"],
        "neg": cfg["neg"],
        "poll_id": None,
        "poll_msg_id": None,
        "correct_idx": None,
        "letters": [],
        "event": asyncio.Event()
    }

    await update.message.reply_text(
        f"🚀 *QUIZ SHURU!*\n\n"
        f"📋 Questions: {len(qs)}\n"
        f"⏱ {t} sec per question (poll auto-close)\n"
        f"🎯 +{cfg['marks']} sahi | −{cfg['neg']} galat\n\n"
        f"Polls mein answer karein. Good luck! 🍀",
        parse_mode=ParseMode.MARKDOWN
    )
    asyncio.create_task(quiz_loop(chat_id, ctx))


async def quiz_loop(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    quiz = active_quizzes[chat_id]
    qs = quiz["questions"]

    for i, q in enumerate(qs):
        if not quiz["active"]:
            break
        quiz["index"] = i
        quiz["answers"] = {}

        letters = [l for l in LETTERS if l in q["options"]]
        if q["answer"] not in letters or len(letters) < 2:
            continue  # invalid question skip
        quiz["letters"] = letters
        quiz["correct_idx"] = letters.index(q["answer"])

        full_q = f"❓ QUESTION {i+1}/{len(qs)}\n\n{q['question']}"
        poll_question = full_q if len(full_q) <= 300 else f"❓ Q{i+1}: Sahi option chunein (question upar dekhein)"

        # Lambi complex question → pehle message mein full text
        if len(full_q) > 300:
            try:
                await ctx.bot.send_message(chat_id, full_q)
            except Exception:
                pass

        opt_texts = [q["options"][l][:100] for l in letters]
        expl = q["explanation"][:200] or None

        try:
            msg = await ctx.bot.send_poll(
                chat_id=chat_id,
                question=poll_question,
                options=opt_texts,
                type=Poll.QUIZ,
                correct_option_id=quiz["correct_idx"],
                explanation=expl,
                is_anonymous=False,
                open_period=quiz["time"]
            )
        except Exception as e:
            await ctx.bot.send_message(chat_id, f"❌ Poll error: {e}")
            continue

        quiz["poll_id"] = msg.poll.id
        quiz["poll_msg_id"] = msg.message_id
        poll_map[msg.poll.id] = chat_id

        # Poll close hone ka wait karo
        quiz["event"].clear()
        try:
            await asyncio.wait_for(quiz["event"].wait(), timeout=quiz["time"] + 15)
        except asyncio.TimeoutError:
            pass

        poll_map.pop(quiz["poll_id"], None)
        await asyncio.sleep(3)

    # ══ QUIZ FINISH ══
    quiz["active"] = False
    last_results[chat_id] = quiz["scores"]
    await ctx.bot.send_message(
        chat_id,
        leaderboard_text(quiz["scores"], "🏆 *FINAL LEADERBOARD* 🏆") + f"\n\n✦ TESTIFY BY AARAV · {CHANNEL}",
        parse_mode=ParseMode.MARKDOWN
    )
    active_quizzes.pop(chat_id, None)


async def stop_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    quiz = active_quizzes.get(chat_id)
    if not quiz or not quiz["active"]:
        await update.message.reply_text("❌ Koi active quiz nahi.")
        return
    if not await is_admin(update):
        await update.message.reply_text("❌ Admin only.")
        return
    quiz["active"] = False
    if quiz["poll_id"] and quiz["poll_msg_id"]:
        try:
            await ctx.bot.stop_poll(chat_id, quiz["poll_msg_id"])
        except Exception:
            pass
    quiz["event"].set()
    await update.message.reply_text("⏹ *Quiz rok diya gaya!*", parse_mode=ParseMode.MARKDOWN)


async def leaderboard_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    quiz = active_quizzes.get(chat_id)
    if quiz and quiz["active"]:
        await update.message.reply_text(leaderboard_text(quiz["scores"], "📊 *LIVE Leaderboard*"), parse_mode=ParseMode.MARKDOWN)
    elif chat_id in last_results:
        await update.message.reply_text(leaderboard_text(last_results[chat_id], "🏆 *Last Quiz Result*"), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Koi scores nahi hain.")


# ═══════════════════════════════════════════════════════════════
# POLL EVENTS (Scoring Engine)
# ═══════════════════════════════════════════════════════════════
async def on_poll_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User ka answer record karta hai (latest revote tracked)."""
    pa = update.poll_answer
    chat_id = poll_map.get(pa.poll_id)
    if not chat_id:
        return
    quiz = active_quizzes.get(chat_id)
    if not quiz or not quiz["active"] or pa.poll_id != quiz["poll_id"]:
        return
    user = pa.user
    if not user:
        return
    opt = pa.option_ids[0] if pa.option_ids else None
    quiz["answers"][user.id] = {"name": user.first_name, "opt": opt}


async def on_poll_state(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Poll close hone par scoring + summary bhejta hai."""
    poll = update.poll
    chat_id = poll_map.get(poll.id)
    if not chat_id:
        return
    quiz = active_quizzes.get(chat_id)
    if not quiz or poll.id != quiz["poll_id"]:
        return
    if not poll.is_closed:
        return

    if quiz["active"]:
        correct = quiz["correct_idx"]
        letters = quiz["letters"]
        right_names, wrong_names = [], []
        for uid, d in quiz["answers"].items():
            sc = quiz["scores"].setdefault(uid, {"name": d["name"], "score": 0})
            if d["opt"] == correct:
                sc["score"] += quiz["marks"]
                right_names.append(d["name"])
            elif d["opt"] is not None:
                sc["score"] -= quiz["neg"]
                wrong_names.append(d["name"])

        correct_letter = letters[correct]
        q = quiz["questions"][quiz["index"]]
        summary = (
            f"⏰ *Time Up — Q{quiz['index']+1} Result*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Sahi answer: *({correct_letter})* {q['options'][correct_letter]}\n\n"
            f"🎯 Sahi kiya: {', '.join(right_names) if right_names else 'Koi nahi 😔'}\n"
            f"❌ Galat kiya: {', '.join(wrong_names) if wrong_names else 'Koi nahi'}\n\n"
        )
        summary += leaderboard_text(quiz["scores"], "📊 *Top Scorers*")
        try:
            await ctx.bot.send_message(chat_id, summary, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    quiz["event"].set()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quizhelp", quiz_help))
    app.add_handler(CommandHandler("setup", setup_cmd))
    app.add_handler(CommandHandler("cancelsetup", cancel_setup))
    app.add_handler(CommandHandler("startquiz", start_quiz))
    app.add_handler(CommandHandler("stopquiz", stop_quiz))
    app.add_handler(CommandHandler("setmarks", set_marks))
    app.add_handler(CommandHandler("setneg", set_neg))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))

    app.add_handler(PollAnswerHandler(on_poll_answer))
    app.add_handler(PollHandler(on_poll_state))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_group_doc))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_text))

    print("🚀 Testify Poll Quiz Bot running...")
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES, timeout=60)


if __name__ == "__main__":
    main()
