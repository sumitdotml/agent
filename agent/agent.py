"""
Outbound Email Guard Agent

A compliance agent that reviews outbound emails for policy violations
and iteratively rewrites them until they pass all compliance checks.

Loop: check → fetch relevant policy → rewrite → redact → re-check → repeat until pass=true
"""

import os
import json
from typing import TypedDict, List, Dict, Any, Optional
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

# Import our compliance tools
from agent.tools import check_compliance, get_policy, redact_pii

load_dotenv()

# -----------------------
# Config
# -----------------------
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("Missing OPENROUTER_API_KEY env var")

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
MAX_ITERATIONS = 5  # Safety limit to prevent infinite loops

llm = ChatOpenAI(
    model=MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "OutboundEmailGuard",
    },
)

# -----------------------
# Tools Registry
# -----------------------
def _check_compliance_wrapper(email_text: str) -> str:
    """Wrapper that returns JSON string for the agent."""
    result = check_compliance(email_text)
    return json.dumps(result, indent=2)

def _get_policy_wrapper(category: str) -> str:
    """Wrapper for policy retrieval."""
    return get_policy(category)

def _redact_pii_wrapper(text: str) -> str:
    """Wrapper that returns JSON string with redacted text."""
    result = redact_pii(text)
    return json.dumps(result, indent=2)

TOOLS = {
    "check_compliance": _check_compliance_wrapper,
    "get_policy": _get_policy_wrapper,
    "redact_pii": _redact_pii_wrapper,
}

TOOL_DESCRIPTIONS = """
Available tools:

1. check_compliance(email_text: str)
   - Checks email for compliance issues (PII, marketing, legal, confidentiality)
   - Returns: {"issues": [...], "pass": bool, "summary": str}
   - Use this FIRST to identify problems, and AFTER each rewrite to verify fixes

2. get_policy(category: str)
   - Retrieves policy guidelines for a specific category
   - Categories: "pii", "marketing", "legal", "confidentiality"
   - Use this to understand HOW to fix identified issues

3. redact_pii(text: str)
   - Automatically redacts PII (emails, phones, SSN, etc.) from text
   - Returns: {"redacted_text": str, "redactions_made": [...], "summary": str}
   - NOTE: Does NOT redact recipient names in greetings (e.g., "Dear Mr. Smith" stays intact)
   - Use this for OTHER people's PII mentioned in the email body
"""

# -----------------------
# State
# -----------------------
class AgentState(TypedDict):
    goal: str  # The task (review this email for compliance)
    email_draft: str  # Current version of the email
    history: List[Dict[str, str]]  # Conversation/tool history
    action: Optional[Dict[str, Any]]  # Last action chosen
    final: Optional[str]  # Final compliant email
    iteration: int  # Track iterations for safety

# -----------------------
# System Prompt
# -----------------------
SYSTEM = f"""You are the Outbound Email Guard, a compliance agent that reviews emails before they are sent externally.

Your job:
1. Check the email for compliance issues using the check_compliance tool
2. If issues are found, fetch the relevant policy to understand how to fix them
3. Rewrite the email to fix the issues (you output the rewritten version as your final answer)
4. Use redact_pii if PII needs to be removed
5. Re-check the rewritten email
6. Repeat until the email passes OR you've tried {MAX_ITERATIONS} times

{TOOL_DESCRIPTIONS}

You MUST return ONLY valid JSON with one of these schemas:

1) Use a tool:
{{
  "type": "tool",
  "thought_summary": "one short sentence about why",
  "name": "<tool_name>",
  "input": {{"<param>": "<value>"}}
}}

2) Propose a rewritten version of the email (use this when you need to fix issues):
{{
  "type": "rewrite",
  "thought_summary": "one short sentence about what you're fixing",
  "email": "<the complete rewritten email text>"
}}

3) Finalize and approve the email (use when email passes compliance):
{{
  "type": "final",
  "thought_summary": "one short sentence summarizing the outcome",
  "answer": "<the final approved email>"
}}

Rules:
- ALWAYS start by checking compliance on the original email
- Fetch relevant policies BEFORE attempting to rewrite
- Use "rewrite" type to propose a fixed version, then re-check compliance
- When rewriting, preserve the email's intent while fixing ALL identified issues
- Use "final" type ONLY when compliance check passes
- If the email is already compliant, return it unchanged with "final" type
- Keep JSON strictly valid (no extra text outside the JSON)

IMPORTANT - What to preserve vs. remove:
- KEEP the recipient's name in greetings (e.g., "Dear Mr. John Smith" - this is who you're writing TO)
- REMOVE/REDACT other people's PII mentioned in the body (e.g., "Account holder: Mr. James Wilson")
- REMOVE confidentiality markers like "INTERNAL ONLY", "CONFIDENTIAL"
- REMOVE internal system references (Jira, Confluence, Slack channels, project codenames)
- ADD unsubscribe link for marketing/promotional emails
- SOFTEN guarantee language ("guaranteed" → "we aim to")
- ADD appropriate disclaimers for financial/legal advice
"""

