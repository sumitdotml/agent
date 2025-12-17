import os
import json
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

# -----------------------
# Config
# -----------------------
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("Missing OPENROUTER_API_KEY env var")

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

llm = ChatOpenAI(
    model=MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        # Optional but recommended by OpenRouter docs
        "HTTP-Referer": "http://localhost",
        "X-Title": "LangGraphMiniAgentDemo",
    },
)

# -----------------------
# Tool(s)
# -----------------------
def calculator(expression: str) -> str:
    allowed = set("0123456789+-*/(). %")
    if any(ch not in allowed for ch in expression):
        return "ERROR: disallowed characters in expression."
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"ERROR: {e}"

TOOLS = {"calculator": calculator}

# -----------------------
# State
# -----------------------
class AgentState(TypedDict):
    goal: str
    # conversation messages (we keep it simple as strings; we can store LC messages too)
    history: List[Dict[str, str]]  # [{"role":"user"/"assistant"/"tool", "content": "..."}]
    # last structured action chosen by the model
    action: Optional[Dict[str, Any]]
    # final answer if done
    final: Optional[str]

SYSTEM = """I am a minimal AI agent.
I return ONLY valid JSON with one of these schemas:

1) Use a tool:
{
  "type": "tool",
  "thought_summary": "one short sentence about why",
  "name": "calculator",
  "input": {"expression": "(2+3)*4"}
}

2) Finish:
{
  "type": "final",
  "thought_summary": "one short sentence about why the work is done",
  "answer": "final answer for the user"
}

Rules:
- I do NOT reveal chain-of-thought. I use only 'thought_summary' (1 sentence).
- I use tools when needed for correctness.
- I keep JSON strictly valid (no extra text).
"""

def _to_messages(state: AgentState):
    msgs = [SystemMessage(content=SYSTEM)]
    # Replay history
    for item in state["history"]:
        role = item["role"]
        content = item["content"]
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            # As a simplification, we just feed assistant content back as "user context"
            # (works fine for small demos; we can use AIMessage if we prefer).
            msgs.append(HumanMessage(content=f"(assistant previously): {content}"))
        elif role == "tool":
            msgs.append(HumanMessage(content=f"TOOL_RESULT: {content}"))
    # Current goal
    msgs.append(HumanMessage(content=f"GOAL: {state['goal']}"))
    return msgs

# -----------------------
# Nodes
# -----------------------
def think_node(state: AgentState) -> Dict[str, Any]:
    """LLM decides what to do next: tool call or final."""
    msgs = _to_messages(state)
    raw = llm.invoke(msgs).content

    try:
        action = json.loads(raw)
    except json.JSONDecodeError:
        action = {
            "type": "final",
            "thought_summary": "Model returned invalid JSON; stopping.",
            "answer": f"ERROR: Model returned non-JSON:\n{raw}",
        }

    # Store the raw action in state updates
    return {"action": action}

def tool_node(state: AgentState) -> Dict[str, Any]:
    """Execute the selected tool and append result to history."""
    action = state.get("action") or {}
    name = action.get("name")
    tool = TOOLS.get(name)

    if not tool:
        result = f"ERROR: unknown tool '{name}'"
    else:
        try:
            result = tool(**(action.get("input") or {}))
        except Exception as e:
            result = f"ERROR: tool crashed: {e}"

    # Add both tool call + tool result to history so the next THINK sees it
    new_history = list(state["history"])
    new_history.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
    new_history.append({"role": "tool", "content": f"{name} -> {result}"})

    return {"history": new_history}

def finalize_node(state: AgentState) -> Dict[str, Any]:
    action = state.get("action") or {}
    ans = action.get("answer", "")
    new_history = list(state["history"])
    new_history.append({"role": "assistant", "content": ans})
    return {"final": ans, "history": new_history}

# -----------------------
# Routing
# -----------------------
def route_after_think(state: AgentState) -> str:
    t = (state.get("action") or {}).get("type")
    if t == "tool":
        return "tool"
    return "finalize"

# -----------------------
# Build graph
# -----------------------
g = StateGraph(AgentState)
g.add_node("think", think_node)
g.add_node("tool", tool_node)
g.add_node("finalize", finalize_node)

g.add_edge(START, "think")
g.add_conditional_edges("think", route_after_think, {"tool": "tool", "finalize": "finalize"})
g.add_edge("tool", "think")
g.add_edge("finalize", END)

app = g.compile()

# -----------------------
# Pretty streaming renderer
# -----------------------
def render_update(update: Dict[str, Any]):
    # update looks like {"think": {...}} or {"tool": {...}} depending on stream_mode="updates"
    for node_name, payload in update.items():
        if node_name == "think":
            action = payload.get("action") if isinstance(payload, dict) else None
            if isinstance(action, dict):
                ts = action.get("thought_summary", "")
                atype = action.get("type", "")
                if ts:
                    print(f"🧠 THINK: {ts}")
                if atype == "tool":
                    print(f"🔧 TOOL_CHOICE: {action.get('name')}  args={action.get('input')}")
                elif atype == "final":
                    print("✅ DECISION: finalize")
            else:
                print("🧠 THINK: (no action)")
        elif node_name == "tool":
            # tool node appends tool result into history; show last tool line if present
            hist = payload.get("history") if isinstance(payload, dict) else None
            if isinstance(hist, list) and hist:
                # last entry should be tool result
                last = hist[-1]
                if last.get("role") == "tool":
                    print(f"📥 TOOL_RESULT: {last.get('content')}")
        elif node_name == "finalize":
            final = payload.get("final") if isinstance(payload, dict) else None
            if final:
                print(f"\n🎉 FINAL:\n{final}\n")

def run(goal: str):
    state: AgentState = {"goal": goal, "history": [], "action": None, "final": None}

    print("\n==============================")
    print("🚀 LangGraph Mini Agent (streaming)")
    print("==============================\n")
    print(f"🎯 GOAL: {goal}\n")

    # stream_mode="updates" yields node-by-node updates (feels agentic)
    for update in app.stream(state, stream_mode="updates"):
        render_update(update)

if __name__ == "__main__":
    run("What is the compound interest on $1200 at 6% for 3 years, compounded annually?")
