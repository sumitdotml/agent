# 2-Hour Hackathon Agent Plan (Experiment → Prototype → Demo)

## Why we’re doing this
In a 2-hour hackathon, we can’t build a full production agent. But we *can* build a convincing prototype that demonstrates the core properties judges associate with an “AI agent,” not just an LLM app.

Our current work is an experiment that proves the agent loop works end-to-end:
- the system **observes**
- **decides** what to do next
- **acts** via tools
- **updates state**
- **loops**
- **stops** with a final answer

This is the minimum unit of “agentic behavior” that can be demoed reliably under time constraints.

---

## Concrete definition: what “AI agent” means (in this hackathon context)
**An AI agent is a goal-directed system where an LLM is used as a decision policy that:**
1. **observes state** (inputs, context, tool outputs),
2. **selects actions** (tool calls or finalization),
3. **executes actions** in an environment (tools / APIs / files / DB),
4. **incorporates feedback** from those actions back into state,
5. **repeats** until a **termination condition** is met.

This is different from:
- a chatbot (reactive Q→A),
- RAG (retrieve→answer),
- fixed workflows (no decision making),
- pipelines (no branching policy).

The “agent” is specifically the **control loop**: the model decides *what to do next* based on the evolving state.

---

## What we built so far: a Minimum Viable Agent (MVA)

### 1) The “agent loop” (concept)
The agent’s behavior can be expressed as a loop:

1. **THINK**: decide next action (tool or final)
2. **ACT**: execute tool if chosen
3. **OBSERVE**: capture tool result in state
4. **repeat** until **FINAL**

This is the smallest system that still counts as an agent.

### 2) Why we used structured JSON actions
We force the model to output *only* valid JSON with one of two schemas:

