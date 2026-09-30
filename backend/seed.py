import json
import re
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, QAItem


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dbp_user:dbp_password@localhost:5432/dbp_validation"
)

JSONL_PATH = os.getenv(
    "JSONL_PATH",
    "/app/data/dbp_1000.jsonl"
)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def parse_record(record):
    messages = record["messages"]

    user_content = next(
        message["content"]
        for message in messages
        if message["role"] == "user"
    )

    assistant_content = next(
        message["content"]
        for message in messages
        if message["role"] == "assistant"
    )

    # -------------------------
    # Extract DBP context + question
    # -------------------------

    marker = "Soalan:\n"

    if "Konteks" in user_content and marker in user_content:
        index = user_content.rfind(marker)

        dbp_context = user_content[:index].strip()
        question = user_content[index + len(marker):].strip()

    else:
        dbp_context = ""
        question = user_content.strip()

    # -------------------------
    # Extract reasoning
    # -------------------------

    match = re.search(
        r"<think>([\s\S]*?)</think>",
        assistant_content
    )

    if match:
        reasoning = match.group(1).strip()

        model_answer = re.sub(
            r"<think>[\s\S]*?</think>",
            "",
            assistant_content
        ).strip()

    else:
        reasoning = ""
        model_answer = assistant_content.strip()

    return {
        "question": question,
        "model_answer": model_answer,
        "reasoning": reasoning,
        "dbp_context": dbp_context
    }


def seed_database():

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:

        with open(JSONL_PATH, "r", encoding="utf-8") as file:

            for index, line in enumerate(file, start=1):

                line = line.strip()

                if not line:
                    continue

                record = json.loads(line)

                parsed = parse_record(record)

                existing = (
                    db.query(QAItem)
                    .filter(QAItem.dataset_index == index)
                    .first()
                )

                if existing:
                    continue

                item = QAItem(
                    question=parsed["question"],
                    model_answer=parsed["model_answer"],
                    reasoning=parsed["reasoning"],
                    dbp_context=parsed["dbp_context"],
                    dataset_name="dbp_1000.jsonl",
                    dataset_index=index
                )

                db.add(item)

        db.commit()

        count = db.query(QAItem).count()

        print(f"Database seeded successfully.")
        print(f"Total QA items: {count}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()