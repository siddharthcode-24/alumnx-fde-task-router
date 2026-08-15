import os
import json
from fastapi.testclient import TestClient
from main import app, init_db
from models import Base, engine, TaskModel, EmailLogModel

Base.metadata.drop_all(bind=engine)
init_db()
client = TestClient(app)

CANDIDATE_ID = "priya.sharma@gmail.com"

def test_users_endpoint():
    print("Testing /users endpoint...")
    res = client.get("/users")
    assert res.status_code == 200
    data = res.json()
    assert "team" in data
    assert len(data["team"]) == 6
    print("  [OK] /users passed!")

def test_tasks_crud_and_validation():
    print("Testing /tasks CRUD and enum validation...")
    # 1. Test bad enum validation (assignee_id)
    bad_payload = {
        "candidate_id": CANDIDATE_ID,
        "source_email_id": "em_test_bad_1",
        "thread_id": "th_test_bad_1",
        "title": "Test Bad Enum",
        "assignee_id": "Aarti", # Should be u_aarti
        "category": "enterprise_rfp",
        "priority": "high",
        "confidence": 0.9
    }
    res = client.post("/tasks", json=bad_payload)
    assert res.status_code == 400
    err = res.json()["detail"]
    assert err["error"] == "invalid_enum_value"
    assert err["field"] == "assignee_id"
    assert err["received"] == "Aarti"
    assert "u_aarti" in err["allowed"]

    # 2. Test valid task creation
    valid_payload = {
        "candidate_id": CANDIDATE_ID,
        "source_email_id": "em_test_001",
        "thread_id": "th_test_001",
        "title": "RFP - Enterprise DMS for Meridian Steel",
        "description": "Meridian Steel RFP for 1200 users",
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "medium",
        "due_date": "2026-08-12",
        "deal_value_inr": 2500000,
        "company_name": "Meridian Steel",
        "confidence": 0.91
    }
    res = client.post("/tasks", json=valid_payload)
    assert res.status_code == 201
    created = res.json()
    assert "task_id" in created
    assert created["candidate_id"] == CANDIDATE_ID
    task_id = created["task_id"]

    # 3. Test list tasks
    res = client.get(f"/tasks?candidate_id={CANDIDATE_ID}")
    assert res.status_code == 200
    tasks = res.json()
    assert any(t["task_id"] == task_id for t in tasks)

    # 4. Test patch task
    patch_payload = {
        "priority": "high",
        "deal_value_inr": 3200000
    }
    res = client.patch(f"/tasks/{task_id}", json=patch_payload)
    assert res.status_code == 200
    updated = res.json()
    assert updated["priority"] == "high"
    assert updated["deal_value_inr"] == 3200000

    # 5. Test delete task
    res = client.delete(f"/tasks/{task_id}")
    assert res.status_code == 200
    print("  [OK] /tasks CRUD & validation passed!")

def test_ingest_worked_examples():
    print("Testing /ingest worked examples & routing rules...")
    examples = [
        # Ex 1: Clean enterprise RFP
        {
            "email_id": "em_ex1",
            "thread_id": "th_ex1",
            "from_name": "Suresh Kulkarni",
            "from_email": "s.kulkarni@meridiansteel.co.in",
            "subject": "RFP - Enterprise Document Management System",
            "body": "Meridian Steel invites proposals for an enterprise DMS. Indicative budget is Rs. 25 lakhs. Proposals must reach us by 12th August 2026.",
            "received_at": "2026-08-01T09:14:22+05:30",
            "is_reply": False
        },
        # Ex 2: SMB demo request
        {
            "email_id": "em_ex2",
            "thread_id": "th_ex2",
            "from_name": "Ankit Bose",
            "from_email": "ankit@railyardlogistics.in",
            "subject": "Quick demo request",
            "body": "Hi, we're a 30-person logistics startup in Pune... can we get a demo sometime next week? Nothing urgent.",
            "received_at": "2026-08-01T11:02:00+05:30",
            "is_reply": False
        },
        # Ex 3: PSU tender below threshold (Aarti)
        {
            "email_id": "em_ex3",
            "thread_id": "th_ex3",
            "from_name": "Procurement BHEL",
            "from_email": "tender@bhel.in",
            "subject": "Tender Notice No. BHEL/PROC/2026/0847",
            "body": "Bharat Heavy Electricals Limited invites bids for supply of analytics software licences. Estimated value: Rs. 6,50,000. Last date: 03-08-2026.",
            "received_at": "2026-08-01T14:20:00+05:30",
            "is_reply": False
        },
        # Ex 4: Marketing sponsorship
        {
            "email_id": "em_ex4",
            "thread_id": "th_ex4",
            "from_name": "Nandita Reddy",
            "from_email": "nandita@saassummit.in",
            "subject": "Sponsorship confirmation needed",
            "body": "We're finalising sponsors for India SaaS Summit. Gold tier is ₹4,00,000. Need confirmation by tomorrow EOD.",
            "received_at": "2026-08-02T16:45:00+05:30",
            "is_reply": False
        },
        # Ex 5: Invoice (Finance)
        {
            "email_id": "em_ex5",
            "thread_id": "th_ex5",
            "from_name": "Vantage Billing",
            "from_email": "accounts@vantagecloud.com",
            "subject": "Invoice INV-2026-0331",
            "body": "Please find attached invoice INV-2026-0331 for Rs. 1,18,000 against PO-88214. Kindly process — 12 days overdue.",
            "received_at": "2026-08-03T10:00:00+05:30",
            "is_reply": False
        },
        # Ex 7: Out of office (NO TASK)
        {
            "email_id": "em_ex7",
            "thread_id": "th_ex7",
            "from_name": "Raghav",
            "from_email": "raghav@northbridge.in",
            "subject": "Out of Office",
            "body": "I am out of office until 14th August with limited access to email.",
            "received_at": "2026-08-03T08:00:00+05:30",
            "is_reply": False
        },
        # Ex 8: Vendor spam (NO TASK)
        {
            "email_id": "em_ex8",
            "thread_id": "th_ex8",
            "from_name": "SEO Agency",
            "from_email": "pitch@growthseo.io",
            "subject": "3x your organic traffic",
            "body": "Hi, I noticed your website isn't ranking on page 1. We do PR outreach and content marketing. Free audit attached.",
            "received_at": "2026-08-04T12:00:00+05:30",
            "is_reply": False
        }
    ]

    res = client.post("/ingest", json={"candidate_id": CANDIDATE_ID, "emails": examples})
    assert res.status_code == 200
    summary = res.json()
    assert summary["processed"] == len(examples)
    assert summary["skipped"] == 2 # Ex 7 and Ex 8 skipped
    assert summary["tasks_created"] == 5 # Ex 1, 2, 3, 4, 5 created
    print("  [OK] /ingest worked examples passed!")

