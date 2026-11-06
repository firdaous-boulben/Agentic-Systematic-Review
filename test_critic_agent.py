
from agents.critic_agent import run_critic_agent

sample_state = {
    "topic": "Explainable Recommender Systems in Education",
    "research_question": (
        "How are explainability methods integrated into "
        "educational recommender systems?"
    ),
    "extracted_data": [
        {
            "title": "Example Study",
            "extracted_information": {
                "main_findings": "Example findings from the abstract."
            }
        }
    ],
    "quality_results": [],
    "synthesis": """
    The available abstract reports collaborative filtering
    and knowledge-based recommendation techniques.
    It does not report an explainability method.
    """
}

result = run_critic_agent(sample_state)

print("\n========== CRITIC FEEDBACK ==========")
print(result["critic_feedback"])

print("\nValidation status:", result["validation_status"])