- Tool call:
  ```json
  {
    "type": "tool",
    "thought_summary": "one short sentence",
    "name": "calculator",
    "input": { "expression": "(2+3)*4" }
  }

- Final answer:

```json
{
  "type": "final",
  "thought_summary": "one short sentence",
  "answer": "..."
}
```

This achieves:

- reliability: less ambiguity than free-form text
- observability: we can show the decision trajectory to judges
- tool routing: deterministic handling of tool calls
- safety: we do not request raw chain-of-thought; we request a one-sentence “thought summary”

In hackathons, this is huge: it makes the system feel “agentic” because decisions are explicit.

### 3) Why we adopted LangGraph

LangGraph is a graph/state-machine framework for agent workflows. Instead of writing `while True: loops` manually, we define:

- State: what the agent “knows” and carries forward
- Nodes: steps like THINK, TOOL, FINALIZE
- Edges: transitions between steps
- Conditional edges: logic to route based on the model decision
- END: termination of the run

This makes the agent:

- easier to reason about
- easier to debug
- easier to demo (because state transitions are explicit)
- streamable (we can show node-by-node execution as a timeline)

### 4) The state machine we implemented (core agent architecture)

#### State

We used a minimal shared state object:
- goal: what the agent is trying to accomplish
- history: a list of events (user input, assistant actions, tool outputs)
- action: the most recent structured decision from the model
- final: the final answer (when done)

This is the bare minimum to demonstrate “memory” and feedback.

#### Nodes
We built three nodes:

Node A — `think`
- Input: current state
- Output: action (tool call or final)

Implementation idea:
- Convert state into messages (system prompt + history + goal)
- Call model (OpenRouter via an OpenAI-compatible endpoint)
- Parse model output as JSON into state["action"]

This is the “policy step” of the agent.

Node B — `tool`
- Input: state["action"] describing a tool call
- Output: appended tool result in history

Implementation idea:
- Execute the specified tool function (e.g., calculator)
- Append a tool-result event to history
- Return to THINK

This is the “acting in the environment” step.

Node C — `finalize`
-Input: state["action"] describing a final response
- Output: set state["final"]

This is the “termination” step.

#### Edges (transitions)
- START → THINK
- THINK → TOOL (if action.type == "tool")
- THINK → FINALIZE (if action.type == "final")
- TOOL → THINK (loop)
- FINALIZE → END

This is the essence of “agent”.

### Why the first version felt “less agentic”
The earlier implementation produced only the final answer. Even though it was an agent internally, the demo experience looked like a normal app.

**Agentic feel requires observability.**

Judges and users need to see:
- "what it decided"
- "what tool it used"
- "what came back"
- "why it stopped"

So we upgraded to streaming, where we render the execution as an “agent timeline”.

### Streaming: making the agent feel alive (without exposing chain-of-thought)

#### What we want to stream

We stream "agent trace" events, not private chain-of-thought:

- 🧠 THINK: one-sentence summary
- 🔧 TOOL_CHOICE: tool name + args
- 📥 TOOL_RESULT: tool output
- ✅ FINAL: final response

#### How LangGraph helps

LangGraph can stream node updates as the graph executes.

#### Why OpenRouter is used and how it fits

We use OpenRouter because it lets us quickly swap models with minimal integration friction.

OpenRouter is compatible with OpenAI-style chat-completions endpoints (base URL + api key), so we can use libraries that expect OpenAI-like APIs while still choosing models via OpenRouter.

This is useful in a hackathon because:

- we can test a fast model for tool decisions
- we can switch to a higher-quality model for final text if needed
- we can use one integration for multiple LLM options

#### What our prototype currently demonstrates (and what it does not)

**It demonstrates:**
- ✅ Goal-directed loop
- ✅ LLM as controller (policy)
- ✅ Tool use (actions)
- ✅ Feedback integration (tool results go back into state)
- ✅ Termination condition (final output)
- ✅ Streaming trace (agent timeline)

**It does not yet demonstrate (but can):**
- ⬜ Multi-tool environment (email, calendar, DB, CRM, ticketing, docs, etc.)
- ⬜ Structured long-term memory (beyond a simple history list)
- ⬜ Robust error recovery and retries
- ⬜ Permissions, audit logs, and policy checks
- ⬜ Multi-agent coordination (optional for hackathon)

For a 2-hour hackathon, we do not need most of the above. But we should architect so they can be added incrementally.

### How this connects to “real-world” (corporate / human-impact) use cases

In the real world, an agent is valuable when it can:

- reduce manual steps
- move information across systems
- enforce consistent policies
- triage, summarize, and execute actions safely

Common corporate “agent” patterns:

- support triage agent (read ticket → ask clarifying questions → draft response → escalate)
- meeting assistant (extract action items → create tasks → notify stakeholders)
- ops agent (inspect logs → run checks → propose fixes → open PR)
- procurement / HR agent (collect requirements → generate forms → route approvals)

All of those can be reduced to:

- a state machine
- tool calls to relevant systems
- safe, observable decision-making

Our prototype is the skeleton that can power any of these.

### Our near-term roadmap (toward a hackathon-grade demo)

#### Phase 1 — “Agent Core” (done)
Phase 1 — “Agent Core” (done)
- agent loop via LangGraph
- structured actions (JSON)
- one tool
- streaming CLI timeline

#### Phase 2 — “Agent Demo UI” (next)
- Goal: make it feel like an agent.

We will build a tiny web UI that shows:

- left: goal + inputs
- right: live timeline of events (think/tool/result/final)
- optional: “state inspector” panel showing the current state object

Streaming mechanism options:

- Server-Sent Events (SSE) over FastAPI
- Streamlit with incremental UI updates
- WebSocket (optional, heavier)

SSE is often ideal for quick hackathons: simple and reliable.

#### Phase 3 — “Real-world toolset” (only if time allows)
Replace the calculator with one or two real tools:

- SQLite query tool (corporate KPI / ops data)
- local file search + summarizer (policy docs / specs)
- ticket mock API tool (simulate corporate workflows)

Pick tools that make the agent feel “real” without requiring enterprise access.

**What success looks like to judges**

A strong 2-hour agent demo shows:

- A clear goal and constraints
- A visible loop (not one-shot completion)
- Tool choice and tool usage are explicit and correct
- Output is grounded in tool results (not hallucinated)
- A clean “agent timeline” makes the process obvious
- Safety posture: no raw chain-of-thought, controlled tools, bounded steps

In other words: agency + correctness + observability.

### Summary

We are building a hackathon-grade AI agent by focusing on the irreducible core:

- The agent is a controller loop (policy → actions → feedback → termination).
- LangGraph expresses this loop as a state machine with nodes and edges.
- We enforce structured decisions via JSON actions for reliability.
- We stream the run as an agent timeline to make it feel truly agentic.
- Next: a web UI that streams these events in real time (SSE/Streamlit).

This gives us a credible “agent” foundation that can later be pointed at real-world tools (work/corporate/human-impact), without changing the agent core.
