/* ======= CONFIG ======= */
const BACKEND_URL = "http://127.0.0.1:5000/analyze"; // make sure Flask runs at this address

/* ======= DOM HOOKS (match your index.html exactly) ======= */
const urlInput = document.getElementById("urlInput");
const analyzeBtn = document.getElementById("analyzeBtn");
// FIX: Corrected ID to match HTML and renamed variable
const transcriptContainer = document.getElementById("transcript-container");
const factBadges = document.getElementById("factBadges");

const statChannel = document.getElementById("statChannel");
const statViews = document.getElementById("statViews");
const statLikes = document.getElementById("statLikes");
const statSubs = document.getElementById("statSubs");
const statComments = document.getElementById("statComments");
const metaChannel = document.getElementById("metaChannel");

const factVerdictButtons = document.getElementById("factVerdictButtons");
const trueBtn = document.querySelector(".true-btn");
const falseBtn = document.querySelector(".false-btn");
const verifyBtn = document.querySelector(".verify-btn");

/* ======= HELPERS ======= */
function setLoading(isLoading) {
  if (!analyzeBtn) return;
  analyzeBtn.disabled = isLoading;
  analyzeBtn.textContent = isLoading ? "Analyzing…" : "Analyze";
}

function formatTime(seconds) {
  if (seconds === undefined || seconds === null || isNaN(seconds)) return "--:--";
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
}

function formatCount(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toLocaleString();
  // sometimes yt-dlp returns strings like "1.2M" — keep as-is
  return String(v);
}

function clearTranscript() {
  transcriptContainer.innerHTML = "";
}

function renderTranscriptFromArray(items) {
  // items: [{start, text}, ...]
  transcriptContainer.innerHTML = "";
  items.forEach(({ start, text }) => {
    const row = document.createElement("div");
    row.className = "row";
    const timeHtml = `<div class="time">${formatTime(start)}</div>`;
    const textHtml = `<div class="text">${escapeHtml(text)}</div>`;
    row.innerHTML = timeHtml + textHtml;
    transcriptContainer.appendChild(row);
  });
  transcriptContainer.scrollTop = 0;
}

function renderTranscriptFromString(text) {
  transcriptContainer.innerHTML = "";
  if (!text || !text.trim()) {
    transcriptContainer.innerHTML = `<div class="text">No transcript available.</div>`;
    return;
  }
  // Try to split into paragraphs or sentences for readability.
  // First split by newlines; if not many, split by sentences.
  const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim());
  if (paragraphs.length > 1) {
    paragraphs.forEach(p => {
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `<div class="time">--:--</div><div class="text">${escapeHtml(p.trim())}</div>`;
      transcriptContainer.appendChild(row);
    });
  } else {
    // fallback: split into ~6-sentence chunks for display
    const sentences = text.match(/[^\.!\?]+[\.!\?]+/g) || [text];
    let chunk = "";
    let chunks = [];
    sentences.forEach(s => {
      if ((chunk + s).length < 180) {
        chunk += s + " ";
      } else {
        chunks.push(chunk.trim());
        chunk = s + " ";
      }
    });
    if (chunk.trim()) chunks.push(chunk.trim());
    chunks.forEach(c => {
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `<div class="time">--:--</div><div class="text">${escapeHtml(c)}</div>`;
      transcriptContainer.appendChild(row);
    });
  }
  transcriptContainer.scrollTop = 0;
}

