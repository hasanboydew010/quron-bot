import requests
import os
import json
import re
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()

TOKEN = os.environ.get("8753022712:AAHkn99MGubmeYib-QBPT6mW36ZhsqCO8ig")
GROQ_KEY = os.environ.get("gsk_nBVu6SjuCPtav3yyhJ4FWGdyb3FYy8e8I7Bsz5bmAaM24121HYC19n2sXoLh")

groq_client = Groq(api_key=GROQ_KEY)

with open("quran.json", "r", encoding="utf-8") as f:
    QURAN = json.load(f)

def matn_tozalash(matn):
    matn = re.sub(r'\d+[-.]?\s*', '', matn)
    matn = re.sub(r'[\u0610-\u061A\u064B-\u065F\u0670]', '', matn)
    matn = re.sub(r'[أإآ]', 'ا', matn)
    matn = re.sub(r'[ىئ]', 'ي', matn)
    matn = re.sub(r'ة', 'ه', matn)
    return matn.strip()

def oyat_qidirish(matn):
    try:
        matn = matn_tozalash(matn)
        sozlar = matn.strip().split()
        print(f"Tozalangan: {matn}")
        qidiruv_variantlar = []
        for i in range(len(sozlar) - 2):
            variant = " ".join(sozlar[i:i+3])
            if len(variant) > 5:
                qidiruv_variantlar.append(variant[:20])
        for sura in QURAN:
            for oyat in sura["ayahs"]:
                oyat_matn = matn_tozalash(oyat["text"])
                for qidiruv in qidiruv_variantlar:
                    if qidiruv in oyat_matn:
                        sura_num = sura["number"]
                        ayat_num = oyat["numberInSurah"]
                        arabcha = oyat["text"]
                        uz = requests.get(
                            f"https://api.alquran.cloud/v1/ayah/{sura_num}:{ayat_num}/uz.sodik",
                            timeout=10
                        ).json()
                        uzbekcha = uz["data"]["text"]
                        print(f"Topildi: {sura['englishName']} {sura_num}:{ayat_num}")
                        return sura["englishName"], sura_num, ayat_num, arabcha, uzbekcha
    except Exception as e:
        print(f"Xato: {e}")
    return None

SURA_NOMLARI = {
    "fotiha": 1, "baqara": 2, "oli imron": 3, "niso": 4, "moida": 5,
    "an'om": 6, "a'rof": 7, "anfol": 8, "tavba": 9, "yunus": 10,
    "hud": 11, "yusuf": 12, "ra'd": 13, "ibrohim": 14, "hijr": 15,
    "nahl": 16, "isro": 17, "kahf": 18, "maryam": 19, "toha": 20,
    "anbiyo": 21, "haj": 22, "mu'minun": 23, "nur": 24, "furqon": 25,
    "shuaro": 26, "naml": 27, "qasas": 28, "ankabut": 29, "rum": 30,
    "luqmon": 31, "sajda": 32, "ahzob": 33, "sabo": 34, "fotir": 35,
    "yosin": 36, "soffot": 37, "sod": 38, "zumar": 39, "g'ofir": 40,
    "fussilat": 41, "shuro": 42, "zuxruf": 43, "duxon": 44, "josiya": 45,
    "ahqof": 46, "muhammad": 47, "fath": 48, "hujurot": 49, "qof": 50,
    "zoriyot": 51, "tur": 52, "najm": 53, "qamar": 54, "rahmon": 55,
    "voqia": 56, "hadid": 57, "mujodala": 58, "hashr": 59, "mumtahana": 60,
    "saf": 61, "juma": 62, "munofiqun": 63, "tag'obun": 64, "talaq": 65,
    "tahrim": 66, "mulk": 67, "qalam": 68, "haqqa": 69, "maarij": 70,
    "nuh": 71, "jin": 72, "muzzammil": 73, "muddassir": 74, "qiyoma": 75,
    "inson": 76, "mursalot": 77, "naba": 78, "noziot": 79, "abasa": 80,
    "takwir": 81, "infitor": 82, "mutaffifin": 83, "inshiqoq": 84, "buruj": 85,
    "toriq": 86, "a'lo": 87, "g'oshiya": 88, "fajr": 89, "balad": 90,
    "shams": 91, "layl": 92, "zuho": 93, "sharh": 94, "tin": 95,
    "alaq": 96, "qadr": 97, "bayyina": 98, "zalzala": 99, "odiyot": 100,
    "qoria": 101, "takosur": 102, "asr": 103, "humaza": 104, "fil": 105,
    "quraysh": 106, "mooun": 107, "kavsar": 108, "kofirun": 109, "nasr": 110,
    "masad": 111, "ixlos": 112, "falaq": 113, "nos": 114,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕌 Assalomu alaykum!\n\n"
        "🎙 Audio yuboring — qaysi oyat ekanini topaman!\n\n"
        "📖 /oyat 1 1 — Fotiha 1-oyat\n"
        "🔍 Sura nomini yozing — masalan: yosin, fotiha, kahf"
    )

