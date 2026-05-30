const subtitle = document.getElementById("subtitle");
const meta = document.getElementById("meta");
const voice = document.getElementById("voice");
const modelStatus = document.getElementById("model-status");

let lastSignature = "";

async function fetchEvent() {
  const response = await fetch("/api/event", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`event fetch failed: ${response.status}`);
  }
  return response.json();
}

function signatureFor(event) {
  return JSON.stringify({
    text: event.text,
    audio_url: event.audio_url,
    turn: event.metadata?.turn_count,
    hunt: event.metadata?.hunt_id,
  });
}

async function applyEvent(event) {
  const signature = signatureFor(event);
  if (signature === lastSignature) {
    return;
  }
  lastSignature = signature;

  if (event.type === "empty") {
    subtitle.textContent = "狩猟アシスト待機中です。";
    meta.textContent = "event: waiting";
    return;
  }

  subtitle.textContent = event.text || "";
  const monster = event.metadata?.predicted_monster || "unknown";
  const confidence = event.metadata?.confidence;
  const turn = event.metadata?.turn_count || "-";
  const confidenceText =
    typeof confidence === "number" ? `${Math.round(confidence * 100)}%` : "-";
  meta.textContent = `turn ${turn} / ${monster} / ${confidenceText}`;

  if (event.audio_url) {
    voice.src = `${event.audio_url}?t=${Date.now()}`;
    try {
      await voice.play();
    } catch (error) {
      console.warn("Audio playback was blocked or failed.", error);
    }
  }
}

async function poll() {
  try {
    const event = await fetchEvent();
    await applyEvent(event);
  } catch (error) {
    meta.textContent = String(error);
  } finally {
    setTimeout(poll, 650);
  }
}

voice.addEventListener("play", () => document.body.classList.add("speaking"));
voice.addEventListener("ended", () => document.body.classList.remove("speaking"));
voice.addEventListener("pause", () => document.body.classList.remove("speaking"));

modelStatus.textContent =
  "Live2D assets loaded; Cubism renderer can be attached here";
poll();

