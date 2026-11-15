# ReviewAI — Agentic Systematic Literature Review

ReviewAI is an AI-powered application that automates systematic literature reviews, from a research question to a structured scientific paper in PDF format.

## 1. Features

- Automatic research protocol generation
- Academic paper search using OpenAlex and Crossref
- Metadata enrichment and duplicate removal
- Dual AI screening with human validation
- PDF retrieval and full-text eligibility assessment
- RAG-based information extraction
- Study quality assessment
- Evidence synthesis and critical evaluation
- PRISMA flow diagram generation
- Scientific manuscript generation and PDF export
- Groq token tracking and workflow recovery

## 2. Tech Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | Python, FastAPI |
| AI Model | Groq — GPT-OSS 20B |
| Agent Orchestration | LangGraph |
| RAG | ChromaDB, SentenceTransformers |
| Checkpoints | SQLite |
| PDF Generation | ReportLab |

## 3. Installation

### Requirements

- Python 3.11
- Node.js and npm
- Groq API key
- Internet connection

### Step 1 — Clone the repository

```bash
git clone https://github.com/firdaous-boulben/Agentic-Systematic-Review.git
cd Agentic-Systematic-Review
```

### Step 2 — Set up the Python environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use the Conda environment:

```bash
conda create -n ReviewAI python=3.11 -y
conda activate ReviewAI
pip install -r requirements.txt
```

### Step 3 — Configure API keys

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b

OPENALEX_API_KEY=your_openalex_api_key
CROSSREF_MAILTO=your_email@example.com
```

## 4. Run the Application

### Terminal 1 — Backend

From the project root:

```bash
export CUDA_VISIBLE_DEVICES=""

python -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8765
```

Backend: http://127.0.0.1:8765

API documentation: http://127.0.0.1:8765/docs

### Terminal 2 — Frontend

```bash
cd client
npm install
npm run dev
```

Frontend: http://localhost:5173

## 5. How to Use

1. Open the frontend.
2. Create a new review.
3. Enter your research question.
4. Let the system search and screen publications.
5. Review and approve the screening results.
6. The system processes PDFs, extracts evidence, and synthesizes findings.
7. Review the generated results.
8. Export the scientific manuscript as PDF.

### Workflow

```text
Research Question
       ↓
Protocol Generation
       ↓
Academic Search
       ↓
Deduplication & Metadata Enrichment
       ↓
Dual AI Screening
       ↓
Human Validation
       ↓
PDF Retrieval & Full-Text Eligibility
       ↓
RAG-Based Data Extraction
       ↓
Quality Assessment
       ↓
Evidence Synthesis
       ↓
Critic Validation
       ↓
PRISMA & Final Report
       ↓
Scientific PDF
```

## 6. Token Monitoring

Review Groq token consumption:

```bash
python show_token_usage.py
```

Usage records are saved in:

```text
data/token_usage.csv
```

The system tracks input tokens, output tokens, and API calls to help evaluate optimization performance.

## 7. Troubleshooting

**CUDA error**

Use CPU execution:

```bash
export CUDA_VISIBLE_DEVICES=""
```

**RAG collection empty**

If processed PDF text already exists, rebuild the index:

```bash
python -m rag.indexer
```

**Groq rate limit**

Check your API quota. Use the available workflow retry options when capacity is restored.

**Interrupted workflow**

Review progress is saved through LangGraph checkpoints in SQLite. Supported retry operations allow incomplete stages to resume without repeating the entire review.

## 8. Project Structure

```text
Agentic-Systematic-Review/
│
├── agents/          # AI agents
├── client/          # React frontend
├── config/          # LLM configuration
├── data/            # PDFs, checkpoints, RAG data
├── rag/             # Indexing and retrieval
├── server/          # FastAPI backend
├── tools/           # Search, PDF and report utilities
├── workflow/        # LangGraph orchestration
│
├── requirements.txt
├── show_token_usage.py
└── README.md
```

## 9. Limitations

- Groq's free API is subject to request and token limits.
- Some publications have missing abstracts or inaccessible PDFs.
- AI-generated assessments may contain errors.
- The six-page manuscript target depends on the volume of evidence and references.
- Researcher verification is required before academic submission.
