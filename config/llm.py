import os
import inspect

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from config.token_tracker import GroqTokenTracker

load_dotenv(override=True)

def get_llm(max_tokens=2000, reasoning_effort="low"):
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")

    if not api_key:
        raise ValueError("GROQ_API_KEY is missing.")

    if not model:
        raise ValueError("GROQ_MODEL is missing.")
    
    frame = inspect.currentframe().f_back
    try:
        agent_name = frame.f_globals.get(
            "__name__", "unknown"
        ).split(".")[-1]
        
    finally:
        del frame

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key.strip(),
        openai_api_base="https://api.groq.com/openai/v1",
        temperature=0,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        callbacks=[
            GroqTokenTracker(agent=agent_name, model=model)
        ]
    )