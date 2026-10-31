"""
✦ TESTIFY BY AARAV — ULTIMATE PREMIUM BOT ✦
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Private: Premium HTML Test Builder (Bilingual, Resume, Lifelines, Analytics)
Group:   Native Telegram Poll Quiz (Complex MCQs, Live Leaderboard)
Render-Safe: Python 3.14 event-loop fix + drop_pending_updates
"""

import os, re, json, random, asyncio, signal, sys
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, PollAnswerHandler, PollHandler
)
from telegram.constants import ParseMode

# ═══════════════════════════════════════════════════════════════
# CONFIG & STATE
# ═══════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL = "@sjvbots"
LETTERS = "ABCDEFGHIJ"

DEFAULT_SETTINGS = {
    "test_name": "Premium Mock Test",
    "instructions": "1. Har question ke 4 options hain.\n2. Sahi answer = +4 marks.\n3. Galat answer = -1 mark.\n4. Timer khatam hone par test auto-submit hogi.",
    "question_limit": 0,
    "duration": 20,
    "marks_per_question": 4,
    "negative_marking": 1,
    "shuffle_questions": False,
    "shuffle_options": False,
    "resume_enabled": True,
    "language_mode": "bilingual",
    "lifelines": {"fifty_fifty": 1, "smart_hint": 1, "skip_question": 3, "extra_time": 1}
}

user_data: Dict[int, Dict] = {}
group_questions: Dict[int, List[dict]] = {}
group_config: Dict[int, dict] = {}
setup_mode: Dict[int, bool] = {}
active_quizzes: Dict[int, dict] = {}
poll_map: Dict[str, int] = {}
last_results: Dict[int, dict] = {}


def get_user(uid: int) -> Dict:
    if uid not in user_data:
        user_data[uid] = {"step": "menu", "questions": [], "settings": json.loads(json.dumps(DEFAULT_SETTINGS)), "ai_config": {}}
    return user_data[uid]


# ═══════════════════════════════════════════════════════════════
# COMPLEX + BILINGUAL PARSER
# ═══════════════════════════════════════════════════════════════
def parse_questions(text: str) -> List[dict]:
    questions = []
    blocks = re.split(r'(?=Q\s*\d+[\.\)])', text, flags=re.IGNORECASE)

    for block in blocks:
        block = block.strip()
        if not block or not re.match(r'Q\s*\d+[\.\)]', block, re.IGNORECASE):
            continue

        lines = block.split('\n')
        st_en, st_hi, q_en, q_hi = "", "", "", ""
        opts_en, opts_hi, exp_en, exp_hi = {}, {}, "", ""
        answer, lang, cur_key, in_expl = None, "en", None, False

        for idx, line in enumerate(lines):
            ls = line.strip()
            if not ls:
                continue

            if ls.startswith("[HI]"): lang = "hi"; ls = ls.replace("[HI]", "").strip()
            elif ls.startswith("[EN]"): lang = "en"; ls = ls.replace("[EN]", "").strip()

            if idx == 0:
                rest = re.sub(r'^Q\s*\d+[\.\)]\s*', '', ls)
                if rest:
                    if lang == "hi": st_hi += rest + " "
                    else: st_en += rest + " "
                continue

            if ls.startswith("👉"):
                t = ls.replace("👉", "").strip()
                if lang == "hi": q_hi += t + " "
                else: q_en += t + " "
                cur_key = None
                continue

            m = re.match(r'^\(?([a-jA-J])[\.\)]\s*(.+)', ls)
            if m:
                key = m.group(1).upper()
                val = m.group(2).strip()
                if "✅" in val:
                    answer = key
                    val = val.replace("✅", "").strip()
                if lang == "hi": opts_hi[key] = val
                else: opts_en[key] = val
                cur_key = key
                in_expl = False
                continue

            if ls.lower().startswith(("ex:", "explanation:")):
                t = ls.split(":", 1)[1].strip()
                if lang == "hi": exp_hi += t + " "
                else: exp_en += t + " "
                in_expl = True
                cur_key = None
                continue

            if in_expl:
                if lang == "hi": exp_hi += ls + " "
                else: exp_en += ls + " "
            elif cur_key:
                if lang == "hi": opts_hi[cur_key] += " " + ls
                else: opts_en[cur_key] += " " + ls
            else:
                if lang == "hi": st_hi += ls + " "
                else: st_en += ls + " "

        if not opts_en:
            opts_en = opts_hi
        if opts_en and len(opts_en) >= 2:
            full_en = (st_en.strip() + ("\n\n👉 " + q_en.strip() if q_en else "")).strip()
            full_hi = (st_hi.strip() + ("\n\n👉 " + q_hi.strip() if q_hi else "")).strip()
            questions.append({
                "question_en": full_en, "question_hi": full_hi,
                "options_en": opts_en, "options_hi": opts_hi if opts_hi else opts_en,
                "answer": answer,
                "explanation_en": exp_en.strip(), "explanation_hi": exp_hi.strip()
            })
    return questions


