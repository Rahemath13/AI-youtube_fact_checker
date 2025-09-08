# agents.py
import os
from crewai import Agent, LLM

# Choose model via env or use a safe default
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")

# Create a lightweight LLM wrapper used by agents
llm = LLM(model=MODEL_NAME)

# Define agents with clear roles + goals
summarizer_agent = Agent(
    role="Summarizer",
    goal="Read a transcript and produce a short 2-line summary and 4-6 concise bullet points highlighting the main ideas.",
    backstory="You are a concise summarizer for tech & news content.",
    llm=llm,
    verbose=True
)

claim_extractor_agent = Agent(
    role="Claim Extractor",
    goal="From a transcript, extract up to 8 clear factual claims (single-sentence), include approximate timestamps if present.",
    backstory="You are good at spotting factual claims and short statements that can be verified.",
    llm=llm,
    verbose=True
)

fact_checker_agent = Agent(
    role="Fact Checker",
    goal="Verify short factual claims using web search when available; otherwise provide a cautious LLM-based check and label it 'LM-based'.",
    backstory="You are a careful fact-checker who prefers to cite sources and indicate uncertainty.",
    llm=llm,
    verbose=True
)

report_writer_agent = Agent(
    role="Report Writer",
    goal="Assemble a human-readable markdown report combining title, summary, extracted claims, verification results and sources.",
    backstory="You are a clear technical writer who produces readable reports for humans.",
    llm=llm,
    verbose=True
)
