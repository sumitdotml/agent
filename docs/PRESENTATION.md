# Outbound Email Guard: An AI Agent for Compliance Review

---

## The Problem

**Outbound emails can contain:**
- Leaked PII (emails, phones, SSNs)
- Confidential markers ("INTERNAL ONLY")
- Unapproved legal language ("we guarantee...")
- Marketing violations (missing unsubscribe)

**Manual review is slow and error-prone.**

---

## Our Solution: An AI Agent

Not just an LLM prompt — a **goal-directed agent** that:

1. **Observes** → Checks email for compliance issues
2. **Decides** → Determines which policy to reference
3. **Acts** → Rewrites the email to fix issues
4. **Loops** → Re-checks until compliant
5. **Stops** → Outputs the safe version

---

## What Makes It an "Agent"?

| Chatbot | RAG App | **Our Agent** |
|---------|---------|---------------|
| Q → A | Retrieve → Answer | Loop until goal met |
| Reactive | One-shot | Goal-directed |
| No tools | Search only | Multiple tools |
| No state | No memory | Iterative state |

**The agent is the control loop — the LLM decides what to do next.**

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│              USER INPUT                     │
│         (Draft Email to Review)             │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│            AGENT LOOP (LangGraph)           │
│  ┌─────────┐    ┌──────┐    ┌─────────┐     │
│  │  THINK  │───▶│ TOOL │───▶│ REWRITE │     │
│  └────┬────┘    └──────┘    └────┬────┘     │
│       │                          │          │
│       └──────────◀───────────────┘          │
│                  │                          │
│            ┌─────▼─────┐                    │
│            │ FINALIZE  │                    │
│            └───────────┘                    │
└─────────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│           COMPLIANT EMAIL                   │
└─────────────────────────────────────────────┘
```

---

## The Tools

1. `check_compliance(email_text)`

Detects issues using regex patterns:
- PII (emails, phones, SSN, credit cards)
- Marketing (promo language without unsubscribe)
- Legal (unapproved guarantees)
- Confidentiality (internal markers, codenames)

2. `get_policy(category)`

Retrieves policy documents:
- `pii.md` — Data protection rules
- `marketing.md` — CAN-SPAM compliance
- `legal.md` — Financial disclaimers
- `confidentiality.md` — What never to share

3. `redact_pii(text)`

Masks sensitive data:
- `john@email.com` → `[REDACTED_EMAIL]`
- `555-123-4567` → `[REDACTED_PHONE]`
- `123-45-6789` → `[REDACTED_SSN]`

---

## The Agent Loop in Action

```
Iteration 1:
  🧠 THINK: "Checking email for compliance issues"
  🔧 TOOL: check_compliance → Found 7 issues
  📋 TOOL: get_policy("pii") → Retrieved policy
  ✏️ REWRITE: Fixed PII and markers

Iteration 2:
  🔧 TOOL: check_compliance → Found 3 issues
  📋 TOOL: get_policy("legal") → Retrieved policy
  ✏️ REWRITE: Fixed guarantee language

Iteration 3:
  🔧 TOOL: check_compliance → 0 issues, PASS!
  ✅ FINALIZE: Output compliant email
```

---

## Structured Actions (Not Free Text)

The agent outputs **strict JSON** for reliability:

```json
{
  "type": "tool",
  "thought_summary": "Checking for compliance issues",
  "name": "check_compliance",
  "input": {"email_text": "..."}
}
```

```json
{
  "type": "rewrite",
  "thought_summary": "Removing PII and confidential markers",
  "email": "Dear Customer, ..."
}
```

```json
{
  "type": "final",
  "thought_summary": "Email now passes all checks",
  "answer": "Dear Customer, ..."
}
```

---

## Why LangGraph?

Instead of `while True` loops, we define:

- **State** — What the agent knows
- **Nodes** — THINK, TOOL, REWRITE, FINALIZE
- **Edges** — Transitions between nodes
- **Conditional edges** — Route based on action type

**Benefits:**
- Easier to debug
- Streamable execution
- Visual state machine
- Built-in safety limits

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | LangGraph |
| LLM Provider | OpenRouter (GPT-4o-mini) |
| Backend | FastAPI + SSE Streaming |
| Frontend | Vanilla JS |
| Tools | Python (regex-based) |

---

## Before & After

**Before (Non-compliant):**
```
CONFIDENTIAL - Internal Only

Dear Mr. John Smith,

We guarantee 100% returns! Contact john@gmail.com
or call 555-123-4567. Your SSN 123-45-6789 is on file.

As discussed in Jira ticket PROJ-1234, Project Phoenix
launches next quarter.
```

**After (Compliant):**
```
Dear Mr. John Smith,

We aim to provide reliable returns. Please contact
our support team for assistance.

We're excited to share updates on our upcoming
product launch.

[Unsubscribe link]
```

---

## What We Learned

### Agentic Behavior Requires Observability
- Users need to SEE the loop
- Show iterations, tool calls, decisions
- "Black box → output" doesn't feel agentic

### Structured Actions > Free Text
- JSON actions are predictable
- Easy to route and validate
- Debuggable decision trajectory

### Tools Should Be Deterministic
- Regex-based detection = reliable
- Minimal to no LLM hallucination in tool outputs
- LLM decides WHEN to use tools, not HOW they work

---

## Challenges Faced

### SSE Streaming Complexity
- Events need proper buffering
- Async callback timing matters
- Browser needs to process before next event

### Making It Feel "Alive"
- Progressive UI updates
- Typing animations
- Issue-by-issue reveal

### Balancing Speed vs. Visibility
- Too fast = looks like one-shot
- Too slow = frustrating
- Found sweet spot with 200-400ms delays

---

## Future Improvements

- [ ] Multi-tool parallel execution
- [ ] Human-in-the-loop approval step
- [ ] Integration with email clients (Gmail, Outlook)
- [ ] Custom policy configuration
- [ ] Audit logging for compliance records
- [ ] Multi-agent review (legal + security + marketing)

---

## Key Takeaways

1. **An agent is a control loop** — observe, decide, act, repeat

2. **LangGraph makes agents easier** — state machines with streaming

3. **Observability matters** — show the process, not just the result

4. **Tools should be reliable** — deterministic > AI-generated

5. **Compliance is a great use case** — clear rules, measurable outcomes

---

## DEMO

---

## Thank You!

**Outbound Email Guard**
*An AI Agent for Compliance Review*

## Resources

- GitHub: [github.com/sumitdotml/building-an-agent](https://github.com/sumitdotml/building-an-agent)
- LangGraph: [langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/)
- OpenRouter: [openrouter.ai/](https://openrouter.ai/)

---