# ═══════════════════════════════════════════════════════════════
# AI PROMPT STUDIO
# ═══════════════════════════════════════════════════════════════
def build_ai_prompt(c: Dict) -> str:
    lang_map = {"hindi": "Hindi", "english": "English", "bilingual": "Hindi + English (Bilingual)", "rajasthani": "Rajasthani"}
    lvl_map = {"easy": "Easy", "moderate": "Moderate", "hard": "Hard", "very_hard": "Very Hard",
               "extreme": "Extreme", "ultra": "Ultra Extreme / Expert", "mixed": "Mixed Difficulty"}
    return f"""Generate {c.get('num',10)} high-quality complex MCQ questions.

📚 SUBJECT: {c.get('subject','General Knowledge')}
🎯 TOPIC: {c.get('topic','General')}
🌐 LANGUAGE: {lang_map.get(c.get('language','hindi'),'Hindi')}
📊 DIFFICULTY: {lvl_map.get(c.get('level','moderate'),'Moderate')}

FORMAT (strictly follow):
Q1. <Statement 1 / Assertion>
<Statement 2 / Reason>
👉 <Question>
(a) <Option 1>
(b) <Option 2> ✅
(c) <Option 3>
(d) <Option 4>
Ex: <Explanation — why correct + why others wrong>

KEY RULES:
- Double line break between statements
- Mix: Assertion-Reason, Multiple Statements, Match the Column
- 👉 before question, ✅ on correct option
- Vary correct option position (not always a)
{f"- Extra: {c['extra']}" if c.get('extra') else ''}"""


