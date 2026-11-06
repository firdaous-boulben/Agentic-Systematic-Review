import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from config.llm import get_llm

load_dotenv()

llm = get_llm()

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic research synthesis specialist.

Your task is to produce a rigorous, critical, and
evidence-based synthesis of the supplied academic studies.

The synthesis must be adapted to the research topic
and approved review protocol. Do not assume a particular
academic domain, methodology, or type of research.

ORGANIZATION:

Organize the synthesis using relevant sections such as:

1. Overview of the Evidence
2. Main Research Themes
3. Methods and Approaches
4. Comparison of Findings
5. Critical Quality Assessment
6. Research Gaps
7. Limitations of the Available Evidence
8. Future Research Directions

Adapt the section headings and their content to the
actual research topic. You may introduce, combine,
or omit sections when appropriate.

Use the topic-specific extraction dimensions from the
approved protocol to identify and organize the main themes.
Do not force irrelevant dimensions into the discussion.

EVIDENCE AND TRACEABILITY:

- Support important claims with specific study titles
  and publication years whenever available.
- Identify which studies support each finding.
- Include numerical results, sample sizes, datasets,
  and evaluation metrics when explicitly reported.
- Do not invent statistics, references, or findings.
- Avoid vague expressions such as "many studies" or
  "most papers" unless the supplied evidence supports them.
- Distinguish individual study findings from conclusions
  reported by systematic reviews or other review papers.
- Use only the supplied paper information and evidence.
- Do not invent missing bibliographic information.

METHODS AND FINDINGS:

- Identify the research methods, techniques, technologies,
  models, variables, datasets, and evaluation approaches
  relevant to the topic.
- Compare studies based on their objectives, contexts,
  methods, and reported results.
- Explain agreements and differences between findings.
- Identify information that was not reported in the
  available text.
- Do not assume that a method or result exists simply
  because it is common in the research domain.

CRITICAL EVALUATION:

- Use the supplied quality appraisal results to discuss
  methodological strengths and weaknesses.
- Connect appraisal findings to the interpretation
  and reliability of study results.
- Do not describe a study as high quality without
  supporting appraisal evidence.
- If appraisal information is unavailable, explicitly
  acknowledge this limitation.
- Do not treat missing appraisal results as evidence
  of poor study quality.

SYNTHESIS:

- Organize findings into meaningful themes.
- Identify patterns, differences, and contradictions.
- Explain the implications of the findings in relation
  to the research question.
- Identify research gaps and explain their implications.
- Suggest relevant directions for future research.
- Distinguish primary studies from review studies.
- Do not treat review conclusions as independent
  experimental findings.
- Do not generalize beyond the available evidence.
- Clearly acknowledge when evidence is preliminary,
  incomplete, or based on abstract-only extraction.

ACADEMIC STYLE:

Write in clear academic English.
Use coherent paragraphs and meaningful transitions.
Avoid simply listing or summarizing papers one by one.
Prioritize critical comparison and synthesis across studies.
Maintain an appropriately cautious academic tone."""
    ),
    (
        "human",
        """Research topic: {topic}

Research question: {research_question}

Approved review protocol:
{protocol_data}

Topic-specific extraction dimensions:
{extraction_dimensions}

Extracted paper information and quality appraisal:

{papers_data}

Produce a comprehensive, critical, and evidence-based
synthesis adapted to this research topic."""
    )
])

synthesis_chain = prompt | llm


def run_synthesis_agent(state):
    print("\\n[Synthesis Agent] Starting evidence synthesis...")

    papers = state.get("extracted_data", [])
    quality_results = state.get("quality_results", [])

    protocol = state.get("protocol", {})

    if not papers:
        print("[Synthesis Agent] No extracted papers available.")

        return {
            "synthesis": "",
            "current_stage": "synthesis_skipped",
            "execution_logs": state.get("execution_logs", []) + [
                "Synthesis skipped: no extracted papers available."
            ]
        }

    # Match quality appraisal results to their corresponding papers.
    appraisal_by_title = {
        paper.get("title"): paper.get("quality_appraisal", {})
        for paper in quality_results
    }

    papers_data = []

    for paper in papers:
        title = paper.get("title")

        papers_data.append({
            "title": title,
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "url": paper.get("url"),
            "source": paper.get("source"),
            "extraction_source": paper.get(
                "extraction_source", "unknown"
            ),
            "evidence_count": paper.get("evidence_count", 0),
            "extracted_information": paper.get(
                "extracted_information", {}
            ),
            "quality_appraisal": appraisal_by_title.get(
                title,
                paper.get("quality_appraisal", {})
            )
        })

    # Keep the protocol information relevant to the synthesis.
    protocol_summary = {
        "research_question": protocol.get("research_question"),
        "objectives": protocol.get("objectives", []),
        "inclusion_criteria": protocol.get("inclusion_criteria", []),
        "extraction_dimensions": protocol.get(
            "extraction_dimensions", []
        )
    }

    extraction_dimensions = protocol.get(
        "extraction_dimensions", []
    )

    response = synthesis_chain.invoke({
        "topic": state.get("topic", "Not specified"),
        "research_question": state.get(
            "research_question",
            protocol.get("research_question", "Not specified")
        ),
        "protocol_data": json.dumps(
            protocol_summary,
            indent=2,
            ensure_ascii=False
        ),
        "extraction_dimensions": json.dumps(
            extraction_dimensions,
            indent=2,
            ensure_ascii=False
        ),
        "papers_data": json.dumps(
            papers_data,
            indent=2,
            ensure_ascii=False
        )
    })

    synthesis = response.content

    print("\\n[Synthesis Agent] Evidence synthesis completed.")

    return {
        "synthesis": synthesis,
        "current_stage": "synthesis_completed",
        "execution_logs": state.get("execution_logs", []) + [
            f"Synthesis generated using {len(papers)} extracted papers."
        ]
    }