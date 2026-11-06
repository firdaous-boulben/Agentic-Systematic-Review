from dotenv import load_dotenv
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config.llm import get_llm

load_dotenv()

# Initialize the LLM
llm = get_llm()

parser = JsonOutputParser()

# Protocol generation prompt
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert in systematic literature reviews.

Your task is to generate a preliminary review protocol
based on the research topic provided.

Generate:
1. A clear research question.
2. Research objectives.
3. Inclusion criteria.
4. Exclusion criteria.
5. Relevant search keywords.
6. Suggested academic databases.
7. A proposed publication year range.

Make the criteria specific and relevant to the topic.
Do not invent research findings or claim that searches
have already been conducted.

The publication year range must extend to the current year,
unless the user specifies a different end year.
Choose an appropriate starting year based on the research topic.
Use the same range consistently in the inclusion and exclusion criteria.

EXTRACTION DIMENSIONS:

Generate a list of 4 to 8 topic-specific extraction dimensions
based on the research topic, research question, and objectives.

These dimensions must identify the specific information
that should be collected from each included study.

Rules:
- Adapt the dimensions to the given research topic.
- Do not use predefined dimensions tied to a particular domain.
- Prefer specific research concepts, methods, technologies,
  variables, or outcomes relevant to the topic.
- Avoid repeating the universal extraction fields.
- Use concise and clear dimension names.
- Ensure the dimensions help answer the research question.

Return only valid JSON with these keys:
research_question,
objectives,
inclusion_criteria,
exclusion_criteria,
keywords,
databases,
publication_year_range,
extraction_dimensions."""
    ),
    (
        "human",
        "Generate a systematic review protocol for this topic: {topic}. The current year is {current_year}."
    )
])

# Build the generation chain
protocol_chain = prompt | llm | parser


def generate_protocol(topic: str) -> dict:

    print("\n[Protocol Agent] Generating review protocol...")

    protocol = protocol_chain.invoke({
        "topic": topic,
        "current_year": datetime.now().year
    })

    print("[Protocol Agent] Protocol generated successfully.")

    return protocol
