"""
FastAPI Backend Server for Outbound Email Guard

Provides REST API endpoints for the web frontend and SSE streaming
for real-time agent execution updates.
"""

import os
import json
import asyncio
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
        state: AgentState = {
            "goal": request.goal,
            "email_draft": request.email_text,
            "history": [],
            "action": None,
            "final": None,
            "iteration": 0,
        }

        current_iteration = 0

        # Send initial event
        print(f"[SSE] Starting agent stream")
        yield f"data: {json.dumps({'type': 'start', 'goal': request.goal})}\n\n"
        await asyncio.sleep(0.1)

        try:
            for update in agent_app.stream(state, stream_mode="updates"):
                for node_name, payload in update.items():

                    if node_name == "think":
                        action = payload.get("action") if isinstance(payload, dict) else None
                        iteration = payload.get("iteration", 0)
                        if iteration > 0:
                            current_iteration = iteration

                        if isinstance(action, dict):
                            print(f"[SSE] Think node - Iteration {iteration}, Action: {action.get('type')}")

                            # Send iteration start event
                            yield f"data: {json.dumps({'type': 'iteration_start', 'iteration': current_iteration})}\n\n"
                            await asyncio.sleep(0.2)

                            # Send thinking event
                            yield f"data: {json.dumps({'type': 'thinking', 'thought': action.get('thought_summary', ''), 'iteration': current_iteration})}\n\n"
                            await asyncio.sleep(0.3)

                            if action.get("type") == "tool":
                                # Send tool selection event
                                yield f"data: {json.dumps({'type': 'tool_selected', 'tool_name': action.get('name', ''), 'tool_input': action.get('input', {}), 'iteration': current_iteration})}\n\n"
                                await asyncio.sleep(0.2)
                            elif action.get("type") == "rewrite":
                                yield f"data: {json.dumps({'type': 'rewrite_start', 'iteration': current_iteration})}\n\n"
                                await asyncio.sleep(0.2)
                            elif action.get("type") == "final":
                                yield f"data: {json.dumps({'type': 'finalizing', 'iteration': current_iteration})}\n\n"
                                await asyncio.sleep(0.2)

                    elif node_name == "tool":
                        hist = payload.get("history") if isinstance(payload, dict) else None
                        if isinstance(hist, list) and hist:
                            last = hist[-1]
                            if last.get("role") == "tool":
                                content = last.get("content", "")
                                print(f"[SSE] Tool node - content preview: {content[:100]}")

                                # Send tool executing event first
                                yield f"data: {json.dumps({'type': 'tool_executing'})}\n\n"
                                await asyncio.sleep(0.4)

                                # Try to parse compliance check result and stream issues individually
                                if "returned:" in content:
                                    try:
                                        result_part = content.split("returned:", 1)[1].strip()
                                        result_json = json.loads(result_part)

                                        if "pass" in result_json:
                                            issues = result_json.get("issues", [])
                                            passed = result_json["pass"]
                                            print(f"[SSE] Compliance check - Pass: {passed}, Issues: {len(issues)}")

                                            # Send compliance check started
                                            yield f"data: {json.dumps({'type': 'compliance_check_started', 'checking': True})}\n\n"
                                            await asyncio.sleep(0.5)

                                            if issues:
                                                # Stream each issue individually with delay
                                                yield f"data: {json.dumps({'type': 'issues_found', 'total_count': len(issues)})}\n\n"
                                                await asyncio.sleep(0.3)

                                                for idx, issue in enumerate(issues):
                                                    severity = issue.get("severity", "medium")
                                                    issue_data = {
                                                        "type": issue.get("type", "unknown"),
                                                        "severity": "critical" if severity in ["critical", "high"] else "warning",
                                                        "title": f"{issue.get('type', 'Unknown').upper()} Issue",
                                                        "description": issue.get("description", ""),
                                                        "category": issue.get("type", "unknown")
                                                    }
                                                    print(f"[SSE] Sending issue {idx+1}/{len(issues)}: {issue_data['title']}")
                                                    yield f"data: {json.dumps({'type': 'issue', 'issue': issue_data, 'index': idx, 'total': len(issues)})}\n\n"
                                                    await asyncio.sleep(0.4)  # Longer delay between each issue

                                                # Send summary after all issues
                                                yield f"data: {json.dumps({'type': 'compliance_result', 'pass': passed, 'issues_count': len(issues), 'summary': result_json.get('summary', ''), 'iteration': current_iteration})}\n\n"
                                            else:
                                                # No issues found
                                                yield f"data: {json.dumps({'type': 'compliance_result', 'pass': passed, 'issues_count': 0, 'summary': 'No issues found', 'iteration': current_iteration})}\n\n"
                                            await asyncio.sleep(0.3)

                                        elif "redacted_text" in result_json:
                                            # Redaction result
                                            redactions = result_json.get("redactions_made", [])
                                            yield f"data: {json.dumps({'type': 'redaction_started'})}\n\n"
                                            await asyncio.sleep(0.2)

                                            for idx, redaction in enumerate(redactions):
                                                yield f"data: {json.dumps({'type': 'redaction_item', 'item': redaction, 'index': idx, 'total': len(redactions)})}\n\n"
                                                await asyncio.sleep(0.15)

                                            yield f"data: {json.dumps({'type': 'redaction_complete', 'count': len(redactions), 'redacted_text': result_json.get('redacted_text', '')[:200]})}\n\n"
                                            await asyncio.sleep(0.1)

                                        else:
                                            # Policy fetch or other tool result
                                            yield f"data: {json.dumps({'type': 'tool_result', 'result': content[:300]})}\n\n"

                                    except json.JSONDecodeError:
                                        # Not JSON, treat as policy text
                                        if "Policy:" in content:
                                            # Extract policy category from content
                                            yield f"data: {json.dumps({'type': 'policy_loaded', 'preview': content[:200]})}\n\n"
                                        else:
                                            yield f"data: {json.dumps({'type': 'tool_result', 'result': content[:300]})}\n\n"
                                else:
                                    # Generic tool result
                                    yield f"data: {json.dumps({'type': 'tool_result', 'result': content[:300]})}\n\n"

                                await asyncio.sleep(0.1)

                    elif node_name == "rewrite":
                        email_draft = payload.get("email_draft") if isinstance(payload, dict) else None
                        if email_draft:
                            print(f"[SSE] Rewrite node - new draft preview: {email_draft[:80]}...")
                            # Send rewrite in progress
                            yield f"data: {json.dumps({'type': 'rewriting', 'iteration': current_iteration})}\n\n"
                            await asyncio.sleep(0.5)

                            # Send rewrite complete with preview
                            yield f"data: {json.dumps({'type': 'rewrite_complete', 'preview': email_draft[:300], 'full_text': email_draft, 'iteration': current_iteration})}\n\n"
                            await asyncio.sleep(0.3)

                    elif node_name == "finalize":
                        final = payload.get("final") if isinstance(payload, dict) else None
                        if final:
                            print(f"[SSE] Finalize node - completed at iteration {current_iteration}")
                            yield f"data: {json.dumps({'type': 'final_check', 'iteration': current_iteration})}\n\n"
                            await asyncio.sleep(0.4)
                            yield f"data: {json.dumps({'type': 'complete', 'final_email': final, 'iteration': current_iteration})}\n\n"
                            await asyncio.sleep(0.2)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
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
