"""
FastAPI Backend Server for Outbound Email Guard

Provides REST API endpoints for the web frontend and SSE streaming
for real-time agent execution updates.
"""

import os
import json
import asyncio
from collections.abc import Mapping
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our agent tools
from agent.tools import check_compliance, get_policy, redact_pii

# Import the agent graph
from agent.agent import app as agent_app, AgentState

load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Outbound Email Guard API",
    description="Compliance checking API for outbound emails",
    version="1.0.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class EmailCheckRequest(BaseModel):
    email_text: str

class PolicyRequest(BaseModel):
    category: str

class RedactRequest(BaseModel):
    text: str

class RewriteRequest(BaseModel):
    email_text: str
    issues: Optional[list] = None

class AgentRunRequest(BaseModel):
    email_text: str
    goal: Optional[str] = "Review this email for compliance issues and rewrite it to be compliant."

# ============================================
# API Endpoints
# ============================================

@app.post("/api/check-compliance")
async def api_check_compliance(request: EmailCheckRequest):
    """Check email for compliance issues."""
    result = check_compliance(request.email_text)
    
    # Transform issues to match frontend expected format
    issues = []
    for issue in result.get("issues", []):
        issues.append({
            "type": issue["type"],
            "severity": "critical" if issue.get("severity") == "critical" else "warning",
            "title": f"{issue['type'].upper()} Issue",
            "description": issue["description"],
            "category": issue["type"]
        })
    
    return {
        "issues": issues,
        "pass": result.get("pass", False),
        "summary": result.get("summary", "")
    }

@app.get("/api/policy/{category}")
async def api_get_policy(category: str):
    """Get policy document by category."""
    content = get_policy(category)
    
    if content.startswith("ERROR"):
        raise HTTPException(status_code=404, detail=content)
    
    # Extract title from markdown (first # heading)
    lines = content.split("\n")
    title = category.upper()
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    
    return {
        "category": category,
        "title": title,
        "content": content
    }

@app.post("/api/redact-pii")
async def api_redact_pii(request: RedactRequest):
    """Redact PII from text."""
    result = redact_pii(request.text)
    
    return {
        "original": request.text,
        "redacted": result.get("redacted_text", request.text),
        "redactions": [
            {"type": r.split(":")[0] if ":" in r else "PII", 
             "original": r, 
             "replacement": "[REDACTED]"}
            for r in result.get("redactions_made", [])
        ]
    }

@app.post("/api/rewrite")
async def api_rewrite_email(request: RewriteRequest):
    """Simple rewrite that applies redaction and basic fixes."""
    # For simple rewrite, just apply PII redaction
    redact_result = redact_pii(request.email_text)
    rewritten = redact_result.get("redacted_text", request.email_text)
    
    changes = []
    for r in redact_result.get("redactions_made", []):
        changes.append({
            "original": r,
            "replacement": "[REDACTED]",
            "reason": "PII redaction"
        })
    
    return {
        "rewritten": rewritten,
        "changes": changes
    }

# ============================================
# SSE Streaming Endpoint for Full Agent Run
# ============================================

