from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from urllib.parse import urlparse, parse_qs

def extract_video_id(url: str) -> str:
    """
    Extracts the video ID from different YouTube URL formats.
    Works with normal videos, shorts, and youtu.be links.
    """
    parsed_url = urlparse(url)

    # Handle youtube.com/watch?v=xxxx
    if "youtube.com" in parsed_url.netloc:
        if parsed_url.path == "/watch":
            return parse_qs(parsed_url.query).get("v", [None])[0]
        # Handle shorts
        if parsed_url.path.startswith("/shorts/"):
            return parsed_url.path.split("/shorts/")[1].split("?")[0]

    # Handle youtu.be/xxxx
    if "youtu.be" in parsed_url.netloc:
        return parsed_url.path.lstrip("/")

    return None


def fetch_transcript(url: str) -> dict:
    """
    Fetches transcript for a given YouTube URL.
    Returns dict with either transcript text or error message.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Invalid YouTube URL"}

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return {"transcript": transcript_text}

    except TranscriptsDisabled:
        return {"error": "Transcripts are disabled for this video"}
    except NoTranscriptFound:
        return {"error": "No transcript found for this video"}
    except VideoUnavailable:
        return {"error": "Video is unavailable"}
    except Exception as e:
        return {"error": str(e)}
