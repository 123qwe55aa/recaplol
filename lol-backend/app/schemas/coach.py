from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class CoachDataWindow(BaseModel):
    match_count: int = 0
    days: Optional[int] = None
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None
    recent_match_ids: List[str] = Field(default_factory=list)
    fingerprint: Optional[str] = None
    primary_role: Optional[str] = None
    primary_champions: List[dict] = Field(default_factory=list)


class CoachPriority(BaseModel):
    area: Optional[str] = None
    category: Optional[str] = None
    title: str
    severity: str = "medium"
    evidence: List[str] = Field(default_factory=list)
    problem: Optional[str] = None
    impact: Optional[str] = None
    recommendation: Optional[str] = None
    rationale: Optional[str] = None
    actions: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    opgg_reference: Optional[str] = None


class CoachReportPayload(BaseModel):
    summary: str
    data_window: CoachDataWindow
    priorities: List[CoachPriority] = Field(default_factory=list)
    confidence: float | str = "medium"
    notes: Optional[str] = None
    generated_at: Optional[str] = None
    follow_up_questions: List[str] = Field(default_factory=list)


class CoachReportResponse(BaseModel):
    id: Optional[int] = None
    puuid: Optional[str] = None
    has_report: bool = True
    report: Optional[CoachReportPayload] = None
    data_fingerprint: Optional[str] = None
    model: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    stale: bool = False
    generated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CoachGenerateRequest(BaseModel):
    force: bool = False
    match_limit: int = 20


class CoachChatRequest(BaseModel):
    question: str
    messages: List[dict] = Field(default_factory=list)


class CoachChatResponse(BaseModel):
    answer: str
    model: Optional[str] = None
    report_id: Optional[int] = None
    cited_priorities: List[str] = Field(default_factory=list)
    used_evidence: List[str] = Field(default_factory=list)
    suggested_next_question: Optional[str] = None