async def audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Audio qabul qilindi...")
    audio = update.message.voice or update.message.audio
    file = await context.bot.get_file(audio.file_id)
    fayl = "audio_temp.ogg"
    await file.download_to_drive(fayl)
    await msg.edit_text("🎙 Ovoz tanilmoqda...")
    with open(fayl, "rb") as f:
        transcription = groq_client.audio.transcriptions.create(
            file=(fayl, f.read()),
            model="whisper-large-v3",
            language="ar",
        )
    matn = transcription.text.strip()
    print(f"Tanilgan: {matn}")
    await msg.edit_text("🔍 Quron'dan qidirilmoqda...")
    topildi = oyat_qidirish(matn)
    os.remove(fayl)
    if topildi:
        sura_nomi, sura, ayat, arabcha, uzbekcha = topildi
        await msg.edit_text(
            f"✅ Topildi!\n\n"
            f"📖 {sura_nomi} — Sura {sura}, Oyat {ayat}\n\n"
            f"🕌 {arabcha}\n\n"
            f"📝 {uzbekcha}"
        )
    else:
        await msg.edit_text(
            f"🎙 Tanilgan matn:\n{matn}\n\n"
            "😔 Topilmadi. Aniqroq audio yuboring."
        )

async def oyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sura = int(context.args[0])
        ayat = int(context.args[1])
        r = requests.get(
            f"https://api.alquran.cloud/v1/ayah/{sura}:{ayat}/editions/quran-uthmani,uz.sodik"
        )
        data = r.json()
        arabcha = data["data"][0]["text"]
        uzbekcha = data["data"][1]["text"]
        sura_nomi = data["data"][0]["surah"]["englishName"]
        await update.message.reply_text(
            f"📖 {sura_nomi} — {sura}-sura, {ayat}-oyat\n\n"
            f"🕌 {arabcha}\n\n"
            f"📝 {uzbekcha}"
        )
    except:
        await update.message.reply_text("❌ Xato! Misol: /oyat 1 1")

async def matn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text.strip().lower()
    if matn in SURA_NOMLARI:
        sura_num = SURA_NOMLARI[matn]
        r = requests.get(
            f"https://api.alquran.cloud/v1/surah/{sura_num}/editions/quran-uthmani,uz.sodik"
        )
        data = r.json()
        sura_ar = data["data"][0]
        sura_uz = data["data"][1]
        await update.message.reply_text(
            f"📖 *{matn.title()} surasi* — {sura_ar['numberOfAyahs']} oyat",
            parse_mode="Markdown"
        )
        for i in range(len(sura_ar["ayahs"])):
            javob = (
                f"*{i+1}.* {sura_ar['ayahs'][i]['text']}\n"
                f"_{sura_uz['ayahs'][i]['text']}_"
            )
            await update.message.reply_text(javob, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "🎙 Audio yuboring yoki sura nomini yozing!\n"
            "Masalan: yosin, fotiha, kahf, ixlos"
        )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("oyat", oyat))
app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, audio_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, matn_handler))

threading.Thread(target=start_health_server, daemon=True).start()
print("Bot ishga tushdi!")
app.run_polling()
