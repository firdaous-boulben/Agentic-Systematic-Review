from config.llm import get_llm

llm = get_llm()

response = llm.invoke(
    "Explain what a systematic literature review is in two sentences."
)

print("\nLLM Response:")
print(response.content)