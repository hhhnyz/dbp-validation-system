from datetime import datetime
import csv
import io

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import QAItem, Validation


app = FastAPI(
    title="DBP Validation API",
    version="1.0.0"
)


class ValidationRequest(BaseModel):
    qa_item_id: int
    label: str
    note: str | None = None
    annotator: str | None = None


@app.get("/")
def root():
    return {
        "message": "DBP Validation API is running"
    }


@app.get("/api/items")
def get_items(
    db: Session = Depends(get_db)
):
    items = (
        db.query(QAItem)
        .order_by(QAItem.dataset_index)
        .all()
    )

    result = []

    for item in items:
        validation = (
            db.query(Validation)
            .filter(
                Validation.qa_item_id == item.id
            )
            .first()
        )

        result.append({
            "id": item.id,
            "dataset_index": item.dataset_index,
            "question": item.question,
            "model_answer": item.model_answer,
            "reasoning": item.reasoning,
            "dbp_context": item.dbp_context,
            "label": (
                validation.label
                if validation
                else None
            ),
            "note": (
                validation.note
                if validation
                else ""
            ),
            "annotator": (
                validation.annotator
                if validation
                else ""
            ),
            "validated_at": (
                validation.validated_at
                if validation
                else None
            )
        })

    return result


@app.post("/api/validations")
def save_validation(
    data: ValidationRequest,
    db: Session = Depends(get_db)
):
    if data.label not in [
        "Valid",
        "Invalid",
        "Not Sure"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid label"
        )

    item = (
        db.query(QAItem)
        .filter(
            QAItem.id == data.qa_item_id
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="QA item not found"
        )

    validation = (
        db.query(Validation)
        .filter(
            Validation.qa_item_id ==
            data.qa_item_id
        )
        .first()
    )

    if validation:
        validation.label = data.label
        validation.note = data.note
        validation.annotator = data.annotator
        validation.validated_at = datetime.utcnow()

    else:
        validation = Validation(
            qa_item_id=data.qa_item_id,
            label=data.label,
            note=data.note,
            annotator=data.annotator,
            validated_at=datetime.utcnow()
        )

        db.add(validation)

    db.commit()
    db.refresh(validation)

    return {
        "success": True,
        "id": validation.id,
        "qa_item_id": validation.qa_item_id,
        "label": validation.label,
        "note": validation.note,
        "annotator": validation.annotator,
        "validated_at": validation.validated_at
    }


@app.get("/api/stats")
def get_stats(
    db: Session = Depends(get_db)
):
    total = db.query(QAItem).count()

    valid = (
        db.query(Validation)
        .filter(
            Validation.label == "Valid"
        )
        .count()
    )

    invalid = (
        db.query(Validation)
        .filter(
            Validation.label == "Invalid"
        )
        .count()
    )

    not_sure = (
        db.query(Validation)
        .filter(
            Validation.label == "Not Sure"
        )
        .count()
    )

    return {
        "total": total,
        "labeled":
            valid +
            invalid +
            not_sure,
        "valid": valid,
        "invalid": invalid,
        "not_sure": not_sure
    }


# ============================================================
# EXPORT CSV
# ============================================================

@app.get("/api/export/csv")
def export_csv(
    db: Session = Depends(get_db)
):
    items = (
        db.query(QAItem)
        .order_by(QAItem.dataset_index)
        .all()
    )

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "id",
        "dataset_index",
        "question",
        "model_answer",
        "reasoning",
        "dbp_context",
        "label",
        "note",
        "annotator",
        "validated_at"
    ])

    for item in items:
        validation = (
            db.query(Validation)
            .filter(
                Validation.qa_item_id ==
                item.id
            )
            .first()
        )

        writer.writerow([
            item.id,
            item.dataset_index,
            item.question,
            item.model_answer,
            item.reasoning or "",
            item.dbp_context or "",
            (
                validation.label
                if validation
                else ""
            ),
            (
                validation.note
                if validation
                else ""
            ),
            (
                validation.annotator
                if validation
                else ""
            ),
            (
                validation.validated_at
                if validation
                else ""
            )
        ])

    output.seek(0)

    return StreamingResponse(
        iter([
            output.getvalue()
        ]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                'attachment; filename="dbp_validation_export.csv"'
        }
    )