from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import random

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze_video():
    data = request.get_json()
    video_url = data.get("url")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Extract video_id from URL
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        else:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        # Simulated fact-check result (later replace with AI)
        fact_check_options = ["True", "False", "Verify"]
        fact_check_result = random.choice(fact_check_options)

        return jsonify({
            "transcript": transcript,
            "fact_check": fact_check_result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
