from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class ClientStatus(str, enum.Enum):
    NEW = "new"
    PLANNED_CALL = "planned_call"
    NO_ANSWER = "no_answer"
    THINKING = "thinking"
    AGREED = "agreed"
    DECLINED = "declined"


class InterestLevel(str, enum.Enum):
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


class CompanySource(str, enum.Enum):
    FOUND = "found"
    RECOMMENDATION = "recommendation"
    INBOUND = "inbound"


class CompanyStatus(str, enum.Enum):
    NOT_CALLED = "not_called"
    RESEARCH = "research"
    NO_ANSWER = "no_answer"
    NEGOTIATION = "negotiation"
    CLIENT = "client"
    DECLINED = "declined"


class PriorityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InteractionResult(str, enum.Enum):
    CALL = "call"
    MESSAGE = "message"
    MEETING = "meeting"


class SuggestionType(str, enum.Enum):
    CITY = "city"
    NICHE = "niche"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    source: Mapped[str] = mapped_column(String(50), default="другое")
    status: Mapped[ClientStatus] = mapped_column(Enum(ClientStatus), default=ClientStatus.NEW)
    interest: Mapped[InterestLevel] = mapped_column(Enum(InterestLevel), default=InterestLevel.COLD)
    next_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    company: Mapped["Company"] = relationship("Company", back_populates="clients")
    interactions: Mapped[list["Interaction"]] = relationship(
        "Interaction", back_populates="client", cascade="all, delete-orphan"
    )


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    niche: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    site: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[CompanySource] = mapped_column(Enum(CompanySource), default=CompanySource.FOUND)
    status: Mapped[CompanyStatus] = mapped_column(Enum(CompanyStatus), default=CompanyStatus.NOT_CALLED)
    priority: Mapped[PriorityLevel] = mapped_column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM)
    contact_person: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    clients: Mapped[list[Client]] = relationship("Client", back_populates="company", cascade="all, delete")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    result: Mapped[InteractionResult] = mapped_column(Enum(InteractionResult))
    status_after: Mapped[ClientStatus] = mapped_column(Enum(ClientStatus))
    comment: Mapped[str | None] = mapped_column(Text)

    client: Mapped[Client] = relationship("Client", back_populates="interactions")


class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = (UniqueConstraint("type", "value", name="uq_suggestion_type_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[SuggestionType] = mapped_column(Enum(SuggestionType), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
