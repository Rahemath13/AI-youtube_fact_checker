import os
import re
import tempfile
import glob
from urllib.parse import urlparse, parse_qs

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# transcript libs
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

# Google API (may be optional if you prefer yt-dlp metadata fallback)
try:
    from googleapiclient.discovery import build
except Exception:
    build = None

# yt-dlp fallback (optional; helps retrieve auto-subtitles & metadata when youtube_transcript_api fails)
try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None

# ----------------- Load env -----------------
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# ----------------- Flask -----------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


# ----------------- Helpers -----------------
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url_or_id: str):
    u = (url_or_id or "").strip()
    if ID_RE.fullmatch(u):
        return u
    try:
        p = urlparse(u)
    except Exception:
        return None
    host = p.netloc.lower().replace("www.", "")
    if host == "youtu.be":
        vid = p.path.lstrip("/").split("/")[0]
        return vid if ID_RE.fullmatch(vid or "") else None
    if "youtube.com" in host:
        qs = parse_qs(p.query)
        if p.path == "/watch":
            vid = qs.get("v", [None])[0]
            return vid if ID_RE.fullmatch(vid or "") else None
        for prefix in ("/shorts/", "/embed/", "/live/"):
            if p.path.startswith(prefix):
                vid = p.path.split(prefix)[1].split("/")[0]
                return vid if ID_RE.fullmatch(vid or "") else None
    return None


def safe_int(x):
    try:
        return int(x)
    except Exception:
        return None


# small helper to parse VTT time like "00:01:23.456" or "01:23.456"
def _vtt_time_to_seconds(ts: str) -> float:
    ts = ts.strip()
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            s = float(parts[2].replace(",", "."))
        elif len(parts) == 2:
            h = 0
            m = int(parts[0])
            s = float(parts[1].replace(",", "."))
        else:
            return float(ts)
        return h * 3600 + m * 60 + s
    except Exception:
        try:
            return float(ts.replace(",", "."))
        except Exception:
            return 0.0


# ----------------- Transcript (robust) -----------------
def fetch_transcript_list(video_id: str):
    """
    Return (items_list, error_message_or_None).
    items_list = [{start: float, text: str}, ...]
    Strategy:
      1) try youtube_transcript_api.get_transcript (fast)
      2) on failure, if yt-dlp available -> download VTT (auto-sub) and parse
      3) otherwise return empty & error message
    """
    # 1) Try youtube_transcript_api (preferred)
    try:
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        out = []
        for entry in data:
            start = float(entry.get("start", 0)) if entry.get("start") is not None else 0.0
            text = (entry.get("text") or "").replace("\n", " ").strip()
            if text:
                out.append({"start": start, "text": text})
        if out:
            return out, None
        # no entries -> fall through to fallback
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        # no transcript available via API -> fall through to yt-dlp fallback
        err_msg = f"{e.__class__.__name__}: {str(e)}"
        # continue to fallback
    except Exception as e:
        # unexpected error from library (e.g. older/wrong install)
        err_msg = f"youtube_transcript_api error: {str(e)}"
        print("DEBUG: youtube_transcript_api error:", repr(e))  # helpful debug in server logs

    # 2) Fallback: try yt-dlp to download VTT subtitle and parse
    if YoutubeDL is None:
        # yt-dlp isn't installed
        return [], f"No transcript available. Fallback not installed: install yt-dlp with `pip install -U yt-dlp` (detail: {err_msg if 'err_msg' in locals() else ''})"

    try:
        tmpdir = tempfile.gettempdir()
        outtmpl = tmpdir + "/%(id)s.%(ext)s"
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "subtitlesformat": "vtt",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
        }
        url = f"https://www.youtube.com/watch?v={video_id}"
        with YoutubeDL(ydl_opts) as ydl:
            # download will write subtitle file(s) to tmpdir if available
            ydl.download([url])

        # find the produced .vtt file(s) for this id in tmpdir
        pattern = os.path.join(tmpdir, f"{video_id}*.vtt")
        candidates = glob.glob(pattern)
        vtt_path = None
        if candidates:
            # pick the first candidate (usually videoid.en.vtt or videoid.vtt)
            vtt_path = candidates[0]

        if not vtt_path:
            return [], "No subtitles available via yt-dlp."

        # parse VTT
        with open(vtt_path, "r", encoding="utf-8", errors="ignore") as fh:
            vtt_text = fh.read()

        # remove header "WEBVTT" if present
        vtt_text = re.sub(r'^\s*WEBVTT.*\n', "", vtt_text, flags=re.IGNORECASE)

        # split by blank lines (simple cue separation)
        blocks = [b.strip() for b in re.split(r'\n\s*\n', vtt_text) if b.strip()]
        items = []
        time_re = re.compile(
            r'(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3}|\d{1,2}:\d{2}:\d{2}\.\d{2,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})'
        )
        for block in blocks:
            m = time_re.search(block)
            if not m:
                continue
            start_ts = m.group(1)
            # find the text lines after the time line
            lines = block.splitlines()
            # find the index of time line
            text_lines = []
            for i, line in enumerate(lines):
                if time_re.search(line):
                    text_lines = lines[i + 1:]
                    break
            if not text_lines:
                # sometimes the block is just time + text on same lines after blank; try other approach
                parts = block.split("\n")
                text_lines = [p for p in parts if not time_re.search(p)]
            caption_text = " ".join([l.strip() for l in text_lines]).strip()
            if not caption_text:
                continue
            try:
                start_sec = _vtt_time_to_seconds(start_ts)
            except Exception:
                start_sec = 0.0
            items.append({"start": start_sec, "text": caption_text})
        # cleanup downloaded VTT files for this id
        for p in candidates:
            try:
                os.remove(p)
            except Exception:
                pass

        if items:
            return items, None
        return [], "No captions parsed from VTT."
    except Exception as e2:
        print("DEBUG: yt-dlp fallback error:", repr(e2))
        return [], f"Transcript fetch failed: {str(e2)}"


