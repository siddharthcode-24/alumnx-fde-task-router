from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

ALLOWED_ASSIGNEES = [
    "u_aarti",
    "u_rohit",
    "u_meera",
    "u_karan",
    "u_divya",
    "u_triage",
]

ALLOWED_CATEGORIES = [
    "enterprise_rfp",
    "smb_enquiry",
    "marketing",
    "alliances",
    "finance",
    "triage",
]

ALLOWED_PRIORITIES = ["high", "medium", "low"]

TEAM_ROSTER = {
    "team": [
        {
            "user_id": "u_aarti",
            "name": "Aarti Menon",
            "department": "Sales — Enterprise",
            "scope": "RFPs, RFIs, tenders, and inbound deals above ₹10,00,000",
        },
        {
            "user_id": "u_rohit",
            "name": "Rohit Sharma",
            "department": "Sales — SMB",
            "scope": "Product enquiries, demo requests, deals at or below ₹10,00,000",
        },
        {
            "user_id": "u_meera",
            "name": "Meera Iyer",
            "department": "Marketing",
            "scope": "Webinars, event and conference sponsorships, content collaborations, PR and media",
        },
        {
            "user_id": "u_karan",
            "name": "Karan Doshi",
            "department": "Alliances",
            "scope": "Reseller, channel partner, and technology integration proposals",
        },
        {
            "user_id": "u_divya",
            "name": "Divya Rao",
            "department": "Finance",
            "scope": "Invoices, purchase orders, payment reminders, GST and vendor billing",
        },
        {
            "user_id": "u_triage",
            "name": "Triage Queue",
            "department": "Operations",
            "scope": "Ambiguous items requiring human review",
        },
    ]
}


class CreateTaskRequest(BaseModel):
    candidate_id: str
    source_email_id: str
    thread_id: str
    title: str
    description: Optional[str] = None
    assignee_id: str
    category: str
    priority: str
    due_date: Optional[str] = None
    deal_value_inr: Optional[int] = None
    company_name: Optional[str] = None
    confidence: float


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    deal_value_inr: Optional[int] = None
    company_name: Optional[str] = None
    confidence: Optional[float] = None


class IngestEmailItem(BaseModel):
    email_id: str
    thread_id: str
    message_index: Optional[int] = 0
    from_name: Optional[str] = None
    from_email: str
    to: Optional[str] = None
    cc: Optional[List[str]] = []
    subject: str
    body: str
    received_at: str
    attachments: Optional[List[str]] = []
    is_reply: Optional[bool] = False


class IngestRequest(BaseModel):
    candidate_id: Optional[str] = "priya.sharma@gmail.com"
    emails: List[IngestEmailItem]


class ChatRequest(BaseModel):
    candidate_id: Optional[str] = "priya.sharma@gmail.com"
    query: str


class LLMDecision(BaseModel):
    is_noise: bool
    noise_reason: Optional[str] = None
    title: str
    description: str
    assignee_id: str
    category: str
    priority: str
    due_date: Optional[str] = None
    deal_value_inr: Optional[int] = None
    company_name: Optional[str] = None
    confidence: float


class ChatResponse(BaseModel):
    answer: str
    supporting_data: Dict[str, Any]