def test_idempotency_and_thread_reconciliation():
    print("Testing idempotency & thread reconciliation...")
    # Re-posting same batch (Run 2 - Idempotency)
    batch = [{
        "email_id": "em_ex1",
        "thread_id": "th_ex1",
        "from_name": "Suresh Kulkarni",
        "from_email": "s.kulkarni@meridiansteel.co.in",
        "subject": "RFP - Enterprise Document Management System",
        "body": "Duplicate email post",
        "received_at": "2026-08-01T09:14:22+05:30",
        "is_reply": False
    }]
    res = client.post("/ingest", json={"candidate_id": CANDIDATE_ID, "emails": batch})
    assert res.status_code == 200
    summary = res.json()
    assert summary["tasks_created"] == 0 # Idempotent - no duplicate tasks!

    # Posting thread reply (Run 3 - Thread reconciliation)
    reply_batch = [{
        "email_id": "em_ex1_reply",
        "thread_id": "th_ex1", # Same thread as Ex 1
        "from_name": "Suresh Kulkarni",
        "from_email": "s.kulkarni@meridiansteel.co.in",
        "subject": "RE: RFP - Enterprise Document Management System",
        "body": "Correction: increased budget of Rs. 32 lakhs, deadline 11th August.",
        "received_at": "2026-08-09T10:00:00+05:30",
        "is_reply": True
    }]
    res = client.post("/ingest", json={"candidate_id": CANDIDATE_ID, "emails": reply_batch})
    assert res.status_code == 200
    summary = res.json()
    assert summary["tasks_created"] == 0
    assert summary["tasks_updated"] == 1 # Updated existing task!
    print("  [OK] Idempotency & Thread Reconciliation passed!")

def test_chat_grounding():
    print("Testing chat grounding & action verb rejections...")
    # 1. Action verb rejection
    res = client.post("/api/chat", json={"candidate_id": CANDIDATE_ID, "query": "Send Aarti an email about Meridian Steel"})
    assert res.status_code == 200
    answer = res.json()
    assert "cannot take external actions" in answer["answer"]

    # 2. Zero-count trap (GST refund)
    res = client.post("/api/chat", json={"candidate_id": CANDIDATE_ID, "query": "How many emails were about GST refunds?"})
    assert res.status_code == 200
    answer = res.json()
    assert answer["supporting_data"]["gst_refund_count"] == 0

    # 3. RFP total deal value query
    res = client.post("/api/chat", json={"candidate_id": CANDIDATE_ID, "query": "What's the total deal value of open RFPs?"})
    assert res.status_code == 200
    answer = res.json()
    assert "total_deal_value_inr" in answer["supporting_data"]
    print("  [OK] Chat grounding passed!")

if __name__ == "__main__":
    test_users_endpoint()
    test_tasks_crud_and_validation()
    test_ingest_worked_examples()
    test_idempotency_and_thread_reconciliation()
    test_chat_grounding()
    print("\nALL TESTS PASSED SUCCESSFULLY!")
