from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class FabricAnalysis(Base):
    __tablename__ = "fabric_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[str] = mapped_column(String(255))
    predicted_fabric: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    washing_temperature: Mapped[str] = mapped_column(String(80))
    washing_mode: Mapped[str] = mapped_column(String(200))
    drying_method: Mapped[str] = mapped_column(String(200))
    ironing_temperature: Mapped[str] = mapped_column(String(200))
    special_care: Mapped[str] = mapped_column(Text)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    probabilities: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    note_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)  # Fernet-encrypted user note
    model_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)  # Synthetic Demo Data flag
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user = relationship("User", back_populates="analyses")
    washing_history = relationship("WashingHistory", back_populates="analysis", cascade="all, delete-orphan")


class FabricKnowledge(Base):
    """Relational copy of the fabric-care knowledge base (source: data/knowledge/care_rules.json)."""

    __tablename__ = "fabric_knowledge"

    id: Mapped[int] = mapped_column(primary_key=True)
    fabric_type: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    property: Mapped[str] = mapped_column(Text)
    washing_method: Mapped[str] = mapped_column(String(200))
    temperature: Mapped[str] = mapped_column(String(80))
    drying_method: Mapped[str] = mapped_column(String(200))
    ironing_method: Mapped[str] = mapped_column(String(200))
    special_care: Mapped[str] = mapped_column(Text)
    detergent: Mapped[str | None] = mapped_column(String(250), nullable=True)
    bleaching: Mapped[str | None] = mapped_column(String(250), nullable=True)


class WashingHistory(Base):
    __tablename__ = "washing_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    fabric_analysis_id: Mapped[int] = mapped_column(ForeignKey("fabric_analyses.id", ondelete="CASCADE"), index=True)
    selected_washing_mode: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user = relationship("User", back_populates="washing_history")
    analysis = relationship("FabricAnalysis", back_populates="washing_history")