function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderTranscript(items) {
  // items can be: array of chunks OR a string
  if (!items) {
    transcriptContainer.innerHTML = `<div class="text">No transcript found for this video.</div>`;
    return;
  }
  if (Array.isArray(items)) {
    // sometimes backend may send array of plain strings; normalize
    const normalized = items.map(it => {
      if (typeof it === "string") return { start: 0, text: it };
      // support objects with text & start
      return { start: it.start ?? 0, text: it.text ?? (it.content || "") };
    });
    renderTranscriptFromArray(normalized);
  } else if (typeof items === "string") {
    renderTranscriptFromString(items);
  } else if (typeof items === "object" && items !== null) {
    // might be {text: "...", segments: [...]}
    if (Array.isArray(items.segments)) {
      const normalized = items.segments.map(s => ({ start: s.start ?? 0, text: s.text ?? s.content ?? "" }));
      renderTranscriptFromArray(normalized);
    } else if (typeof items.text === "string") {
      renderTranscriptFromString(items.text);
    } else {
      transcriptContainer.innerHTML = `<div class="text">No transcript available.</div>`;
    }
  } else {
    transcriptContainer.innerHTML = `<div class="text">No transcript available.</div>`;
  }
}

// FIX: Corrected function to handle a single verdict string from the backend
function renderBadgesFromText(verdictText) {
  const txt = (verdictText || "").toLowerCase();
  factBadges.innerHTML = "";

  const span = document.createElement("span");
  span.className = `badge ${txt}`;
  span.textContent = txt.toUpperCase();
  factBadges.appendChild(span);
}

function showAnalyzingBadge() {
  factBadges.innerHTML = "";
  const span = document.createElement("span");
  span.className = "badge verify";
  span.textContent = "ANALYZING…";
  factBadges.appendChild(span);
}

// FIX: Corrected function to check for an exact match, not an inclusion
function highlightVerdict(verdict) {
  // verdict: "true" | "false" | "verify" (case-insensitive)
  const v = (verdict || "").toString().toLowerCase();
  if (!factVerdictButtons) return;
  // remove previous active classes
  [trueBtn, falseBtn, verifyBtn].forEach(btn => {
    if (!btn) return;
    btn.classList.remove("active");
    btn.setAttribute("aria-pressed", "false");
  });
  // Now, we check for an exact match, not an inclusion
  if (v === "true" && trueBtn) {
    trueBtn.classList.add("active");
    trueBtn.setAttribute("aria-pressed", "true");
  } else if (v === "false" && falseBtn) {
    falseBtn.classList.add("active");
    falseBtn.setAttribute("aria-pressed", "true");
  } else if (v === "verify" && verifyBtn) {
    verifyBtn.classList.add("active");
    verifyBtn.setAttribute("aria-pressed", "true");
  }
}

/* setStats: accept multiple backend shapes */
function setStatsFromResponse(data) {
  // Accept shapes:
  // 1) data.video_info = {channel, views, likes, subscribers, comments}
  // 2) data.metadata = {...}
  // 3) top-level: data.channel, data.views, data.likes, ...
  const info = data?.video_info ?? data?.metadata ?? {};

  const channel = info.channel ?? data.channel ?? data.meta?.channel ?? data.title ?? "—";
  const views = info.views ?? data.views ?? data.meta?.views ?? null;
  const likes = info.likes ?? data.likes ?? data.meta?.likes ?? null;
  const subs = info.subscribers ?? data.subscribers ?? data.meta?.subscribers ?? null;
  const comments = info.comments ?? data.comments ?? data.meta?.comments ?? null;

  statChannel.textContent = channel || "—";
  statViews.textContent = formatCount(views);
  statLikes.textContent = formatCount(likes);
  statSubs.textContent = formatCount(subs);
  statComments.textContent = formatCount(comments) || "—";
  metaChannel.textContent = channel || "—";
}

