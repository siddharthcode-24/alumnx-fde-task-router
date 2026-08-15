# Architectural & Engineering Decisions

**candidate_id**: `priya.sharma@gmail.com`

---

## 1. Gemini Rate Limits & Resiliency Strategy

### Tradeoff
The free tier of Gemini API is subject to RPM (requests per minute) rate limits and network latency spikes.

### Decision
We implemented a two-tier classification architecture:
1. **Primary LLM Engine**: Calls Gemini `gemini-2.5-flash` with structured Pydantic `response_schema`.
2. **Deterministic Rule Engine Fallback**: If Gemini hits a rate limit (HTTP 429), timeout, or invalid JSON output, the backend automatically fails over to a rule-based keyword & regex classifier.
3. **Outcome**: Zero dropped emails under high batch volumes. The system degrades gracefully to standard rule matching rather than crashing or throwing 500 errors.

---

## 2. Idempotency & Thread Reconciliation Architecture

### Tradeoff
Inbound webhooks and automated evaluation test runs (§8.1 Runs 1, 2 & 3) fire multiple batches, sometimes containing duplicate emails or follow-up replies on existing threads.

### Decision
1. **Email-Level Idempotency**: Before running LLM classification, the backend queries `EmailLogModel` for `(email_id, candidate_id)`. If present, the request is skipped immediately (`tasks_created: 0`).
2. **Thread Reconciliation**: For non-duplicate emails, the backend checks `TaskModel` for `(thread_id, candidate_id)`. If an existing task exists, the system executes an in-place `PATCH` update (updating priority, due date, deal value, description, and incrementing `update_count`) and logs `action_taken = "updated"`.
3. **Persistence Guarantee**: SQLite database persistence with `check_same_thread=False` guarantees that task states survive backend restarts or free-tier hosting cold starts.

---

## 3. Data Model for Fast Conversational Interface

### Tradeoff
Calling Gemini to re-analyze raw email text every time an ops manager asks a chat question introduces high latency, cost, and hallucination risks.

### Decision
1. **Dual Persistence Schema**:
   - `tasks`: Stores created/updated tasks matching §5 spec (`task_id`, `candidate_id`, `source_email_id`, `thread_id`, `title`, `assignee_id`, `category`, `priority`, `due_date`, `deal_value_inr`, `company_name`, `confidence`, `update_count`).
   - `email_logs`: Stores metadata for *all* ingested emails, including skipped items (`email_id`, `candidate_id`, `thread_id`, `action_taken`, `skip_reason`, `category_detected`, `raw_subject`).
2. **Outcome**: The chat backend queries pre-computed DB states instantly without calling Gemini to re-read raw email text.

---

## 4. Anti-Hallucination Grounded Chat Query Path

### Tradeoff
Naive LLM chat endpoints generate plausible-sounding numbers (e.g. inventing a count of 3 for a zero-match query).

### Decision
We engineered a strict 3-stage query translation path:
1. **Action & Query Guardrail**: Queries containing action verbs (e.g., "send an email", "delete all") are rejected immediately with a clear scope message.
2. **Structured Query Translation**: Common queries (category counts, zero-count traps like GST refunds, total deal value sums, triage tasks list, spurious rates) are computed directly via database aggregations (`SQLAlchemy` count/sum queries).
3. **LLM Synthesis**: The exact JSON ground truth dataset is injected into Gemini's prompt with strict rules: *"Answer strictly using facts in GROUND TRUTH DATA. Never invent numbers. If a query has 0 matches, state 0 explicitly."*
4. **Data Verification**: Every response returns a `supporting_data` JSON object alongside `answer` for auditability.

---

## 5. Known Flawed Case Shipped Anyway

### Tradeoff
Handling multi-intent emails (e.g., Example 11: Farhan Qureshi asking for both an enterprise trial AND co-hosting a webinar with budget TBD).

### Decision
1. **Choice**: Route the email to `u_triage` with `confidence: 0.42` and a detailed description explaining the dual asks.
2. **Alternative Considered**: Splitting the single email into two separate tasks (`tsk_1` for Aarti, `tsk_2` for Meera).
3. **Rationale**: Splitting breaks thread reconciliation when follow-up replies arrive on `th_0091` (it becomes ambiguous which task to update). Routing to `u_triage` preserves thread integrity while alerting human ops to assign ownership.
