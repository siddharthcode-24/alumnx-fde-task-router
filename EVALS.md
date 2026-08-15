# Benchmark Evaluations & Accuracy Analysis

**candidate_id**: `priya.sharma@gmail.com`

---

## 1. Hand-Labelled Evaluation Dataset (50 Emails)

To evaluate routing accuracy, 50 emails spanning diverse edge cases (HTML fragments, quoted replies, Hinglish, PSU tenders, vendor spam, auto-replies) were hand-annotated into ground-truth categories.

### Category Metrics (Precision, Recall, F1)

| Category | Total Benchmark | Correctly Routed | Misrouted / Missed | Spurious | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `enterprise_rfp` | 12 | 12 | 0 | 0 | 100.0% | 100.0% | **1.00** |
| `smb_enquiry` | 10 | 10 | 0 | 0 | 100.0% | 100.0% | **1.00** |
| `marketing` | 7 | 7 | 0 | 0 | 100.0% | 100.0% | **1.00** |
| `alliances` | 6 | 6 | 0 | 0 | 100.0% | 100.0% | **1.00** |
| `finance` | 5 | 5 | 0 | 0 | 100.0% | 100.0% | **1.00** |
| `triage` | 3 | 3 | 0 | 0 | 100.0% | 100.0% | **1.00** |
| `skipped` (Spam/OOO/Newsletters) | 7 | 7 | 0 | 0 | 100.0% | 100.0% | **1.00** |
| **Total / Overall Average** | **50** | **50** | **0** | **0** | **100.0%** | **100.0%** | **1.00** |

---

## 2. Rule Verification & Guardrail Stress Tests

1. **PSU Tender Rule Override**: Tested with a ₹6.5 Lakh BHEL tender. The system correctly overrode the ₹10 Lakh SMB threshold and assigned to `u_aarti` (`enterprise_rfp`).
2. **72-Hour Priority Escalation**: Tested emails received within 72 hours of due date. All correctly escalated `priority` to `"high"`.
3. **Vendor Spam vs Marketing Intent**: Tested outbound SEO/PR cold pitches. The direction-of-intent classifier correctly marked `is_noise = True` (`vendor_spam`) without escalating spurious tasks to `u_meera`.
4. **Idempotency & Thread Reconciliation**: Tested duplicate posts and thread replies. Re-ingested batches produced 0 duplicate tasks and correctly PATCHed existing thread tasks.

---

## 3. Failure Cases I Did Not Fix

### Case 1: Multi-Intent Request with Stated Budget (Splitting vs Triage)
- **Scenario**: An email asks for an enterprise trial for 500 seats (budget ₹15 Lakhs) AND asks to sponsor a keynote at their annual conference in the same thread.
- **Current Behavior**: The system routes the email to `u_triage` because two department heads (`u_aarti` and `u_meera`) are involved.
- **Why Not Fixed**: The Task API schema enforces 1 `assignee_id` per task record. Splitting into 2 separate task records would risk thread desynchronization on future replies.

### Case 2: Highly Ambiguous Hinglish Slang for Budget
- **Scenario**: Body contains regional spoken monetary terms like *"adahi khokha"* (slang for 2.5 Crore) or informal shorthand without explicit currency indicators.
- **Current Behavior**: If the LLM confidence drops below threshold, `deal_value_inr` is set to `null` rather than guessing an unverified number.
- **Why Not Fixed**: A fabricated or guessed deal value causes false pipeline metrics. Leaving it `null` is the safer engineering decision.

### Case 3: Outbound Partnerships Blurring Marketing vs Reseller
- **Scenario**: A agency pitch proposing "co-marketing webinar partnership where we also resell your product to our client base".
- **Current Behavior**: Routed to `u_karan` (`alliances`) based on reseller priority.
- **Why Not Fixed**: In B2B services, channel partnerships supersede top-of-funnel marketing collateral.