/* ======= MAIN ACTION (called by your form onsubmit) ======= */
async function analyzeVideo() {
  const url = urlInput.value?.trim();
  if (!url) {
    alert("Please paste a YouTube URL.");
    urlInput.focus();
    return;
  }

  setLoading(true);
  showAnalyzingBadge();
  clearTranscript();
  highlightVerdict(""); // reset

  try {
    const res = await fetch(BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        url
      })
    });

    // Network-level failures will throw before this point.
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`Server responded ${res.status}: ${text || "Unknown error"}`);
    }

    const data = await res.json().catch(() => null);
    if (!data) throw new Error("Server returned invalid JSON");

    // If backend returns an error wrapper
    if (data.error) {
      throw new Error(data.error);
    }
    // Some of our backend variants return {"ok":false, "error":"..."}
    if (data.ok === false && data.error) {
      throw new Error(data.error);
    }

    // ===== TRANSCRIPT =====
    // Accept data.transcript as array OR string OR data.transcript_text
    const transcriptCandidate = data.transcript ?? data.transcript_text ?? data.text ?? null;
    if (Array.isArray(transcriptCandidate) && transcriptCandidate.length) {
      renderTranscript(transcriptCandidate);
    } else if (typeof transcriptCandidate === "string" && transcriptCandidate.trim().length) {
      renderTranscript(transcriptCandidate);
    } else {
      // fallback: if backend returned 'transcript' inside object or 'description'
      const alt = data.description ?? data.meta?.description ?? "";
      if (alt && alt.length) {
        renderTranscript(alt);
      } else {
        transcriptContainer.innerHTML = `<div class="text">No transcript found for this video.</div>`;
      }
    }

    // ===== FACT-CHECK =====
    // fact_check may be string or object {verdict, explanation, confidence}
    let verdictText = "";
    if (!data.fact_check && data.verdict) {
      // some backends return 'verdict' top-level
      if (typeof data.verdict === "string") verdictText = data.verdict;
      else if (typeof data.verdict === "object" && data.verdict.verdict) verdictText = data.verdict.verdict;
    } else if (typeof data.fact_check === "string") {
      verdictText = data.fact_check;
    } else if (typeof data.fact_check === "object" && data.fact_check !== null) {
      // Try to use .verdict if present; otherwise attempt to stringify
      verdictText = data.fact_check.verdict ?? JSON.stringify(data.fact_check);
    } else {
      verdictText = "";
    }

    renderBadgesFromText(verdictText);
    highlightVerdict(verdictText);

    // Optionally display fact-check explanation in a badge area if available
    const explanation = (data.fact_check && typeof data.fact_check === "object") ? (data.fact_check.explanation ?? "") : (data.fact_check_explanation ?? "");
    if (explanation) {
      // add a small explanation node under badges
      let explNode = document.getElementById("fcExplanation");
      if (!explNode) {
        explNode = document.createElement("div");
        explNode.id = "fcExplanation";
        explNode.style.marginTop = "8px";
        explNode.style.fontSize = "13px";
        explNode.style.opacity = "0.9";
        factBadges.parentNode.insertBefore(explNode, factBadges.nextSibling);
      }
      explNode.textContent = explanation;
    } else {
      const n = document.getElementById("fcExplanation");
      if (n) n.remove();
    }

    // ===== STATS =====
    setStatsFromResponse(data);

    // Ensure fact verdict buttons are visible if they were hidden
    if (factVerdictButtons) factVerdictButtons.style.display = "flex";

  } catch (err) {
    console.error("Analyze error:", err);
    // User-friendly message
    alert(`Analyze failed: ${err.message || err}`);
    // Show error badge
    factBadges.innerHTML = `<span class="badge verify">ERROR</span>`;
  } finally {
    setLoading(false);
  }
}

/* ======= Button click handlers (visual only) ======= */
if (trueBtn) {
  trueBtn.addEventListener("click", () => {
    highlightVerdict("true");
  });
}
if (falseBtn) {
  falseBtn.addEventListener("click", () => {
    highlightVerdict("false");
  });
}
if (verifyBtn) {
  verifyBtn.addEventListener("click", () => {
    highlightVerdict("verify");
  });
}

/* Optional: also bind click in case form handler removed later */
if (analyzeBtn) {
  analyzeBtn.addEventListener("click", (e) => {
    const formParent = analyzeBtn.closest("form");
    if (formParent) return; // form submission already calls analyzeVideo
    e.preventDefault();
    analyzeVideo();
  });
}

/* Expose globally because your <form onsubmit="analyzeVideo()"> calls it */
window.analyzeVideo = analyzeVideo;