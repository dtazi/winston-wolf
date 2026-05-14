"""Dataclasses for Winston Wolf core entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Customer:
    id: str
    name: str
    pitch_path: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass(slots=True)
class Campaign:
    id: str
    customer_id: str
    name: str
    brief_path: Optional[str] = None
    status: str = "draft"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(slots=True)
class SourceChannel:
    id: str
    name: str
    type: str
    access_tier: str
    description: Optional[str] = None
    url: Optional[str] = None


@dataclass(slots=True)
class Lead:
    id: str
    customer_id: str
    campaign_id: str
    niche_id: str
    source_channel_id: str
    source_record_id: Optional[str] = None
    access_difficulty: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    company_country: Optional[str] = None
    company_region: Optional[str] = None
    company_size_band: Optional[str] = None
    person_first_name: Optional[str] = None
    person_last_name: Optional[str] = None
    person_title: Optional[str] = None
    person_email: Optional[str] = None
    email_confidence: Optional[int] = None
    email_method: Optional[str] = None
    person_phone: Optional[str] = None
    person_linkedin: Optional[str] = None
    status: str = "cold"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass(slots=True)
class Send:
    id: str
    lead_id: str
    subject: str
    body_text: str
    sent_at: datetime
    microsoft_message_id: Optional[str] = None
    pixel_token: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass(slots=True)
class Event:
    id: Optional[int]
    lead_id: str
    event_type: str
    timestamp: datetime
    send_id: Optional[str] = None
    payload: Optional[str] = None
    recorded_at: Optional[datetime] = None
