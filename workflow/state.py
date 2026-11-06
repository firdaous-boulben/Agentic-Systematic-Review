from typing import TypedDict, List, Dict, Optional, Any

class ReviewState(TypedDict, total=False):

    # 1. User input
    topic: str
    research_question: str

    # 2. Review protocol
    protocol: Dict[str, Any]
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]

    # 3. Literature search
    search_queries: List[str]
    retrieved_papers: List[Dict[str, Any]]
    unique_papers: List[Dict[str, Any]]

    # 4. Screening
    screening_results: List[Dict[str, Any]]
    included_papers: List[Dict[str, Any]]
    excluded_papers: List[Dict[str, Any]]
    uncertain_papers: List[Dict[str, Any]]

    # 5. Full-text retrieval and eligibility
    pdf_retrieval_results: List[Dict[str, Any]]
    full_text_available_papers: List[Dict[str, Any]]
    full_text_assessment_results: List[Dict[str, Any]]
    full_text_eligible_papers: List[Dict[str, Any]]
    full_text_excluded_papers: List[Dict[str, Any]]
    full_text_uncertain_papers: List[Dict[str, Any]]

    # 6. Information extraction
    extracted_data: List[Dict[str, Any]]

    # 7. Quality assessment
    quality_results: List[Dict[str, Any]]

    # 8. Synthesis and report
    synthesis: Optional[str]
    final_report: Optional[str]

    # 9. Quality control
    critic_feedback: Optional[str]
    validation_status: Optional[str]

    # 10. Human approval
    human_approval: Optional[bool]

    # 11. Execution tracking
    current_stage: str
    execution_logs: List[str]
    errors: List[str]

    # PRISMA tracking
    prisma_data: Dict[str, Any]
    prisma_diagram_path: Optional[str]