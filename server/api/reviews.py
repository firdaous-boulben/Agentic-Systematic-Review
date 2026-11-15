from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse

from server.api.schemas import ReviewCreate, ScreeningDecision
from server.services.review_service import (
    start_review,
    resume_review,
    continue_review,
    get_review,
    get_all_checkpoint_reviews,
    prepare_screening_retry,
    continue_screening_retry,
    prepare_extraction_retry,
    continue_extraction_retry,
    prepare_full_text_eligibility_retry,
    continue_full_text_eligibility_retry,
)
from server.services.review_registry import (
    register_review,
    get_registered_reviews
)
from server.services.export_service import (
    export_markdown,
    export_pdf,
    export_docx,
    export_bibtex,
)

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.post("/")
def create_review(payload: ReviewCreate, background_tasks: BackgroundTasks):
    review_id = str(uuid4())

    register_review(review_id, payload.topic)

    background_tasks.add_task(
        start_review,
        review_id,
        payload.topic
    )

    return {
        "review_id": review_id,
        "topic": payload.topic,
        "status": "started"
    }


@router.get("/")
def list_reviews():
    def report_exists(review):
        if not review:
            return False

        report_path = review.get("final_report")

        if not report_path:
            return False

        path = Path(report_path)

        if not path.is_absolute():
            path = Path.cwd() / path

        return path.is_file()

    registered = get_registered_reviews()
    registered_ids = {item["review_id"] for item in registered}

    results = []

    for item in registered:
        review = get_review(item["review_id"])

        results.append({
            "id": item["review_id"],
            "topic": item["topic"],
            "status": review["status"] if review else "queued",
            "papers": (
                len(review.get("included_papers", []))
                + len(review.get("excluded_papers", []))
                + len(review.get("uncertain_papers", []))
            ) if review else 0,
            "created_at": item["created_at"],
            "report_available": report_exists(review)
        })

    for item in get_all_checkpoint_reviews():
        review_id = item["review_id"]

        if review_id not in registered_ids:
            review = get_review(review_id)

            results.append({
                "id": review_id,
                "topic": item.get("topic") or "Untitled Review",
                "status": item["status"],
                "papers": (
                    len(item.get("included_papers", []))
                    + len(item.get("excluded_papers", []))
                    + len(item.get("uncertain_papers", []))
                ),
                "created_at": None,
                "report_available": report_exists(review)
            })

    return results

@router.get("/{review_id}")
def retrieve_review(review_id: str):
    review = get_review(review_id)

    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    return review


@router.post("/{review_id}/approve")
def approve_screening(
    review_id: str,
    payload: ScreeningDecision,
    background_tasks: BackgroundTasks
):
    review = get_review(review_id)

    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    if review["status"] != "awaiting_human_review":
        raise HTTPException(
            status_code=409,
            detail="Review is not waiting for screening approval."
        )

    background_tasks.add_task(
        resume_review,
        review_id,
        payload.dict()
    )

    return {
        "review_id": review_id,
        "status": "resuming"
    }

@router.post("/{review_id}/retry-screening")
def retry_screening(review_id: str, background_tasks: BackgroundTasks):
    review = get_review(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    if review.get("status") != "screening_incomplete":
        raise HTTPException(
            status_code=400,
            detail="This review does not require screening recovery."
        )

    try:
        prepare_screening_retry(review_id)
        background_tasks.add_task(continue_screening_retry, review_id)

        return {
            "message": "Screening retry started.",
            "review_id": review_id
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))

@router.post("/{review_id}/retry-extraction")
def retry_extraction(review_id: str, background_tasks: BackgroundTasks):
    review = get_review(review_id)

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Review not found."
        )

    if review["status"] != "extraction_incomplete":
        raise HTTPException(
            status_code=409,
            detail="Review is not waiting for extraction recovery."
        )

    try:
        prepare_extraction_retry(review_id)

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    background_tasks.add_task(
        continue_extraction_retry,
        review_id
    )

    return {
        "review_id": review_id,
        "status": "retrying_extraction"
    }

@router.post("/{review_id}/retry-full-text-eligibility")
def retry_full_text_eligibility(review_id: str, background_tasks: BackgroundTasks):
    review = get_review(review_id)

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Review not found."
        )

    allowed_stages = [
        "eligibility_partial",
        "eligibility_failed",
        "report_generated",
        "extraction_skipped",
    ]

    if review.get("current_stage") not in allowed_stages:
        raise HTTPException(
            status_code=400,
            detail="This review is not ready for full-text eligibility recovery."
        )

    try:
        prepare_full_text_eligibility_retry(review_id)

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    background_tasks.add_task(
        continue_full_text_eligibility_retry,
        review_id
    )

    return {
        "review_id": review_id,
        "status": "retrying_full_text_eligibility"
    }

@router.get("/{review_id}/report", response_class=PlainTextResponse)
async def get_review_report(review_id: str):
    review = get_review(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    report_path = review.get("final_report")

    if not report_path:
        raise HTTPException(status_code=404, detail="Report not generated yet")

    path = Path(report_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")

    return path.read_text(encoding="utf-8")

@router.post("/{review_id}/continue")
def continue_existing_review(
    review_id: str,
    background_tasks: BackgroundTasks
):
    review = get_review(review_id)

    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    if review["status"] == "awaiting_human_review":
        raise HTTPException(
            status_code=409,
            detail="Review is waiting for human approval."
        )

    if not review.get("next_nodes"):
        raise HTTPException(
            status_code=409,
            detail="No pending workflow stages to continue."
        )

    background_tasks.add_task(continue_review, review_id)

    return {
        "review_id": review_id,
        "status": "resuming",
        "next_nodes": review["next_nodes"]
    }


def create_export_response(review_id: str, exporter, media_type: str, filename: str):
    review = get_review(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    try:
        file_path = exporter(review_id, review)

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {error}"
        )


@router.get("/{review_id}/export/markdown")
def download_markdown(review_id: str):
    return create_export_response(
        review_id,
        export_markdown,
        "text/markdown",
        "systematic_review_report.md"
    )


@router.get("/{review_id}/export/pdf")
def download_pdf(review_id: str):
    return create_export_response(
        review_id,
        export_pdf,
        "application/pdf",
        "systematic_review_report.pdf"
    )


@router.get("/{review_id}/export/docx")
def download_docx(review_id: str):
    return create_export_response(
        review_id,
        export_docx,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "systematic_review_report.docx"
    )


@router.get("/{review_id}/export/bibtex")
def download_bibtex(review_id: str):
    return create_export_response(
        review_id,
        export_bibtex,
        "application/x-bibtex",
        "references.bib"
    )
