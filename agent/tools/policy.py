"""Policy retrieval tool for compliance guidance."""

import os
from pathlib import Path

# Get the policies directory relative to this file
POLICIES_DIR = Path(__file__).parent.parent / "policies"


# Fallback policies if files don't exist
FALLBACK_POLICIES = {
    "pii": """# PII (Personal Identifiable Information) Policy

## Overview
All outbound communications must protect personal identifiable information (PII) of customers, employees, and partners.

## What Constitutes PII
- Full names (when combined with other data)
- Email addresses (external/personal)
- Phone numbers
- Social Security Numbers (SSN)
- Credit card numbers
- Physical addresses
- Date of birth
- Account numbers

## Requirements
1. **Never include raw PII** in external emails
2. **Redact or mask** sensitive information: use [REDACTED] or partial masking (e.g., ***-**-1234)
3. **Reference by ID** instead of name when possible
4. **Encrypt attachments** containing PII

## Exceptions
- The recipient's own information (when sending to that person)
- Information already publicly available
- Information with explicit written consent to share

## Remediation
If PII is detected, either:
- Remove the PII entirely
- Replace with redacted placeholders
- Reference ticket/case ID instead of personal details""",

    "marketing": """# Marketing Communications Policy

## Overview
All promotional and marketing emails must comply with CAN-SPAM Act and company guidelines.

## Required Elements
1. **Clear identification** as promotional content (if applicable)
2. **Unsubscribe mechanism** - Every marketing email MUST include:
   - "Unsubscribe" link or instructions
   - Format: "To unsubscribe, click here: [link]" or "Reply with UNSUBSCRIBE"
3. **Physical address** of the company
4. **Accurate subject line** - No deceptive subjects

## Prohibited Content
- False or misleading header information
- Deceptive subject lines
- Hidden promotional intent
- Pressure tactics without proper disclosure

## Promotional Language Guidelines
Words like "discount", "offer", "deal", "limited time", "act now" trigger marketing compliance requirements.

## Remediation
If marketing content lacks unsubscribe:
- Add: "To unsubscribe from these communications, please reply with 'UNSUBSCRIBE' or click here: [unsubscribe_link]"
- Place at the bottom of the email""",

    "legal": """# Legal Language Policy

## Overview
Outbound communications must not create unintended legal obligations or liability.

## Prohibited Language
1. **Absolute guarantees**: Avoid "guarantee", "guaranteed", "100%", "promise", "assured"
2. **Binding commitments** without legal review
3. **Unauthorized disclaimers** or liability waivers

## Required Disclaimers
When providing advice or recommendations, include appropriate disclaimers:
- Financial advice: "This is not financial advice. Please consult a qualified financial advisor."
- Legal topics: "This information is for general purposes only and does not constitute legal advice."
- Technical recommendations: "Results may vary. This suggestion is based on general best practices."

## Advisory Language
Phrases like "we recommend", "you should", "our advice", "suggested action" require:
- Appropriate disclaimer
- Qualification of the advice
- Reference to professional consultation if applicable

## Remediation
- Replace "guarantee" with "we aim to" or "our goal is"
- Add appropriate disclaimers for advisory content
- Soften absolute language to qualified statements""",

    "confidentiality": """# Confidentiality Policy

## Overview
Outbound emails must not contain internal-only or confidential information.

## Confidentiality Markers (NEVER in outbound emails)
- "INTERNAL ONLY"
- "CONFIDENTIAL" 
- "DO NOT DISTRIBUTE"
- "NOT FOR EXTERNAL"
- "RESTRICTED"
- "PRIVATE"

If these markers appear, the content should NOT be sent externally.

## Protected Information Categories
1. **Project codenames** - Internal project names like "Project Phoenix" should not be disclosed
2. **Internal systems** - References to Jira, Confluence, internal Slack channels, SharePoint, intranet
3. **Unreleased features** - Product roadmap items not yet public
4. **Internal metrics** - Non-public performance data
5. **Employee information** - Internal org details, salary info, etc.

## Remediation
- Remove confidentiality markers entirely
- Replace project codenames with generic descriptions
- Remove references to internal tools (or replace with "our team" / "we discussed")
- Ensure content is appropriate for external audience

## When in Doubt
If unsure whether content is appropriate for external sharing, remove it or seek approval."""
}


def get_policy(category: str) -> str:
    """
    Retrieve policy text for a given compliance category.
    
    Args:
        category: One of 'pii', 'marketing', 'legal', 'confidentiality'
        
    Returns:
        Policy text as a string
    """
    category = category.lower().strip()
    
    valid_categories = ['pii', 'marketing', 'legal', 'confidentiality']
    if category not in valid_categories:
        return f"ERROR: Unknown policy category '{category}'. Valid categories: {', '.join(valid_categories)}"
    
    # Try to read from file first
    policy_file = POLICIES_DIR / f"{category}.md"
    if policy_file.exists():
        return policy_file.read_text()
    
    # Fall back to embedded policies
    return FALLBACK_POLICIES.get(category, f"ERROR: Policy '{category}' not found")
