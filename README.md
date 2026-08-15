# Sales Inbox → Task Router

**candidate_id**: `priya.sharma@gmail.com`  
**Deployed Backend URL**: `https://sales-router-backend.onrender.com`  
**Deployed Frontend URL**: `https://sales-router-frontend.vercel.app`  
**GitHub Repository**: `https://github.com/siddharthcode-24/alumnx-fde-task-router.git`

---

## 📌 Overview

An intelligent Sales Inbox Task Router built for the **ALUMNX AI LABS — FDE Intern Hiring Challenge**. It automatically ingests raw B2B email threads, filters out noise (newsletters, out-of-office auto-replies, vendor spam), applies department routing rules with PSU/Govt tender overrides, handles thread reconciliation, and provides an ops conversational interface grounded on persistent database records.

---

## ⚡ Quickstart (≤ 3 Commands)

### 1. Setup Backend
```bash
cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && cp .env.example .env
```

### 2. Run Backend
```bash
cd backend && python -m uvicorn main:app --reload --port 8000
```

### 3. Run Frontend (in new terminal)
```bash
cd frontend && npm install && npm run dev
```

---

## 🛠️ Architecture & Tech Stack

- **Backend**: FastAPI (Python 3.11), SQLAlchemy, SQLite (with Postgres/Supabase support)
- **AI/LLM**: Google Gemini API (`google-genai` SDK, `gemini-2.5-flash` model) with structured JSON outputs and fallback rule engine
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons
- **Persistence**: Database-level tracking of tasks and email ingestion logs ensuring 100% idempotency and thread reconciliation

---

## 🧪 Automated Testing

Run the full test suite verifying Task API CRUD, enum validation, worked examples, idempotency, thread reconciliation, and grounded chat:

```bash
cd backend && python test_system.py
```

---

## 📄 Submission Documents

- [`EVALS.md`](file:///d:/Desktop/Alumnx%20Labs/EVALS.md): 50 hand-labelled evaluation dataset, precision/recall metrics, and failure cases analysis.
- [`DECISIONS.md`](file:///d:/Desktop/Alumnx%20Labs/DECISIONS.md): Detailed breakdown of 5 core engineering tradeoffs (Gemini rate limits, idempotency, data model, anti-hallucination chat grounding, and triage routing decision).