@app.post("/api/run-agent")
async def api_run_agent_stream(request: AgentRunRequest):
    """
    Run the full agent loop with Server-Sent Events (SSE) streaming.
    Returns real-time updates as the agent executes with granular progressive events.
    """
    async def generate_events():
        def sse(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        def _coerce_int(value, default: int = 0) -> int:
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    return default
            return default

        def _extract_last_tool_call(hist: list) -> tuple[Optional[str], dict]:
            """
            Try to recover the last tool call metadata from history.
            tool_node appends: assistant(JSON tool call) then tool(result).
            """
            if len(hist) < 2:
                return None, {}
            prev = hist[-2]
            if not isinstance(prev, Mapping) or prev.get("role") != "assistant":
                return None, {}
            raw = prev.get("content", "")
            if not isinstance(raw, str) or not raw:
                return None, {}
            try:
                action = json.loads(raw)
            except json.JSONDecodeError:
                return None, {}
            if not isinstance(action, Mapping) or action.get("type") != "tool":
                return None, {}
            return action.get("name"), action.get("input") or {}

        state: AgentState = {
            "goal": request.goal,
            "email_draft": request.email_text,
            "history": [],
            "action": None,
            "final": None,
            "iteration": 0,
            "step": 0,
        }

        # Track "iteration" as compliance cycles (each compliance check == 1 iteration)
        current_cycle = 0
        cycle_count = 0

        def current_iter_for_ui() -> int:
            return current_cycle if current_cycle > 0 else 1

        # Send initial event
        print(f"[SSE] Starting agent stream")
        yield sse({"type": "start", "goal": request.goal})
        await asyncio.sleep(0.1)

        try:
            for update in agent_app.stream(state, stream_mode="updates"):
                for node_name, payload in update.items():

                    if not isinstance(payload, Mapping):
                        continue

                    # ----------------------------
                    # Finalize (robust to node name)
                    # ----------------------------
                    if payload.get("final"):
                        final = payload.get("final")
                        print(f"[SSE] Finalize node ({node_name}) - completed at iteration {current_iter_for_ui()}")
                        yield sse({"type": "final_check", "iteration": current_iter_for_ui()})
                        await asyncio.sleep(0.2)
                        yield sse({"type": "complete", "final_email": final, "iteration": current_iter_for_ui()})
                        await asyncio.sleep(0.1)
                        continue

                    # ----------------------------
                    # Think / decision (robust to node name)
                    # ----------------------------
                    if "action" in payload:
                        action = payload.get("action")
                        if isinstance(action, Mapping):
                            action_type = action.get("type")
                            tool_name = action.get("name") if action_type == "tool" else None
                            if action_type == "tool" and tool_name == "check_compliance":
                                cycle_count += 1
                                current_cycle = cycle_count
                                yield sse({"type": "iteration_start", "iteration": current_cycle})
                                await asyncio.sleep(0.05)

                            print(
                                f"[SSE] Think node ({node_name}) - Cycle {current_iter_for_ui()}, Action: {action_type}"
                            )

                            yield sse(
                                {
                                    "type": "thinking",
                                    "thought": action.get("thought_summary", ""),
                                    "iteration": current_iter_for_ui(),
                                }
                            )
                            await asyncio.sleep(0.05)

                            if action_type == "tool":
                                yield sse(
                                    {
                                        "type": "tool_selected",
                                        "tool_name": tool_name or "",
                                        "tool_input": action.get("input", {}),
                                        "iteration": current_iter_for_ui(),
                                    }
                                )
                                await asyncio.sleep(0.05)
                            elif action_type == "rewrite":
                                yield sse({"type": "rewrite_start", "iteration": current_iter_for_ui()})
                                await asyncio.sleep(0.05)
                            elif action_type == "final":
                                yield sse({"type": "finalizing", "iteration": current_iter_for_ui()})
                                await asyncio.sleep(0.05)
                        continue

                    # ----------------------------
                    # Tool update vs rewrite update (both include history)
                    # ----------------------------
                    hist = payload.get("history")
                    if isinstance(hist, list) and hist:
                        last = hist[-1]
                        last_role = last.get("role") if isinstance(last, Mapping) else None

                        # Tool node updates always end with the tool result.
                        if last_role == "tool":
                            content = last.get("content", "") if isinstance(last, Mapping) else ""
                            if not isinstance(content, str):
                                content = str(content)

                            tool_name, tool_input = _extract_last_tool_call(hist)
                            if not tool_name and " returned:" in content:
                                tool_name = content.split(" returned:", 1)[0].strip()

                            print(f"[SSE] Tool node ({node_name}) - {tool_name or 'unknown'} preview: {content[:100]}")

                            yield sse(
                                {
                                    "type": "tool_executing",
                                    "iteration": current_iter_for_ui(),
                                    "tool_name": tool_name,
                                }
                            )
                            await asyncio.sleep(0.05)

                            if "returned:" not in content:
                                yield sse(
                                    {
                                        "type": "tool_result",
                                        "iteration": current_iter_for_ui(),
                                        "tool_name": tool_name,
                                        "result": content[:300],
                                    }
                                )
                                await asyncio.sleep(0.05)
                                continue

                            result_part = content.split("returned:", 1)[1].strip()

                            # Tool-specific handling
                            if tool_name == "get_policy":
                                # Raw markdown policy text
                                title = None
                                for line in result_part.splitlines():
                                    if line.startswith("# "):
                                        title = line[2:].strip()
                                        break
                                yield sse(
                                    {
                                        "type": "policy_loaded",
                                        "iteration": current_iter_for_ui(),
                                        "category": (tool_input or {}).get("category"),
                                        "title": title,
                                        "preview": result_part[:400],
                                    }
                                )
                                await asyncio.sleep(0.05)
                                continue

                            # JSON-ish tools
                            try:
                                result_json = json.loads(result_part)
                            except json.JSONDecodeError:
                                yield sse(
                                    {
                                        "type": "tool_result",
                                        "iteration": current_iter_for_ui(),
                                        "tool_name": tool_name,
                                        "result": content[:300],
                                    }
                                )
                                await asyncio.sleep(0.05)
                                continue

                            if "pass" in result_json:
                                issues = result_json.get("issues", []) or []
                                passed = bool(result_json.get("pass"))
                                print(f"[SSE] Compliance check - Pass: {passed}, Issues: {len(issues)}")

                                yield sse({"type": "compliance_check_started", "iteration": current_iter_for_ui()})
                                await asyncio.sleep(0.05)

                                if issues:
                                    yield sse(
                                        {
                                            "type": "issues_found",
                                            "iteration": current_iter_for_ui(),
                                            "total_count": len(issues),
                                        }
                                    )
                                    await asyncio.sleep(0.05)

                                    for idx, issue in enumerate(issues):
                                        if not isinstance(issue, Mapping):
                                            continue
                                        severity = issue.get("severity", "medium")
                                        issue_type = issue.get("type", "unknown")
                                        issue_data = {
                                            "type": issue_type,
                                            "severity": "critical"
                                            if severity in ["critical", "high"]
                                            else "warning",
                                            "title": f"{str(issue_type).upper()} Issue",
                                            "description": issue.get("description", ""),
                                            "category": issue_type,
                                        }
                                        print(f"[SSE] Sending issue {idx+1}/{len(issues)}: {issue_data['title']}")
                                        yield sse(
                                            {
                                                "type": "issue",
                                                "iteration": current_iter_for_ui(),
                                                "issue": issue_data,
                                                "index": idx,
                                                "total": len(issues),
                                            }
                                        )
                                        await asyncio.sleep(0.05)

                                yield sse(
                                    {
                                        "type": "compliance_result",
                                        "iteration": current_iter_for_ui(),
                                        "pass": passed,
                                        "issues_count": len(issues),
                                        "summary": result_json.get("summary", ""),
                                    }
                                )
                                await asyncio.sleep(0.05)

                                if not passed and issues:
                                    feedback_map = {
                                        "pii": "Remove/redact any third-party PII (emails, phones, SSNs, account numbers).",
                                        "marketing": "Add clear unsubscribe instructions and avoid pressure tactics or misleading urgency.",
                                        "legal": "Soften absolute claims/guarantees and add appropriate disclaimers for advice.",
                                        "confidentiality": "Remove internal-only markers and references to internal tools/projects.",
                                    }
                                    categories = sorted(
                                        {str(i.get("type")) for i in issues if isinstance(i, Mapping) and i.get("type")}
                                    )
                                    suggestions = [feedback_map.get(c) for c in categories if feedback_map.get(c)]
                                    if suggestions:
                                        yield sse(
                                            {
                                                "type": "feedback",
                                                "iteration": current_iter_for_ui(),
                                                "categories": categories,
                                                "text": " ".join(suggestions),
                                            }
                                        )
                                        await asyncio.sleep(0.05)

                                continue

                            if "redacted_text" in result_json:
                                redactions = result_json.get("redactions_made", []) or []
                                yield sse({"type": "redaction_started", "iteration": current_iter_for_ui()})
                                await asyncio.sleep(0.05)

                                for idx, redaction in enumerate(redactions):
                                    yield sse(
                                        {
                                            "type": "redaction_item",
                                            "iteration": current_iter_for_ui(),
                                            "item": redaction,
                                            "index": idx,
                                            "total": len(redactions),
                                        }
                                    )
                                    await asyncio.sleep(0.02)

                                yield sse(
                                    {
                                        "type": "redaction_complete",
                                        "iteration": current_iter_for_ui(),
                                        "count": len(redactions),
                                        "redacted_text": result_json.get("redacted_text", "")[:200],
                                    }
                                )
                                await asyncio.sleep(0.05)
                                continue

                            yield sse(
                                {
                                    "type": "tool_result",
                                    "iteration": current_iter_for_ui(),
                                    "tool_name": tool_name,
                                    "result": content[:300],
                                }
                            )
                            await asyncio.sleep(0.05)
                            continue

                    # ----------------------------
                    # Rewrite node (robust to node name)
                    # ----------------------------
                    email_draft = payload.get("email_draft")
                    if isinstance(email_draft, str) and email_draft:
                        print(f"[SSE] Rewrite node ({node_name}) - new draft preview: {email_draft[:80]}...")
                        yield sse({"type": "rewriting", "iteration": current_iter_for_ui()})
                        await asyncio.sleep(0.05)
                        yield sse(
                            {
                                "type": "rewrite_complete",
                                "preview": email_draft[:300],
                                "full_text": email_draft,
                                "iteration": current_iter_for_ui(),
                            }
                        )
                        await asyncio.sleep(0.05)
                        continue

        except Exception as e:
            yield sse({"type": "error", "message": str(e)})

        yield sse({"type": "done"})

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

# ============================================
# Non-streaming Agent Run (simpler)
# ============================================

@app.post("/api/run-agent-sync")
async def api_run_agent_sync(request: AgentRunRequest):
    """
    Run the full agent loop synchronously and return the final result.
    Use this for simpler integrations that don't need streaming.
    """
    state: AgentState = {
        "goal": request.goal,
        "email_draft": request.email_text,
        "history": [],
        "action": None,
        "final": None,
        "iteration": 0,
        "step": 0,
    }
    
    iterations = []
    final_email = request.email_text
    
    try:
        for update in agent_app.stream(state, stream_mode="updates"):
            for node_name, payload in update.items():
                if node_name == "think":
                    action = payload.get("action") if isinstance(payload, dict) else None
                    if isinstance(action, dict):
                        iterations.append({
                            "iteration": payload.get("iteration", 0),
                            "thought": action.get("thought_summary", ""),
                            "action_type": action.get("type", ""),
                            "tool_name": action.get("name") if action.get("type") == "tool" else None
                        })
                        
                elif node_name == "finalize":
                    final = payload.get("final") if isinstance(payload, dict) else None
                    if final:
                        final_email = final
                        
    except Exception as e:
        return {"error": str(e), "final_email": final_email, "iterations": iterations}
    
    # Check final compliance
    final_check = check_compliance(final_email)
    
    return {
        "final_email": final_email,
        "passed": final_check.get("pass", False),
        "iterations": iterations,
        "total_iterations": len(iterations)
    }

# ============================================
# Static Files (Web UI)
# ============================================

# Serve web directory
WEB_DIR = Path(__file__).parent / "web"

# Mount static files at /static path (not root, to avoid conflicts with API)
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

@app.get("/")
async def serve_index():
    """Serve the main HTML page."""
    return FileResponse(WEB_DIR / "index.html")

@app.get("/styles.css")
async def serve_styles():
    """Serve CSS file."""
    return FileResponse(WEB_DIR / "styles.css", media_type="text/css")

@app.get("/app.js")
async def serve_app_js():
    """Serve app.js file."""
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")

@app.get("/api.js")
async def serve_api_js():
    """Serve api.js file."""
    return FileResponse(WEB_DIR / "api.js", media_type="application/javascript")

# ============================================
# Health Check
# ============================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🚀 Starting Outbound Email Guard Server on http://localhost:{port}")
    print(f"📁 Serving web UI from: {WEB_DIR}")
    print(f"\n📋 API Endpoints:")
    print(f"   POST /api/check-compliance  - Check email compliance")
    print(f"   GET  /api/policy/{{category}} - Get policy document")
    print(f"   POST /api/redact-pii        - Redact PII from text")
    print(f"   POST /api/rewrite           - Simple rewrite with redaction")
    print(f"   POST /api/run-agent         - Full agent (SSE streaming)")
    print(f"   POST /api/run-agent-sync    - Full agent (synchronous)")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=port)
