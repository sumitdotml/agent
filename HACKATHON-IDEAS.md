# Hackathon Agent Ideas (Critiqued + Curated)

This is a judge-style critique of the original list, plus a short final set I believe are actually strong *agent* demos under our constraints (2 hours, 2–3 tools, visible loop, real-world framing).

## Non-Negotiable Agent Criteria

1. Clear single goal (review X → produce Y).
2. 2–3 deterministic, mockable tools (local DB/files; no fragile web APIs).
3. A real loop (observe → decide → act → observe → repeat) with an outcome-based stop condition.
4. 30-second narration is obvious.
5. Demo is legible: judge can see why each tool call happened.

## Final Shortlist (Keep)

### 0) Outbound Email Guard (Compliance Agent)
**Goal:** Review a drafted outbound email for compliance issues; rewrite until it passes.

**Tools (2–3):**
- `check_compliance(email_text)` → `{"issues": [...], "pass": bool}` (mockable: regex/keyword rules)
- `get_policy(category)` → returns canned policy text (pii/marketing/legal/confidentiality)
- `redact_pii(text)` → deterministic PII redaction

**Loop:** check → fetch relevant policy → rewrite → redact → re-check → repeat until `pass=true`.

---

### 1) Incident Triage + Status Update Agent (Best “agentic feel”)
**Goal:** Given an incident report + symptoms, decide the next diagnostic check, run it, repeat until confident, then output a status update and next steps.

**Why it’s strong (judge view):**
- Very obvious loop: “run check → learn → choose next check”.
- Easy to stream as a timeline (think/tool/result).
- Grounding is natural: final answer cites check outputs + runbook text.

**Tools (2–3):**
- `run_check(check_id)` → deterministic (mock) metrics/log snippets.
- `search_runbook(query)` → relevant runbook sections from local markdown.
- `write_update(channel, message)` → writes a Slack-style update to a file.

**Termination:** stop when confidence is high or max checks reached.

---

### 2) Lost & Found Matchmaker Agent (High human-impact, low build time)
**Goal:** Match a “lost item” report to likely “found item” posts and output a message that asks exactly one high-signal verification question.

**Why it’s strong (judge view):**
- Feels real and non-corporate.
- Loop is natural: broaden/narrow search, rerank, re-check ambiguity.
- Deterministic grounding: “I matched on location/time/color/brand”.

**Tools (2–3):**
- `search_posts(filters)` → queries a local SQLite/JSON dataset of lost/found posts.
- `score_match(lost_post, candidate)` → deterministic scoring (weights + thresholds).
- `write_message_draft(match_id, text)` → writes a message draft file.

**Termination:** stop when top match clears confidence threshold, else output top 3 + verification questions.

---

### 3) Waste-Sorting Coach Agent (Local rules, instant credibility)
**Goal:** For a list of household items, decide trash/recycle/compost/drop-off and cite the exact rule used (city-specific).

**Why it’s strong (judge view):**
- Grounded by rules text (no vibes).
- Repeats per-item and can self-correct when rules conflict.
- Human-impact framing (waste reduction) without needing APIs.

**Tools (2–3):**
- `lookup_rules(item, locale)` → rule snippets from local markdown.
- `validate_decision(item, bin)` → deterministic check against parsed rules.
- `write_sorting_list(items_with_bins)` → writes a printable checklist.

**Termination:** stop when all items validated; mark items “needs clarification” when rules conflict.

---

### 4) Expense/Receipt Sanity Checker Agent (Tiny mock data, real loop)
**Goal:** Review an expense list, detect violations/missing receipts, and output a “fix list” (what to change or justify), not just pass/fail.

**Why it’s strong (judge view):**
- The loop is clear: validate → find missing info → re-validate.
- Deterministic policies make it defensible.

**Tools (2–3):**
- `check_policy(line_item)` → deterministic policy checks (caps, categories).
- `lookup_receipt(receipt_id)` → reads a local receipt stub store.
- `write_fix_list(report)` → writes a structured report (JSON/MD).

**Termination:** stop when no violations remain or when remaining issues require human input.

---

### 5) Security Alert Triage Agent (Keep only if judges like “ops”)
**Goal:** Triage an alert using local “threat intel” + asset criticality + playbook, then recommend contain/escalate/ignore with justification.

**Why it’s strong (judge view):**
- Naturally agentic: enrichment changes the decision.
- Strong observability: “indicator → intel → playbook → action”.

**Tools (2–3):**
- `enrich_indicator(ioc)` → local JSON mapping (reputation, known malware family).
- `get_asset_context(host)` → SQLite lookup (owner, criticality).
- `lookup_playbook(alert_type)` → local markdown sections.

**Termination:** stop when recommended action is supported by intel + playbook.

---

## Dropped (And Why)

- Job Application Screener: judge will poke bias/fairness; also becomes subjective fast.
- Incident Post-Mortem Writer: tends to become one-shot summarization; keep the “triage” version instead.
- Data Pipeline Failure Analyzer: overlaps with incident triage; log parsing can derail a 2-hour build.
- Interview Debrief Synthesizer: mostly summarization; loop is weak unless we add real conflict resolution.
- Changelog to Release Notes: one-shot polishing; not agentic.
- Meeting Notes to Action Items: common and often turns into extraction (pipeline).
- Contract Clause Risk Assessor: hard to do credibly without lots of legal scaffolding.
- PR Risk Assessor: deceptively deep (diff parsing, coverage) and easy to overpromise.
- Vendor Risk Evaluator: doc parsing + scoring is fragile; demo risk.
- SLA Breach Predictor: basically a calculation, not an agent.
- Knowledge Base Gap Finder: clustering/topic modeling is more work than it looks in 2 hours.
- Config Drift Detector: fine, but less “wow” unless we already have a config corpus.

---

## Additional Non-Corporate Ideas (Also Strong)

### A) Food Rescue Matchmaker Agent
**Goal:** Match surplus food offers to nearby shelters with constraints (pickup window, refrigeration, allergies) and output a pickup plan.

**Tools (2–3):**
- `search_offers_and_needs(filters)` (SQLite)
- `score_feasibility(offer, need)` (deterministic)
- `write_pickup_plan(plan)` (MD/JSON)

**Loop:** propose match → detect constraint violations → adjust filters → repeat.

---

### B) Apartment Maintenance Triage Agent
**Goal:** Turn a tenant report into a safe triage decision (emergency vs routine), troubleshooting steps, and a ready-to-send message.

**Tools (2–3):**
- `lookup_issue_playbook(issue_type)` (markdown)
- `risk_check(symptoms)` (deterministic red flags: gas smell, sparking, flooding)
- `write_ticket_and_message(payload)` (JSON/MD)

**Loop:** classify → run risk check → fetch playbook → revise decision → finalize.

---

## Ultimate Recommendation (Pick One)

- Build **Incident Triage + Status Update** for maximum “agentic feel” on stage.
- Build **Lost & Found Matchmaker** for maximum human-impact with minimal complexity.
