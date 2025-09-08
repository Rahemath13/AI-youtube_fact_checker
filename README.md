# AI youtube_fact_checker

A **YouTube Fact Checker** web application that verifies the authenticity of YouTube video content. The app extracts video transcripts, uses OpenAI’s language model for analysis, and provides fact-checked insights in real-time.

---

## 🔍 Project Overview

With the rise of misinformation on YouTube, verifying content is crucial. This project allows users to:

- Extract transcripts from any YouTube video.
- Analyze the content for accuracy using AI.
- Highlight potential misinformation or factual inconsistencies.
- Provide a user-friendly interface for quick verification.

**Tech Stack**:

- **Python**  
- **Streamlit** – Frontend and web app interface  
- **LangChain & CrewAI** – Intelligent agent for fact-checking  
- **OpenAI API** – Language model for content analysis  
- **youtube-transcript-api** – Extracts video transcripts  
- **Flask (optional)** – API endpoints for backend operations

---

## ⚙ Features

- **YouTube URL Input**: Enter any YouTube video URL to fetch the transcript.  
- **Transcript Analysis**: Summarizes and checks facts from video content.  
- **Real-time Fact Checking**: Uses AI models to validate claims.  
- **Clean UI**: Easy-to-read results with highlights for inaccurate information.  
- **Optional Screenshots**: Attach images or screenshots to support verification.  

---
Results:
![Fact Check Result](results/screenshot1.png)

## 🛠 Installation

Follow these steps to set up the project on your local machine:

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/youtube-fact-checker.git
cd youtube-fact-checker
