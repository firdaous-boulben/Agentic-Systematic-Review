from tools.report_generator import generate_review_report

sample_state = {
    "topic": "Explainable Recommender Systems in Education",
    "research_question": "How are explainability methods integrated into educational recommender systems?",
    "protocol": {},
    "search_queries": ["explainable recommender systems in education"],
    "retrieved_papers": [{"source": "OpenAlex"}],
    "prisma_data": {
        "records_identified": 50,
        "duplicates_removed": 1,
        "records_screened": 5,
        "records_excluded": 2,
        "records_included_after_screening": 2,
        "records_uncertain": 1
    },
    "screening_results": [{}, {}, {}, {}, {}],
    "included_papers": [{}, {}],
    "excluded_papers": [{}, {}],
    "uncertain_papers": [{}],
    "human_approval": True,
    "extracted_data": [],
    "quality_results": [],
    "synthesis": "Preliminary evidence synthesis.",
    "critic_feedback": "Needs revision."
}

path = generate_review_report(sample_state)

print("Generated report:", path)
