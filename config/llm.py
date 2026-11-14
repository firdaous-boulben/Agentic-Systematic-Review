import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(override=True)

def get_llm(max_tokens=2000, reasoning_effort=None):
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")

    if not api_key:
        raise ValueError("GROQ_API_KEY is missing.")

    if not model:
        raise ValueError("GROQ_MODEL is missing.")

    model_kwargs = {}
    if reasoning_effort:
        model_kwargs["reasoning"] = {
            "effort": reasoning_effort
        }

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key.strip(),
        openai_api_base="https://api.groq.com/openai/v1",
        temperature=0,
        max_tokens=max_tokens,
        model_kwargs=model_kwargs
    )