# -----------------------
# Message Construction
# -----------------------
def _to_messages(state: AgentState):
    msgs = [SystemMessage(content=SYSTEM)]
    
    # Add iteration context
    if state["iteration"] > 0:
        msgs.append(HumanMessage(content=f"[Iteration {state['iteration']}/{MAX_ITERATIONS}]"))
    
    # Replay history
    for item in state["history"]:
        role = item["role"]
        content = item["content"]
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs.append(HumanMessage(content=f"(previous action): {content}"))
        elif role == "tool":
            msgs.append(HumanMessage(content=f"TOOL_RESULT:\n{content}"))
    
    # Current email and goal
    msgs.append(HumanMessage(content=f"""
TASK: {state['goal']}

CURRENT EMAIL DRAFT:
---
{state['email_draft']}
---

Analyze this email and take the next appropriate action.
"""))
    
    return msgs

# -----------------------
# Nodes
# -----------------------
def think_node(state: AgentState) -> Dict[str, Any]:
    """LLM decides what to do next: tool call or final."""
    
    # Check iteration limit
    if state["iteration"] >= MAX_ITERATIONS:
        return {
            "action": {
                "type": "final",
                "thought_summary": f"Reached maximum iterations ({MAX_ITERATIONS}). Returning best effort.",
                "answer": state["email_draft"]
            }
        }
    
    msgs = _to_messages(state)
    raw = llm.invoke(msgs).content
    
    # Try to extract JSON from the response (handle markdown code blocks)
    json_str = raw.strip()
    if json_str.startswith("```"):
        # Remove markdown code block
        lines = json_str.split("\n")
        json_str = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
    
    try:
        action = json.loads(json_str)
    except json.JSONDecodeError:
        action = {
            "type": "final",
            "thought_summary": "Model returned invalid JSON; stopping.",
            "answer": f"ERROR: Model returned non-JSON:\n{raw}",
        }

    return {"action": action, "iteration": state["iteration"] + 1}

def tool_node(state: AgentState) -> Dict[str, Any]:
    """Execute the selected tool and append result to history."""
    action = state.get("action") or {}
    name = action.get("name")
    tool = TOOLS.get(name)

    if not tool:
        result = f"ERROR: unknown tool '{name}'. Available tools: {list(TOOLS.keys())}"
    else:
        try:
            tool_input = action.get("input") or {}
            result = tool(**tool_input)
        except Exception as e:
            result = f"ERROR: tool crashed: {e}"

    # Add both tool call + tool result to history
    new_history = list(state["history"])
    new_history.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
    new_history.append({"role": "tool", "content": f"{name} returned:\n{result}"})
    
    # If this was a redact_pii call, update the email draft with redacted version
    updates = {"history": new_history}
    if name == "redact_pii":
        try:
            result_data = json.loads(result)
            if "redacted_text" in result_data:
                updates["email_draft"] = result_data["redacted_text"]
        except:
            pass  # Keep original if parsing fails
    
    return updates

def finalize_node(state: AgentState) -> Dict[str, Any]:
    """Finalize with the compliant email."""
    action = state.get("action") or {}
    final_email = action.get("answer", state["email_draft"])
    thought = action.get("thought_summary", "")
    
    new_history = list(state["history"])
    new_history.append({"role": "assistant", "content": f"FINAL: {thought}\n\n{final_email}"})
    
    return {"final": final_email, "history": new_history}

# -----------------------
# Rewrite Node
# -----------------------
def rewrite_node(state: AgentState) -> Dict[str, Any]:
    """Update the email draft with the proposed rewrite."""
    action = state.get("action") or {}
    new_email = action.get("email", state["email_draft"])
    thought = action.get("thought_summary", "")
    
    new_history = list(state["history"])
    new_history.append({
        "role": "assistant", 
        "content": f"REWRITE: {thought}\n\nProposed new version:\n{new_email}"
    })
    
    return {"email_draft": new_email, "history": new_history}

# -----------------------
# Routing
# -----------------------
def route_after_think(state: AgentState) -> str:
    t = (state.get("action") or {}).get("type")
    if t == "tool":
        return "tool"
    elif t == "rewrite":
        return "rewrite"
    return "finalize"

# -----------------------
# Build Graph
# -----------------------
g = StateGraph(AgentState)
g.add_node("think", think_node)
g.add_node("tool", tool_node)
g.add_node("rewrite", rewrite_node)
g.add_node("finalize", finalize_node)

g.add_edge(START, "think")
g.add_conditional_edges("think", route_after_think, {"tool": "tool", "rewrite": "rewrite", "finalize": "finalize"})
g.add_edge("tool", "think")
g.add_edge("rewrite", "think")  # After rewrite, go back to think to re-check
g.add_edge("finalize", END)

app = g.compile()

