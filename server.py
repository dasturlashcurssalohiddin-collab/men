"""
MatnAI TTS Backend
-------------------
edge-tts asosida haqiqiy neural ovoz yaratadi va MP3 formatida qaytaradi.
Railway yoki Render'da bot.py kabi joylashtiring (siz allaqachon shu workflow bilan ishlagansiz).

Local ishga tushirish:
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8000

Railway'da:
    - Start command: uvicorn server:app --host 0.0.0.0 --port $PORT
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import edge_tts
import os

app = FastAPI(title="MatnAI TTS Backend")

# Frontend istalgan domendan (yoki file:// dan) so'rov yubora oladi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tilga qarab eng tabiiy eshitiladigan standart ovozlar
DEFAULT_VOICES = {
    "uz-UZ": ["uz-UZ-MadinaNeural", "uz-UZ-SardorNeural"],
    "en-US": ["en-US-AvaNeural", "en-US-AndrewNeural", "en-US-EmmaNeural"],
    "ru-RU": ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"],
    "tr-TR": ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"],
    "ar-SA": ["ar-SA-ZariyahNeural", "ar-SA-HamedNeural"],
    "de-DE": ["de-DE-KatjaNeural", "de-DE-ConradNeural"],
}


class TTSRequest(BaseModel):
    text: str
    voice: str = "uz-UZ-MadinaNeural"
    rate: str = "+0%"   # masalan "-20%" ... "+50%"
    pitch: str = "+0Hz"  # masalan "-20Hz" ... "+20Hz"


@app.get("/")
def root():
    return {"status": "ok", "service": "MatnAI TTS backend ishlayapti"}


@app.get("/voices")
async def list_voices():
    """Brauzer frontendi uchun tartiblangan, sodda ovozlar ro'yxati."""
    try:
        all_voices = await edge_tts.list_voices()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ovozlar ro'yxatini olishda xato: {e}")

    result = {}
    for v in all_voices:
        locale = v["Locale"]
        result.setdefault(locale, []).append({
            "name": v["ShortName"],
            "gender": v["Gender"],
        })
    return {"defaults": DEFAULT_VOICES, "all": result}


@app.post("/tts")
async def generate_tts(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Matn bo'sh bo'lishi mumkin emas")
    if len(text) > 8000:
        raise HTTPException(status_code=400, detail="Matn juda uzun (max 8000 belgi)")

    try:
        communicate = edge_tts.Communicate(text, req.voice, rate=req.rate, pitch=req.pitch)
        audio_chunks = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.extend(chunk["data"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ovoz yaratishda xato: {e}")

    if not audio_chunks:
        raise HTTPException(status_code=500, detail="Audio yaratilmadi, ovoz nomini tekshiring")

    return Response(
        content=bytes(audio_chunks),
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="matnai_audio.mp3"'},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