# ═══════════════════════════════════════════════════════════════
# PREMIUM HTML GENERATOR
# ═══════════════════════════════════════════════════════════════
def generate_html_test(test_name: str, questions: List[dict], s: Dict) -> str:
    if s.get("shuffle_questions"): random.shuffle(questions)
    if s.get("shuffle_options"):
        for q in questions:
            for k in ("options_en", "options_hi"):
                items = list(q[k].items()); random.shuffle(items); q[k] = dict(items)
    if s.get("question_limit", 0) > 0:
        questions = questions[:s["question_limit"]]

    q_json = json.dumps(questions, ensure_ascii=False)
    s_json = json.dumps(s, ensure_ascii=False)
    instr = s.get("instructions", "").replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{test_name} | Testify By Aarav</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root{{--card:rgba(255,255,255,.05);--gold:#ffd700;--ok:#2ed573;--bad:#ff4757}}
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}}
body{{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);min-height:100vh;color:#fff;padding:15px}}
.wrap{{max-width:860px;margin:0 auto}}
.hdr{{background:var(--card);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.1);border-radius:20px;padding:20px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
.brand{{color:var(--gold);font-weight:800;font-size:13px;letter-spacing:2px}}
.tmr{{background:linear-gradient(135deg,#ff4757,#ff6b81);padding:10px 18px;border-radius:12px;font-weight:700;font-size:18px;box-shadow:0 4px 15px rgba(255,71,87,.4)}}
.lbtn{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#fff;padding:8px 14px;border-radius:10px;cursor:pointer;font-weight:600}}
.qbox{{background:var(--card);border:1px solid rgba(255,255,255,.1);border-radius:20px;padding:22px;margin-bottom:18px}}
.qtxt{{font-size:17px;line-height:1.7;margin-bottom:18px;white-space:pre-wrap}}
.opt{{background:rgba(255,255,255,.03);border:2px solid rgba(255,255,255,.08);border-radius:14px;padding:14px;margin:9px 0;cursor:pointer;display:flex;gap:12px;align-items:center;transition:.25s}}
.opt:hover{{border-color:var(--gold)}}
.opt.sel{{border-color:var(--gold);background:rgba(255,215,0,.15)}}
.opt.cor{{border-color:var(--ok);background:rgba(46,213,115,.15)}}
.opt.wrn{{border-color:var(--bad);background:rgba(255,71,87,.15)}}
.opt.hid{{opacity:.25;pointer-events:none}}
.key{{background:rgba(255,255,255,.1);width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}}
.opt.sel .key{{background:var(--gold);color:#000}}
.opt.cor .key{{background:var(--ok)}}
.opt.wrn .key{{background:var(--bad)}}
.pal{{display:grid;grid-template-columns:repeat(auto-fill,minmax(42px,1fr));gap:8px;margin:14px 0}}
.pb{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);color:#fff;padding:11px 0;border-radius:10px;cursor:pointer;font-weight:600}}
.pb.ans{{background:var(--ok);border-color:var(--ok)}}
.pb.cur{{background:var(--gold);color:#000;border-color:var(--gold)}}
.pb.bm{{outline:2px solid var(--bad)}}
.btn{{background:linear-gradient(135deg,#ffd700,#ff9500);color:#000;border:none;padding:13px 24px;border-radius:13px;font-weight:700;cursor:pointer;margin:5px;font-size:14px}}
.btn.sec{{background:rgba(255,255,255,.08);color:#fff}}
.ll{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:10px 16px;margin:5px;display:inline-flex;cursor:pointer;font-size:13px}}
.ll:hover{{background:rgba(255,255,255,.12)}}
.res{{background:var(--card);border-radius:24px;padding:30px;text-align:center}}
.score{{font-size:52px;font-weight:800;background:linear-gradient(135deg,#ffd700,#ff9500);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:15px 0}}
.stat{{display:flex;justify-content:center;gap:25px;flex-wrap:wrap;margin:15px 0;font-size:14px}}
.exp{{background:rgba(46,213,115,.08);border-left:4px solid var(--ok);padding:14px;margin-top:14px;border-radius:10px;line-height:1.6;font-size:14px}}
#startScr{{position:fixed;inset:0;background:rgba(15,12,41,.96);backdrop-filter:blur(12px);z-index:99;display:flex;align-items:center;justify-content:center;padding:20px}}
.scard{{background:var(--card);border:1px solid rgba(255,255,255,.12);border-radius:24px;padding:28px;max-width:520px;width:100%;text-align:center}}
.scard input{{width:100%;padding:13px;border-radius:12px;border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.05);color:#fff;margin:14px 0;font-size:15px}}
.inst{{text-align:left;background:rgba(255,255,255,.04);padding:14px;border-radius:12px;margin:14px 0;font-size:13px;line-height:1.7}}
</style>
</head>
<body>
<div id="startScr"><div class="scard">
<div class="brand" style="font-size:16px;margin-bottom:12px">✦ TESTIFY BY AARAV ✦</div>
<h2>{test_name}</h2>
<div style="opacity:.8;font-size:13px;margin-top:8px">⏱ {s['duration']} min · 🎯 {s['marks_per_question']} marks/Q · ❌ -{s['negative_marking']} negative</div>
<div class="inst">{instr}</div>
<input id="uName" placeholder="Enter your name">
<button class="btn" style="width:100%" onclick="begin(true)">🚀 Start Test</button>
<button class="btn sec" id="resumeBtn" style="width:100%;display:none" onclick="begin(false)">💾 Resume Previous Attempt</button>
</div></div>

<div class="wrap" id="app" style="display:none">
<div class="hdr">
<div><div class="brand">✦ TESTIFY BY AARAV</div><div id="uDisp" style="margin-top:4px;font-weight:600">👤 Candidate</div></div>
<div style="display:flex;gap:10px;align-items:center">
<button class="lbtn" id="langBtn" onclick="togLang()">🌐 हिंदी</button>
<div class="tmr" id="tmr">⏱ 00:00</div>
</div></div>

<div id="testArea">
<div class="qbox"><div class="qtxt" id="qTxt"></div><div id="optArea"></div></div>
<div><strong>📋 Question Palette</strong><div class="pal" id="pal"></div></div>
<div><strong>🛟 Lifelines</strong><div id="llArea" style="margin-top:8px"></div></div>
<div style="text-align:center;margin:25px 0">
<button class="btn sec" onclick="nav(-1)">← Prev</button>
<button class="btn sec" onclick="nav(1)">Next →</button>
<button class="btn sec" onclick="togBm()">🔖 Bookmark</button>
<button class="btn" onclick="submit()">✓ Submit</button>
</div></div>
<div id="resArea" style="display:none"></div>
<div style="text-align:center;padding:25px;opacity:.5;font-size:11px;letter-spacing:1px">TESTIFY BY AARAV · EXAM STUDIO</div>
</div>

<script>
const Q={q_json}, S={s_json};
let cur=0, ans={{}}, bmk=new Set(), hid={{}}, ll={{...S.lifelines}}, time=S.duration*60, tmrInt=null, uName='Candidate';
let lang=(S.language_mode==='hindi')?'hi':'en', started=false;
const LS='testify_'+S.test_name.replace(/\\s/g,'_');

function save(){{ if(!S.resume_enabled||!started)return;
  localStorage.setItem(LS, JSON.stringify({{ans,bmk:[...bmk],cur,time,uName,lang}})); }}
function loadSave(){{ try{{ const d=localStorage.getItem(LS); return d?JSON.parse(d):null; }}catch(e){{ return null; }} }}

if(S.resume_enabled && loadSave()) document.getElementById('resumeBtn').style.display='block';

function begin(fresh){{
  const n=document.getElementById('uName').value.trim();
  if(n) uName=n;
  if(!fresh){{ const d=loadSave(); if(d){{ ans=d.ans||{{}}; bmk=new Set(d.bmk||[]); cur=d.cur||0; time=d.time||time; uName=d.uName||uName; lang=d.lang||lang; }} }}
  else localStorage.removeItem(LS);
  started=true;
  document.getElementById('uDisp').textContent='👤 '+uName;
  document.getElementById('startScr').style.display='none';
  document.getElementById('app').style.display='block';
  updLangBtn(); render(); startTmr(); setInterval(save,3000);
}}

function updLangBtn(){{ document.getElementById('langBtn').textContent = lang==='en' ? '🌐 हिंदी' : '🌐 English'; }}
function togLang(){{ lang = lang==='en'?'hi':'en'; updLangBtn(); render(); }}

function qText(q){{ return (lang==='hi'&&q.question_hi)?q.question_hi:q.question_en; }}
function qOpts(q){{ return (lang==='hi'&&q.options_hi)?q.options_hi:q.options_en; }}
function qExp(q){{ return (lang==='hi'&&q.explanation_hi)?q.explanation_hi:q.explanation_en; }}

function render(){{
  const q=Q[cur];
  document.getElementById('qTxt').innerHTML=`<strong>Q${{cur+1}}/${{Q.length}}.</strong><br><br>${{qText(q).replace(/\\n/g,'<br>')}}`;
  const oa=document.getElementById('optArea'); oa.innerHTML='';
  Object.entries(qOpts(q)).forEach(([k,v])=>{{
    const d=document.createElement('div');
    d.className='opt'+(ans[cur]===k?' sel':'')+((hid[cur]||[]).includes(k)?' hid':'');
    d.innerHTML=`<div class="key">${{k}}</div><div>${{v}}</div>`;
    d.onclick=()=>{{ ans[cur]=k; render(); save(); }};
    oa.appendChild(d);
  }});
  renderPal(); renderLL();
}}

function renderPal(){{
  const p=document.getElementById('pal'); p.innerHTML='';
  Q.forEach((_,i)=>{{
    const b=document.createElement('button');
    b.className='pb'+(ans[i]!==undefined?' ans':'')+(i===cur?' cur':'')+(bmk.has(i)?' bm':'');
    b.textContent=i+1; b.onclick=()=>{{ cur=i; render(); save(); }};
    p.appendChild(b);
  }});
}}

function renderLL(){{
  const a=document.getElementById('llArea'); a.innerHTML='';
  [['fifty_fifty','🎯 50:50'],['smart_hint','💡 Smart Hint'],['skip_question','⏭ Skip'],['extra_time','⏱ +30s']]
  .forEach(([k,l])=>{{ if(ll[k]>0){{
    const d=document.createElement('div'); d.className='ll';
    d.innerHTML=`${{l}} <small>(${{ll[k]}})</small>`; d.onclick=()=>useLL(k); a.appendChild(d);
  }}}});
}}

function useLL(k){{
  if(ll[k]<=0)return; ll[k]--;
  const q=Q[cur];
  if(k==='fifty_fifty'){{
    const wrong=Object.keys(qOpts(q)).filter(x=>x!==q.answer).sort(()=>Math.random()-.5).slice(0,2);
    hid[cur]=wrong;
  }} else if(k==='smart_hint'){{
    const t=(qOpts(q)[q.answer]||''); alert('💡 Hint: Sahi option ka pehla akshar "'+(t.charAt(0)||'?')+'" hai, length '+t.length+' characters.');
  }} else if(k==='skip_question'){{ delete ans[cur]; nav(1); }}
  else if(k==='extra_time'){{ time+=30; }}
  render(); save();
}}

function nav(d){{ if(cur+d>=0&&cur+d<Q.length){{ cur+=d; render(); save(); }} }}
function togBm(){{ if(bmk.has(cur))bmk.delete(cur); else bmk.add(cur); renderPal(); save(); }}

function startTmr(){{
  tmrInt=setInterval(()=>{{
    time--; if(time<=0){{ clearInterval(tmrInt); submit(); return; }}
    const m=Math.floor(time/60), sec=time%60;
    document.getElementById('tmr').textContent=`⏱ ${{String(m).padStart(2,'0')}}:${{String(sec).padStart(2,'0')}}`;
  }},1000);
}}

function submit(){{
  clearInterval(tmrInt); localStorage.removeItem(LS); started=false;
  let cor=0,wrn=0,una=0;
  Q.forEach((q,i)=>{{ if(ans[i]===undefined)una++; else if(ans[i]===q.answer)cor++; else wrn++; }});
  const sc=(cor*S.marks_per_question)-(wrn*S.negative_marking);
  const att=cor+wrn, acc=att?Math.round(cor/att*100):0;
  const used=S.duration*60-time, um=Math.floor(used/60), us=used%60;
  document.getElementById('testArea').style.display='none';
  const r=document.getElementById('resArea'); r.style.display='block';
  r.innerHTML=`<div class="res"><h2>📊 Result — ${{uName}}</h2>
  <div class="score">${{sc}} / ${{Q.length*S.marks_per_question}}</div>
  <div class="stat"><span>✅ ${{cor}}</span><span>❌ ${{wrn}}</span><span>⚪ ${{una}}</span><span>🎯 Accuracy ${{acc}}%</span><span>⏱ Used ${{um}}m ${{us}}s</span></div>
  <button class="btn" onclick="review()">📖 Review Solutions</button>
  <button class="btn sec" onclick="location.reload()">🔄 Retake</button></div>
  <div id="revArea" style="margin-top:20px"></div>`;
}}

function review(){{
  const a=document.getElementById('revArea'); a.innerHTML='';
  Q.forEach((q,i)=>{{
    const u=ans[i], ic=u===q.answer;
    let oh='';
    Object.entries(qOpts(q)).forEach(([k,v])=>{{
      let c='opt'; if(k===q.answer)c+=' cor'; else if(k===u)c+=' wrn';
      oh+=`<div class="${{c}}"><div class="key">${{k}}</div><div>${{v}}</div></div>`;
    }});
    a.innerHTML+=`<div class="qbox"><div class="qtxt"><strong>Q${{i+1}}.</strong> ${{ic?'✅':(u?'❌':'⚪')}}<br><br>${{qText(q).replace(/\\n/g,'<br>')}}</div>${{oh}}
    ${{qExp(q)?`<div class="exp">💡 ${{qExp(q)}}</div>`:''}}</div>`;
  }});
}}
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# PRIVATE MODE HANDLERS
# ═══════════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ("group", "supergroup"):
        await update.message.reply_text(
            "✦ *TESTIFY POLL QUIZ BOT* ✦\n\n"
            "*Admin Commands:*\n/setup • /startquiz 30 • /stopquiz\n/setmarks 4 • /setneg 1 • /leaderboard • /quizhelp",
            parse_mode=ParseMode.MARKDOWN)
        return
    get_user(update.effective_user.id)["step"] = "menu"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Paste Questions", callback_data="paste_q"),
         InlineKeyboardButton("📂 Import TXT", callback_data="upload_txt")],
        [InlineKeyboardButton("🤖 AI Prompt Studio", callback_data="ai_prompt")],
        [InlineKeyboardButton("⚙️ Test Settings", callback_data="settings"),
         InlineKeyboardButton("🛟 Lifelines", callback_data="lifelines")],
        [InlineKeyboardButton("🚀 Generate & Download HTML", callback_data="generate")],
        [InlineKeyboardButton("📢 Join @sjvbots", url="https://t.me/sjvbots")]
    ])
    txt = ("✦ *TESTIFY BY AARAV* ✦\n━━━━━━━━━━━━━━━━━━━━━━\n"
           "🎯 *Premium CBT Test Builder*\n\n"
           "✨ *Premium Features:*\n"
           "🌐 Bilingual Switch (HI/EN)\n💾 Resume After Refresh\n"
           "🎫 Start Screen + Instructions\n📊 Accuracy & Time Analytics\n"
           "🔖 Bookmarks + Palette\n🛟 4 Lifelines\n🎲 Shuffle Engine\n"
           "🤖 AI Prompt (Rajasthani + Ultra Extreme)\n━━━━━━━━━━━━━━━━━━━━━━\n"
           "Option chunein 👇")
    if update.callback_query:
        await update.callback_query.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(txt, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def cb_paste(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    get_user(q.from_user.id)["step"] = "waiting_q"
    await q.edit_message_text(
        "📝 *Paste Questions*\n\n`Q1. [EN] Statement`\n`[HI] Statement`\n`👉 Question?`\n"
        "`(a) Opt`\n`(b) Opt ✅`\n`Ex: [EN] Exp`\n`[HI] Exp`\n\n❌ /start = cancel",
        parse_mode=ParseMode.MARKDOWN)


async def cb_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    get_user(q.from_user.id)["step"] = "waiting_file"
    await q.edit_message_text("📂 *.txt file* upload karein.\n❌ /start = cancel", parse_mode=ParseMode.MARKDOWN)


async def cb_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    s = get_user(q.from_user.id)["settings"]
    txt = (f"⚙️ *Test Configuration*\n━━━━━━━━━━━━━━\n📛 `{s['test_name']}`\n"
           f"⏱ {s['duration']} min · 🎯 {s['marks_per_question']} marks · ❌ -{s['negative_marking']}\n"
           f"🔢 Limit: {s['question_limit']} · 🎲 Shuffle: {'On' if s['shuffle_questions'] else 'Off'}\n"
           f"💾 Resume: {'On' if s['resume_enabled'] else 'Off'} · 🌐 {s['language_mode']}")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📛 Name", callback_data="set_name"), InlineKeyboardButton("📝 Instructions", callback_data="set_inst")],
        [InlineKeyboardButton("⏱ Duration", callback_data="set_dur"), InlineKeyboardButton("🎯 Marks", callback_data="set_marks")],
        [InlineKeyboardButton("🔢 Q Limit", callback_data="set_limit"), InlineKeyboardButton("❌ Negative", callback_data="set_neg")],
        [InlineKeyboardButton("🎲 Shuffle Qs", callback_data="tog_sq"), InlineKeyboardButton("🎲 Shuffle Opts", callback_data="tog_so")],
        [InlineKeyboardButton("💾 Resume", callback_data="tog_rs"), InlineKeyboardButton("🌐 Language", callback_data="set_lang")],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ])
    await q.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def cb_settings2(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; u = get_user(q.from_user.id); d = q.data; s = u["settings"]
    if d == "tog_sq": s["shuffle_questions"] = not s["shuffle_questions"]
    elif d == "tog_so": s["shuffle_options"] = not s["shuffle_options"]
    elif d == "tog_rs": s["resume_enabled"] = not s["resume_enabled"]
    elif d in ("set_name", "set_inst", "set_dur", "set_marks", "set_limit"):
        u["step"] = d
        msgs = {"set_name": "📛 Test name:", "set_inst": "📝 Instructions likhein:",
                "set_dur": "⏱ Duration (min):", "set_marks": "🎯 Marks/Q:", "set_limit": "🔢 Limit (0=all):"}
        await q.edit_message_text(msgs[d]); return
    elif d == "set_neg":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data="neg_" + t) for t in ["0", "0.25", "0.33", "0.5", "1"]]])
        await q.edit_message_text("❌ Negative marking:", reply_markup=kb); return
    elif d.startswith("neg_"): s["negative_marking"] = float(d[4:])
    elif d == "set_lang":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Auto", callback_data="lang_auto"),
                                    InlineKeyboardButton("Hindi", callback_data="lang_hindi"),
                                    InlineKeyboardButton("English", callback_data="lang_english"),
                                    InlineKeyboardButton("Bilingual", callback_data="lang_bilingual")]])
        await q.edit_message_text("🌐 Language mode:", reply_markup=kb); return
    elif d.startswith("lang_"): s["language_mode"] = d[5:]
    await q.answer("✅ Updated"); u["step"] = "menu"; await cb_settings(update, ctx)


async def cb_lifelines(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ll = get_user(q.from_user.id)["settings"]["lifelines"]
    txt = (f"🛟 *Custom Lifelines*\n━━━━━━━━━━━━━━\n🎯 50:50: `{ll['fifty_fifty']}` · 💡 Hint: `{ll['smart_hint']}`\n"
           f"⏭ Skip: `{ll['skip_question']}` · ⏱ +30s: `{ll['extra_time']}`")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 50:50", callback_data="ll_fifty_fifty"), InlineKeyboardButton("💡 Hint", callback_data="ll_smart_hint")],
        [InlineKeyboardButton("⏭ Skip", callback_data="ll_skip_question"), InlineKeyboardButton("⏱ +30s", callback_data="ll_extra_time")],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ])
    await q.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def cb_ll2(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; u = get_user(q.from_user.id)
    u["step"] = "setll_" + q.data[3:]
    await q.edit_message_text("Kitne uses? (number):")


async def cb_ai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    u = get_user(q.from_user.id); u["step"] = "ai_lang"; u["ai_config"] = {}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮 Hindi", callback_data="ail_hindi"), InlineKeyboardButton("🇬🇧 English", callback_data="ail_english")],
        [InlineKeyboardButton("🌐 Bilingual", callback_data="ail_bilingual"), InlineKeyboardButton("🏜 Rajasthani", callback_data="ail_rajasthani")]
    ])
    await q.edit_message_text("🤖 *AI Prompt Studio*\n\n🌐 Language:", reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def cb_ai2(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; u = get_user(q.from_user.id); d = q.data
    if d.startswith("ail_"):
        u["ai_config"]["language"] = d[4:]; u["step"] = "ai_num"
        await q.edit_message_text("🔢 Kitne questions?"); return
    if d.startswith("ailvl_"):
        u["ai_config"]["level"] = d[6:]; u["step"] = "ai_subject"
        await q.edit_message_text("📚 Subject:"); return


async def cb_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    u = get_user(q.from_user.id)
    if not u["questions"]:
        await q.edit_message_text("❌ Pehle questions paste/upload karein!"); return
    await q.edit_message_text("⏳ *Premium HTML generate ho rahi hai...*", parse_mode=ParseMode.MARKDOWN)
    try:
        html = generate_html_test(u["settings"]["test_name"], u["questions"], u["settings"])
        fn = u["settings"]["test_name"].replace(" ", "_") + "_premium.html"
        with open(fn, "w", encoding="utf-8") as f: f.write(html)
        with open(fn, "rb") as f:
            await q.message.reply_document(f, caption=(
                f"✅ *{u['settings']['test_name']}* Ready!\n📋 {len(u['questions'])} Qs · ⏱ {u['settings']['duration']} min\n"
                f"✨ Bilingual · Resume · Lifelines · Analytics\n✦ TESTIFY BY AARAV"),
                parse_mode=ParseMode.MARKDOWN)
        os.remove(fn)
    except Exception as e:
        await q.message.reply_text(f"❌ Error: {e}")


async def cb_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    get_user(q.from_user.id)["step"] = "menu"
    await start(update, ctx)


# ═══════════════════════════════════════════════════════════════
# TEXT / DOCUMENT HANDLERS
# ═══════════════════════════════════════════════════════════════
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        if setup_mode.get(chat.id):
            qs = parse_questions(update.message.text)
            if not qs:
                await update.message.reply_text("❌ Valid questions nahi mile. /quizhelp dekhein."); return
            group_questions[chat.id] = qs; setup_mode[chat.id] = False
            await update.message.reply_text(f"✅ *{len(qs)} questions load!* Ab `/startquiz 30` chalayein.", parse_mode=ParseMode.MARKDOWN)
        return

    u = get_user(update.effective_user.id); st = u["step"]; t = update.message.text.strip()

    if st == "waiting_q":
        qs = parse_questions(t)
        if not qs: await update.message.reply_text("❌ Format check karein."); return
        u["questions"] = qs; u["step"] = "menu"
        await update.message.reply_text(f"✅ *{len(qs)} questions load ho gaye!* 🎉", parse_mode=ParseMode.MARKDOWN)
    elif st in ("set_name", "set_inst"):
        u["settings"]["test_name" if st == "set_name" else "instructions"] = t
        u["step"] = "menu"; await update.message.reply_text("✅ Save ho gaya!")
    elif st in ("set_dur", "set_marks", "set_limit"):
        try:
            u["settings"][{"set_dur": "duration", "set_marks": "marks_per_question", "set_limit": "question_limit"}[st]] = int(t)
            u["step"] = "menu"; await update.message.reply_text("✅ Updated!")
        except ValueError: await update.message.reply_text("❌ Number daalein.")
    elif st.startswith("setll_"):
        try:
            u["settings"]["lifelines"][st[6:]] = int(t); u["step"] = "menu"
            await update.message.reply_text("✅ Lifeline uses set!")
        except ValueError: await update.message.reply_text("❌ Number daalein.")
    elif st == "ai_num":
        try: u["ai_config"]["num"] = int(t); u["step"] = "ai_level"
        except ValueError: await update.message.reply_text("❌ Number daalein."); return
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(x, callback_data="ailvl_" + x.lower().replace(" ", "_"))
                                    for x in ["Easy", "Moderate", "Hard"]],
                                   [InlineKeyboardButton(x, callback_data="ailvl_" + x.lower().replace(" ", "_"))
                                    for x in ["Very Hard", "Extreme", "Mixed"]]])
        await update.message.reply_text("📊 Difficulty:", reply_markup=kb)
    elif st == "ai_subject":
        u["ai_config"]["subject"] = t; u["step"] = "ai_topic"
        await update.message.reply_text("🎯 Topic:")
    elif st == "ai_topic":
        u["ai_config"]["topic"] = t; u["step"] = "ai_extra"
        await update.message.reply_text("✨ Extra requirements (ya `skip`):")
    elif st == "ai_extra":
        u["ai_config"]["extra"] = "" if t.lower() == "skip" else t
        u["step"] = "menu"
        await update.message.reply_text("✨ *AI Prompt:*\n\n```\n" + build_ai_prompt(u["ai_config"]) + "\n```\n\nIsse AI tool mein paste karein, phir questions yahan paste karein!", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("👋 /start se menu kholein.")


async def handle_doc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    is_group = chat.type in ("group", "supergroup")
    if is_group and not setup_mode.get(chat.id): return
    if not is_group and get_user(update.effective_user.id)["step"] != "waiting_file": return
    doc = update.message.document
    if not doc.file_name.lower().endswith(".txt"):
        await update.message.reply_text("❌ Sirf .txt files."); return
    await update.message.reply_text("⏳ File padhi ja rahi hai...")
    try:
        file = await ctx.bot.get_file(doc.file_id); p = f"tmp_{chat.id}.txt"
        await file.download_to_drive(p)
        with open(p, encoding="utf-8") as f: content = f.read()
        os.remove(p)
        qs = parse_questions(content)
        if not qs: await update.message.reply_text("❌ Valid questions nahi mile."); return
        if is_group:
            group_questions[chat.id] = qs; setup_mode[chat.id] = False
            await update.message.reply_text(f"✅ *{len(qs)} questions!* `/startquiz 30` se shuru karein.", parse_mode=ParseMode.MARKDOWN)
        else:
            u = get_user(update.effective_user.id); u["questions"] = qs; u["step"] = "menu"
            await update.message.reply_text(f"✅ *{len(qs)} questions load!* 🎉", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ═══════════════════════════════════════════════════════════════
# GROUP POLL QUIZ
# ═══════════════════════════════════════════════════════════════
async def is_admin(update: Update) -> bool:
    try:
        m = await update.effective_chat.get_member(update.effective_user.id)
        return m.status in ("creator", "administrator")
    except Exception:
        return False


def get_cfg(cid: int) -> dict:
    return group_config.setdefault(cid, {"marks": 4, "neg": 0})


def lb_text(scores: dict, title: str) -> str:
    if not scores: return title + "\n\nKoi score nahi."
    txt = title + "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for r, (uid, d) in enumerate(sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)[:10], 1):
        txt += f"{{1:'🥇',2:'🥈',3:'🥉'}.get({r},'🏅')} *{r}. {d['name']}* — {d['score']} pts\n".replace("{1:'🥇',2:'🥈',3:'🥉'}.get(" + str(r) + ",'🏅')", {1: "🥇", 2: "🥈", 3: "🥉"}.get(r, "🏅"))
    return txt


async def g_setup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"): return await update.message.reply_text("❌ Sirf groups.")
    if not await is_admin(update): return await update.message.reply_text("❌ Admin only.")
    setup_mode[update.effective_chat.id] = True
    await update.message.reply_text("📝 *Setup Mode ON* — questions paste karein ya .txt bhejein.\n❌ /cancelsetup", parse_mode=ParseMode.MARKDOWN)


async def g_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    setup_mode.pop(update.effective_chat.id, None)
    await update.message.reply_text("✅ Setup band.")


async def g_marks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return await update.message.reply_text("❌ Admin only.")
    try:
        get_cfg(update.effective_chat.id)["marks"] = float(update.message.text.split()[1])
        await update.message.reply_text("✅ Marks set!")
    except Exception: await update.message.reply_text("Usage: /setmarks 4")


async def g_neg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return await update.message.reply_text("❌ Admin only.")
    try:
        get_cfg(update.effective_chat.id)["neg"] = float(update.message.text.split()[1])
        await update.message.reply_text("✅ Negative set!")
    except Exception: await update.message.reply_text("Usage: /setneg 1")


async def g_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if update.effective_chat.type not in ("group", "supergroup"): return await update.message.reply_text("❌ Sirf groups.")
    if not await is_admin(update): return await update.message.reply_text("❌ Admin only.")
    qs = group_questions.get(cid)
    if not qs: return await update.message.reply_text("❌ Pehle /setup karein!")
    if cid in active_quizzes and active_quizzes[cid]["active"]: return await update.message.reply_text("⚠️ Quiz chal raha hai! /stopquiz")
    try: t = max(5, min(600, int(update.message.text.split()[1])))
    except Exception: t = 30
    cfg = get_cfg(cid)
    active_quizzes[cid] = {"questions": qs, "index": 0, "scores": {}, "answers": {}, "active": True,
                           "time": t, "marks": cfg["marks"], "neg": cfg["neg"],
                           "poll_id": None, "poll_msg_id": None, "correct_idx": None, "letters": [], "event": asyncio.Event()}
    await update.message.reply_text(f"🚀 *QUIZ SHURU!* {len(qs)} questions · ⏱ {t}s/poll · 🎯 +{cfg['marks']}/-{cfg['neg']}", parse_mode=ParseMode.MARKDOWN)
    asyncio.create_task(quiz_loop(cid, ctx))


async def quiz_loop(cid: int, ctx: ContextTypes.DEFAULT_TYPE):
    quiz = active_quizzes[cid]
    for i, q in enumerate(quiz["questions"]):
        if not quiz["active"]: break
        quiz["index"] = i; quiz["answers"] = {}
        letters = [l for l in LETTERS if l in q["options_en"]]
        if q["answer"] not in letters or len(letters) < 2: continue
        quiz["letters"] = letters; quiz["correct_idx"] = letters.index(q["answer"])
        full = f"❓ QUESTION {i+1}/{len(quiz['questions'])}\n\n{q['question_en']}"
        pq = full if len(full) <= 300 else f"❓ Q{i+1}: Sahi option chunein (question upar)"
        if len(full) > 300:
            try: await ctx.bot.send_message(cid, full)
            except Exception: pass
        try:
            msg = await ctx.bot.send_poll(chat_id=cid, question=pq,
                                          options=[q["options_en"][l][:100] for l in letters],
                                          type=Poll.QUIZ, correct_option_id=quiz["correct_idx"],
                                          explanation=(q["explanation_en"][:200] or None),
                                          is_anonymous=False, open_period=quiz["time"])
        except Exception: continue
        quiz["poll_id"] = msg.poll.id; quiz["poll_msg_id"] = msg.message_id
        poll_map[msg.poll.id] = cid
        quiz["event"].clear()
        try: await asyncio.wait_for(quiz["event"].wait(), timeout=quiz["time"] + 15)
        except asyncio.TimeoutError: pass
        poll_map.pop(quiz["poll_id"], None)
        await asyncio.sleep(3)
    quiz["active"] = False; last_results[cid] = quiz["scores"]
    await ctx.bot.send_message(cid, lb_text(quiz["scores"], "🏆 *FINAL LEADERBOARD* 🏆") + f"\n\n✦ TESTIFY BY AARAV · {CHANNEL}", parse_mode=ParseMode.MARKDOWN)
    active_quizzes.pop(cid, None)


async def g_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id; quiz = active_quizzes.get(cid)
    if not quiz or not quiz["active"]: return await update.message.reply_text("❌ Koi quiz nahi.")
    if not await is_admin(update): return await update.message.reply_text("❌ Admin only.")
    quiz["active"] = False
    if quiz["poll_id"] and quiz["poll_msg_id"]:
        try: await ctx.bot.stop_poll(cid, quiz["poll_msg_id"])
        except Exception: pass
    quiz["event"].set()
    await update.message.reply_text("⏹ *Quiz stopped!*", parse_mode=ParseMode.MARKDOWN)


async def g_lb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id; quiz = active_quizzes.get(cid)
    if quiz and quiz["active"]:
        await update.message.reply_text(lb_text(quiz["scores"], "📊 *LIVE Leaderboard*"), parse_mode=ParseMode.MARKDOWN)
    elif cid in last_results:
        await update.message.reply_text(lb_text(last_results[cid], "🏆 *Last Result*"), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Koi scores nahi.")


async def g_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Poll Quiz Guide*\n━━━━━━━━━━━━━━\n"
        "1️⃣ /setup → questions paste/.txt\n2️⃣ /startquiz 30 → poll quiz\n"
        "3️⃣ Timer khatam → auto result + explanation\n4️⃣ /leaderboard → scores\n\n"
        "Format: `Q1. Statement` + `👉 Q?` + `(a)..(d) ✅` + `Ex:`\n"
        "BotFather: Privacy Mode DISABLE karein.", parse_mode=ParseMode.MARKDOWN)


async def on_poll_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pa = update.poll_answer; cid = poll_map.get(pa.poll_id)
    if not cid: return
    quiz = active_quizzes.get(cid)
    if not quiz or not quiz["active"] or pa.poll_id != quiz["poll_id"] or not pa.user: return
    quiz["answers"][pa.user.id] = {"name": pa.user.first_name, "opt": (pa.option_ids[0] if pa.option_ids else None)}


async def on_poll_state(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    poll = update.poll; cid = poll_map.get(poll.id)
    if not cid: return
    quiz = active_quizzes.get(cid)
    if not quiz or poll.id != quiz["poll_id"] or not poll.is_closed: return
    if quiz["active"]:
        cor = quiz["correct_idx"]; right, wrong = [], []
        for uid, d in quiz["answers"].items():
            sc = quiz["scores"].setdefault(uid, {"name": d["name"], "score": 0})
            if d["opt"] == cor: sc["score"] += quiz["marks"]; right.append(d["name"])
            elif d["opt"] is not None: sc["score"] -= quiz["neg"]; wrong.append(d["name"])
        q = quiz["questions"][quiz["index"]]; L = quiz["letters"][cor]
        try:
            await ctx.bot.send_message(cid,
                f"⏰ *Q{quiz['index']+1} Result*\n✅ Sahi: *({L})* {q['options_en'][L]}\n"
                f"🎯 {', '.join(right) if right else 'Koi nahi'}\n❌ {', '.join(wrong) if wrong else 'Koi nahi'}\n\n"
                + lb_text(quiz["scores"], "📊 *Top Scorers*"), parse_mode=ParseMode.MARKDOWN)
        except Exception: pass
    quiz["event"].set()


# ═══════════════════════════════════════════════════════════════
# MAIN (Render / Python 3.14 Fixed)
# ═══════════════════════════════════════════════════════════════
def main():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed(): raise RuntimeError
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setup", g_setup))
    app.add_handler(CommandHandler("cancelsetup", g_cancel))
    app.add_handler(CommandHandler("startquiz", g_start))
    app.add_handler(CommandHandler("stopquiz", g_stop))
    app.add_handler(CommandHandler("setmarks", g_marks))
    app.add_handler(CommandHandler("setneg", g_neg))
    app.add_handler(CommandHandler("leaderboard", g_lb))
    app.add_handler(CommandHandler("quizhelp", g_help))

    app.add_handler(CallbackQueryHandler(cb_paste, pattern="^paste_q$"))
    app.add_handler(CallbackQueryHandler(cb_upload, pattern="^upload_txt$"))
    app.add_handler(CallbackQueryHandler(cb_settings, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(cb_settings2, pattern="^(set_|tog_|neg_|lang_)"))
    app.add_handler(CallbackQueryHandler(cb_lifelines, pattern="^lifelines$"))
    app.add_handler(CallbackQueryHandler(cb_ll2, pattern="^ll_"))
    app.add_handler(CallbackQueryHandler(cb_ai, pattern="^ai_prompt$"))
    app.add_handler(CallbackQueryHandler(cb_ai2, pattern="^(ail_|ailvl_)"))
    app.add_handler(CallbackQueryHandler(cb_generate, pattern="^generate$"))
    app.add_handler(CallbackQueryHandler(cb_menu, pattern="^menu$"))

    app.add_handler(PollAnswerHandler(on_poll_answer))
    app.add_handler(PollHandler(on_poll_state))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🚀 Testify Ultimate Premium Bot running...")
    try: signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    except Exception: pass
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES, timeout=60)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot stopped.")
