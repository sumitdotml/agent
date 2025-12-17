# Outbound Email Guard Agent - Implementation TODO

## Overview

**Agent Name:** Outbound Email Guard (Compliance Agent)  
**Goal:** Review a drafted outbound email for compliance issues; rewrite until it passes.  
**Loop:** check → fetch relevant policy → rewrite → redact → re-check → repeat until `pass=true`

---

## Phase 1: Define Tools (Core Infrastructure)

### Tool 1: `check_compliance(email_text)` ✅
- [x] Create function signature with type hints
- [x] Implement detection rules:
  - [x] PII detection (names, emails, phone numbers, SSN patterns, credit cards)
  - [x] Marketing compliance (missing unsubscribe, promotional language without disclaimer)
  - [x] Legal language issues (unapproved guarantees, liability statements)
  - [x] Confidentiality violations (internal-only markers, sensitive keywords, project codenames)
- [x] Return structure: `{"issues": [{"type": str, "description": str, "severity": str}], "pass": bool}`
- [ ] Add unit tests for each detection rule (optional enhancement)

### Tool 2: `get_policy(category)` ✅
- [x] Define supported categories: `pii`, `marketing`, `legal`, `confidentiality`
- [x] Create policy documents (mock/canned text):
  - [x] `pii.md` - Rules about personal information
  - [x] `marketing.md` - Rules about promotional content
  - [x] `legal.md` - Rules about legal language and disclaimers
  - [x] `confidentiality.md` - Rules about sensitive information
- [x] Return relevant policy text for given category
- [x] Handle unknown category gracefully

### Tool 3: `redact_pii(text)` ✅
- [x] Implement PII pattern detection:
  - [x] Email addresses → `[REDACTED_EMAIL]`
  - [x] Phone numbers → `[REDACTED_PHONE]`
  - [x] SSN patterns → `[REDACTED_SSN]`
  - [x] Credit cards → `[REDACTED_CC_****XXXX]`
  - [x] Names (via title patterns) → `[REDACTED_NAME]`
- [x] Return redacted text
- [x] Preserve email structure and readability

### Tool 4: `submit_email(email_text)` (Skipped)
- [ ] Not implemented (agent finalizes with "final" action type instead)

---

## Phase 2: Update Agent Core ✅

### State Definition
- [x] Update `AgentState` TypedDict:
  - [x] `email_draft: str` - Current version of the email
  - [x] `iteration: int` - Track rewrite iterations (safety limit)
  - [x] `history: List` - Track tool calls and results

### System Prompt
- [x] Update system prompt for email compliance context
- [x] Define available tools with clear descriptions
- [x] Add 3 action types: tool, rewrite, final
- [x] Set max iterations (5 max)

### Tool Registry
- [x] Replace calculator with compliance tools
- [x] Update `TOOLS` dict with new functions
- [x] Ensure proper error handling for each tool

### Additional: Rewrite Node
- [x] Added `rewrite` action type for iterative email fixing
- [x] Agent now proposes rewrites that update the email_draft
- [x] Loop: check → policy → rewrite → re-check until pass

---

## Phase 3: Create Test Scenarios ✅

### Test Email 1: PII Violation ✅
- [x] Create email with exposed customer names, emails, phone numbers (`test_emails/pii_violation.txt`)
- [x] ✅ Agent detects PII, fetches pii policy, redacts/rewrites

### Test Email 2: Marketing Compliance ✅
- [x] Create promotional email missing unsubscribe link (`test_emails/marketing_issue.txt`)
- [x] ✅ Agent detects issue, fetches marketing policy, adds unsubscribe

### Test Email 3: Confidentiality Breach ✅
- [x] Create email with "INTERNAL ONLY" content and project codenames (`test_emails/confidentiality_breach.txt`)
- [x] ✅ Agent detects confidentiality issues, removes markers and internal references

### Test Email 4: Multiple Issues ✅
- [x] Create email with PII + marketing + confidentiality issues (`test_emails/multiple_issues.txt`)
- [x] ✅ Agent handles all 9 issues across iterations, produces clean email

### Test Email 5: Clean Email ✅
- [x] Create compliant email (`test_emails/clean_email.txt`)
- [x] ✅ Agent checks, finds no issues, finalizes in 2 iterations

---

## Phase 4: Polish & Demo Prep

### Streaming Output ✅
- [x] Update `render_update()` for email-specific events
- [x] Show compliance check results clearly (PASS/FAIL, issue list)
- [x] Display rewrite iterations with preview
- [x] Show final approved email prominently

### Demo Script
- [x] Prepared 5 compelling demo scenarios
- [ ] Write narration for 30-second explanation
- [x] Test full loop timing (~20-30 seconds per run)

### Safety Limits ✅
- [x] Implement max iteration check (5 iterations max)
- [x] Graceful "best effort" message when limit reached
- [ ] Add timeout handling (optional enhancement)

---

## File Structure (Proposed)

```
building-an-agent/
├── agent/
│   ├── __init__.py
│   ├── agent.py          # Updated with new tools & state
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── compliance.py   # check_compliance()
│   │   ├── policy.py       # get_policy()
│   │   ├── redaction.py    # redact_pii()
│   │   └── submit.py       # submit_email()
│   └── policies/
│       ├── pii.md
│       ├── marketing.md
│       ├── legal.md
│       └── confidentiality.md
├── test_emails/
│   ├── pii_violation.txt
│   ├── marketing_issue.txt
│   ├── confidentiality_breach.txt
│   ├── multiple_issues.txt
│   └── clean_email.txt
└── ...
```

---

## Quick Start Checklist

1. [x] Create `agent/tools/` directory
2. [x] Create `agent/policies/` directory  
3. [x] Implement `check_compliance()` tool
4. [x] Implement `get_policy()` tool
5. [x] Implement `redact_pii()` tool
6. [x] Create policy markdown files
7. [x] Update agent.py with new tools
8. [x] Create test emails
9. [x] Run first end-to-end test ✅
10. [x] Polish streaming output ✅
11. [ ] Demo rehearsal

---

## Success Criteria

- [x] Agent loops visibly (not one-shot) ✅ Shows iterations 1-5+
- [x] Each tool call is explicit and justified ✅ Shows tool name + reasoning
- [x] Final email passes compliance check ✅ Verified on all test cases
- [x] Grounded output (cites policy, shows what was changed) ✅ Fetches policies before rewriting
- [x] Clean timeline view for judges ✅ Emoji-rich, structured output
- [x] Runs reliably in < 30 seconds ✅ ~20-30s per demo run

---

---

## How to Run

```bash
# Run on a specific test email
uv run python -m agent.agent test_emails/pii_violation.txt
uv run python -m agent.agent test_emails/marketing_issue.txt
uv run python -m agent.agent test_emails/confidentiality_breach.txt
uv run python -m agent.agent test_emails/multiple_issues.txt
uv run python -m agent.agent test_emails/clean_email.txt

# Run with default demo email (PII example)
uv run python -m agent.agent
```

---

## Notes

- Keep tools **deterministic** (regex/keyword based) for reliability
- Policy files should be human-readable (good for demo)
- The agent rewrites email text using the "rewrite" action type
- Tools are for **external checks**, not text generation
- Max 5 iterations prevents infinite loops
