from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    DateTime,
    ForeignKey
)

from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class QAItem(Base):
    __tablename__ = "qa_items"

    id = Column(Integer, primary_key=True)

    question = Column(Text, nullable=False)

    model_answer = Column(Text, nullable=False)

    reasoning = Column(Text)

    dbp_context = Column(Text)

    dataset_name = Column(String(255), nullable=False)

    dataset_index = Column(
        Integer,
        nullable=False,
        unique=True
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


class Validation(Base):
    __tablename__ = "validations"

    id = Column(Integer, primary_key=True)

    qa_item_id = Column(
        Integer,
        ForeignKey(
            "qa_items.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        unique=True
    )

    label = Column(
        String(20),
        nullable=False
    )

    note = Column(Text)

    annotator = Column(String(255))

    validated_at = Column(
        DateTime,
        server_default=func.now()
    )