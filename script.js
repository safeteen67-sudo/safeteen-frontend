const API_BASE_URL = "https://safeteen-backend1.onrender.com";
// ---------- Anonymous ID ----------
// สุ่มใหม่ทุกครั้งที่เปิดเซสชัน เก็บไว้ใน sessionStorage เท่านั้น (หายเมื่อปิดแท็บ)
// ไม่ผูกกับชื่อ อีเมล หรือข้อมูลระบุตัวตนใดๆ
function getAnonymousId() {
  let id = sessionStorage.getItem("safeteen_anon_id");
  if (!id) {
    id = "anon-" + Math.random().toString(36).slice(2, 8) + Date.now().toString(36).slice(-4);
    sessionStorage.setItem("safeteen_anon_id", id);
  }
  return id;
}

const anonId = getAnonymousId();
document.getElementById("anon-id-badge").textContent = anonId;

// ---------- Chat ----------
const chatLog = document.getElementById("chat-log");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("chat-send");

function appendMessage(text, role) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  appendMessage(text, "user");
  chatInput.value = "";
  sendBtn.disabled = true;

  const thinkingEl = appendMessage("กำลังพิมพ์...", "bot");

  try {
    const res = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        anonymous_id: anonId
      })
    });

    if (!res.ok) throw new Error("Request failed: " + res.status);

    const data = await res.json();
    thinkingEl.textContent = data.reply || "ขอโทษด้วย ตอนนี้ระบบขัดข้อง ลองใหม่อีกครั้งนะ";

    if (data.flagged_notice) {
      appendMessage(data.flagged_notice, "system");
    }
  } catch (err) {
    thinkingEl.textContent = "เชื่อมต่อกับระบบไม่ได้ในตอนนี้ ลองใหม่อีกครั้งสักครู่นะ";
    console.error(err);
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});