# ----------------- Metadata (YouTube Data API with fallback) -----------------
def fetch_video_metadata_using_api(video_id: str):
    """
    Primary: use YouTube Data API v3 (requires YOUTUBE_API_KEY).
    Fallback: if Google API not available or fails, try yt-dlp extract_info.
    """
    # Try Google API first (if available)
    if YOUTUBE_API_KEY and build is not None:
        try:
            yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
            vresp = yt.videos().list(part="snippet,statistics", id=video_id).execute()
            if vresp.get("items"):
                v = vresp["items"][0]
                snip = v.get("snippet", {})
                stats = v.get("statistics", {})
                channel_title = snip.get("channelTitle")
                channel_id = snip.get("channelId")
                subs = None
                if channel_id:
                    cresp = yt.channels().list(part="statistics", id=channel_id).execute()
                    if cresp.get("items"):
                        subs = cresp["items"][0]["statistics"].get("subscriberCount")
                return {
                    "title": snip.get("title"),
                    "channel": channel_title,
                    "views": safe_int(stats.get("viewCount")),
                    "likes": safe_int(stats.get("likeCount")),
                    "comments": safe_int(stats.get("commentCount")),
                    "subscribers": safe_int(subs) if subs is not None else None,
                }
        except Exception as e:
            print("DEBUG: YouTube Data API error:", repr(e))
            # fallthrough to yt-dlp fallback

    # Fallback to yt-dlp (if available)
    if YoutubeDL is not None:
        try:
            ydl_opts = {"skip_download": True, "quiet": True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False) or {}
            return {
                "title": info.get("title"),
                "channel": info.get("uploader") or info.get("channel"),
                "views": safe_int(info.get("view_count")),
                "likes": safe_int(info.get("like_count")),
                "comments": safe_int(info.get("comment_count")),
                "subscribers": None,
            }
        except Exception as e:
            print("DEBUG: yt-dlp metadata error:", repr(e))
            return {"error": f"Metadata fetch failed: {str(e)}"}

    return {"error": "Missing YOUTUBE_API_KEY and yt-dlp not installed"}


# ----------------- NEW FACT-CHECKING LOGIC -----------------
def get_fact_check_verdict(transcript_text):
    """
    Analyzes the transcript for keywords to determine a simple fact-check verdict.
    """
    transcript_lower = transcript_text.lower()

    # Check for keywords that might indicate misinformation or a disclaimer
    keywords_false = ["conspiracy theory", "false claim", "debunked", "hoax", "not true"]
    for keyword in keywords_false:
        if keyword in transcript_lower:
            return "False"

    # Check for keywords that might indicate a scientific or factual basis
    keywords_true = ["peer-reviewed study", "scientific evidence", "data shows", "verifiable"]
    for keyword in keywords_true:
        if keyword in transcript_lower:
            return "True"

    # If no strong keywords are found, default to "Verify"
    return "Verify"


# ----------------- END OF NEW FACT-CHECKING LOGIC -----------------


# ----------------- Routes -----------------
@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        data = request.get_json(force=True) or {}
        url = (data.get("url") or "").strip()
        if not url:
            return jsonify({"error": "No URL provided"}), 200

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 200

        # 1) transcript as list for your UI
        transcript_items, transcript_err = fetch_transcript_list(video_id)

        # 2) stats via YouTube API (or yt-dlp fallback)
        meta = fetch_video_metadata_using_api(video_id)

        # ----------------- NEW: Join transcript for analysis -----------------
        transcript_text = " ".join([item['text'] for item in transcript_items])

        # ----------------- NEW: Call the fact-check function -----------------
        verdict = get_fact_check_verdict(transcript_text)
        # ----------------- END OF NEW CODE -----------------

        # Build response that matches your frontend expectations
        resp = {
            "ok": True,
            "video_id": video_id,
            "transcript": transcript_items[:200],  # cap for speed
            "transcript_error": transcript_err,
            "fact_check": verdict,  # ----------------- NEW: Use the verdict variable -----------------
            "video_info": {
                "channel": meta.get("channel"),
                "views": meta.get("views"),
                "likes": meta.get("likes"),
                "subscribers": meta.get("subscribers"),
                "comments": meta.get("comments"),
            },
        }
        return jsonify(resp), 200
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


# ----------------- Run -----------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)