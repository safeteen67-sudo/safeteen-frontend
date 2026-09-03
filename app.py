import os
import re
import logging

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("safeteen")

app = Flask(__name__)

# ตั้งค่า origin ของ Cloudflare Pages ให้ตรงกับโดเมนจริงของคุณหลัง deploy
# เช่น "https://safeteen.pages.dev" — ห้ามปล่อยเป็น "*" ถ้าจะใช้งานจริง
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGIN}})

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

SYSTEM_INSTRUCTION = """\
คุณคือ SafeTeen Assistant — ผู้ช่วยให้ความรู้ด้านสุขภาวะทางเพศสำหรับเยาวชนไทย
หลักการทำงาน:
1. ให้ข้อมูลที่ถูกต้องตามหลักวิชาการเรื่องเพศศึกษา การคุมกำเนิด และการป้องกันโรคติดต่อทางเพศสัมพันธ์
2. ใช้ภาษาที่เป็นมิตร ไม่ตัดสิน ไม่ทำให้ผู้ถามรู้สึกอาย
3. ไม่วินิจฉัยอาการทางการแพทย์ — แนะนำให้พบแพทย์หรือคลินิกเมื่อเป็นเรื่องเฉพาะบุคคล
4. หากมีสัญญาณว่าผู้ใช้กำลังตกอยู่ในอันตราย ถูกล่วงละเมิด หรือคิดทำร้ายตัวเอง
   ให้ตอบด้วยความห่วงใย และแนะนำให้ติดต่อผู้ใหญ่ที่ไว้ใจได้หรือสายด่วนที่เกี่ยวข้องทันที
   อย่าให้ข้อมูลที่อาจเพิ่มความเสี่ยง
5. ไม่สร้างเนื้อหาทางเพศแบบชัดเจนหรือกระตุ้นอารมณ์ทางเพศ ตอบในเชิงให้ความรู้เท่านั้น
6. คำตอบกระชับ อ่านง่าย เหมาะกับผู้อ่านวัยรุ่น
"""

# คำที่บ่งชี้ความเสี่ยงเร่งด่วน — ใช้เป็นตัวกรองเบื้องต้นก่อนส่งต่อให้ AI
# นี่เป็นเพียง safety net อย่างง่าย ไม่ควรใช้แทนระบบคัดกรองที่ผ่านการออกแบบโดยผู้เชี่ยวชาญ
CRISIS_PATTERNS = [
    r"ฆ่าตัวตาย", r"อยากตาย", r"ทำร้ายตัวเอง", r"ถูกข่มขืน", r"ถูกล่วงละเมิด",
]

CRISIS_NOTICE = (
    "ขอบคุณที่เล่าให้ฟัง เรื่องนี้สำคัญและไม่ควรแบกไว้คนเดียว "
    "ลองติดต่อผู้ใหญ่ที่คุณไว้ใจ หรือสายด่วนสุขภาพจิต 1323 (โทรฟรี 24 ชม.) "
    "หรือหากอยู่ในอันตรายเฉพาะหน้า โทร 191 ทันที"
)


def contains_crisis_signal(text: str) -> bool:
    return any(re.search(p, text) for p in CRISIS_PATTERNS)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/chat", methods=["POST"])
def chat():
    if not GEMINI_API_KEY:
        return jsonify({"reply": "ระบบยังไม่ได้ตั้งค่า API key กรุณาติดต่อผู้ดูแลระบบ"}), 500

    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    anon_id = body.get("anonymous_id", "unknown")

    if not message:
        return jsonify({"reply": "พิมพ์คำถามมาได้เลยนะ"}), 400
    if len(message) > 1000:
        return jsonify({"reply": "ข้อความยาวเกินไป ลองย่อลงหน่อยนะ"}), 400

    log.info("chat message from %s (len=%d)", anon_id, len(message))

    flagged_notice = CRISIS_NOTICE if contains_crisis_signal(message) else None

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 500},
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        reply = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "ขอโทษด้วย ตอบไม่ได้ในตอนนี้ ลองใหม่อีกครั้งนะ")
        )
    except Exception as exc:
        log.exception("Gemini API call failed")
        reply = "ขอโทษด้วย ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งนะ"

    return jsonify({"reply": reply, "flagged_notice": flagged_notice})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