# -----------------------
# Pretty Streaming Renderer
# -----------------------
def render_update(update: Dict[str, Any]):
    """Render agent updates in a readable format."""
    for node_name, payload in update.items():
        if node_name == "think":
            action = payload.get("action") if isinstance(payload, dict) else None
            iteration = payload.get("iteration", 0)
            if isinstance(action, dict):
                ts = action.get("thought_summary", "")
                atype = action.get("type", "")
                print(f"\n{'='*50}")
                print(f"🔄 Iteration {iteration}")
                print(f"{'='*50}")
                if ts:
                    print(f"🧠 THINKING: {ts}")
                if atype == "tool":
                    tool_name = action.get('name')
                    tool_input = action.get('input', {})
                    print(f"🔧 TOOL: {tool_name}")
                    # Show truncated input for readability
                    for k, v in tool_input.items():
                        v_str = str(v)
                        if len(v_str) > 100:
                            v_str = v_str[:100] + "..."
                        print(f"   └─ {k}: {v_str}")
                elif atype == "rewrite":
                    print("✏️  DECISION: Rewriting email")
                elif atype == "final":
                    print("✅ DECISION: Finalizing email")
                    
        elif node_name == "tool":
            hist = payload.get("history") if isinstance(payload, dict) else None
            if isinstance(hist, list) and hist:
                last = hist[-1]
                if last.get("role") == "tool":
                    content = last.get("content", "")
                    # Parse and display tool result nicely
                    print(f"\n📥 RESULT:")
                    # Try to parse as JSON for nicer display
                    try:
                        if "returned:" in content:
                            result_part = content.split("returned:", 1)[1].strip()
                            result_json = json.loads(result_part)
                            if "pass" in result_json:
                                status = "✅ PASS" if result_json["pass"] else "❌ FAIL"
                                print(f"   Status: {status}")
                                if result_json.get("issues"):
                                    print(f"   Issues found: {len(result_json['issues'])}")
                                    for issue in result_json["issues"][:3]:  # Show max 3
                                        print(f"   └─ [{issue['type']}] {issue['description']}")
                            elif "redacted_text" in result_json:
                                print(f"   {result_json.get('summary', 'Redaction complete')}")
                            else:
                                # Policy text - show first 200 chars
                                print(f"   Policy retrieved (showing preview):")
                                preview = result_part[:200] + "..." if len(result_part) > 200 else result_part
                                print(f"   {preview}")
                    except:
                        # Show raw if parsing fails
                        preview = content[:300] + "..." if len(content) > 300 else content
                        print(f"   {preview}")
                        
        elif node_name == "rewrite":
            email_draft = payload.get("email_draft") if isinstance(payload, dict) else None
            if email_draft:
                print(f"\n📝 REWRITTEN EMAIL (preview):")
                preview = email_draft[:300] + "..." if len(email_draft) > 300 else email_draft
                for line in preview.split('\n')[:8]:  # Show first 8 lines
                    print(f"   {line}")
                if len(email_draft) > 300 or len(email_draft.split('\n')) > 8:
                    print(f"   ...")
                    
        elif node_name == "finalize":
            final = payload.get("final") if isinstance(payload, dict) else None
            if final:
                print(f"\n{'='*50}")
                print("🎉 FINAL COMPLIANT EMAIL")
                print(f"{'='*50}")
                print(final)
                print(f"{'='*50}\n")

# -----------------------
# Main Run Function  
# -----------------------
def run(email_text: str, goal: str = "Review this email for compliance issues and rewrite it to be compliant."):
    """
    Run the Email Guard agent on an email.
    
    Args:
        email_text: The email content to review
        goal: Optional custom goal/instructions
    """
    state: AgentState = {
        "goal": goal,
        "email_draft": email_text,
        "history": [],
        "action": None,
        "final": None,
        "iteration": 0,
    }

    print("\n" + "="*60)
    print("📧 OUTBOUND EMAIL GUARD - Compliance Agent")
    print("="*60)
    print(f"\n🎯 GOAL: {goal}")
    print(f"\n📝 ORIGINAL EMAIL:\n{'-'*40}")
    print(email_text)
    print(f"{'-'*40}\n")
    print("Starting compliance review...\n")

    for update in app.stream(state, stream_mode="updates"):
        render_update(update)

def run_from_file(filepath: str):
    """Run the agent on an email from a file."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}")
        return
    
    email_text = path.read_text()
    run(email_text)

# -----------------------
# CLI Entry Point
# -----------------------
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run on specified file
        run_from_file(sys.argv[1])
    else:
        # Default demo with PII violation email
        demo_email = """Subject: Update on Your Account Issue

Hi,

I wanted to follow up regarding the issue you reported last week.

I've reviewed the account for John Smith (john.smith@gmail.com) and found the following:
- Account holder: John Smith
- Phone on file: (555) 123-4567
- Last 4 of SSN: The full SSN 452-33-8891 was used for verification

We recommend updating your contact information at your earliest convenience.

Please let me know if you have any questions.

Best regards,
Customer Support Team"""
        
        run(demo_email)
