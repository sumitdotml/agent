"""Compliance checking tool for email content."""

import re
from typing import Dict, List, Any


def check_compliance(email_text: str) -> Dict[str, Any]:
    """
    Check an email for compliance issues.
    
    Args:
        email_text: The email content to check
        
    Returns:
        Dict with 'issues' list and 'pass' boolean
    """
    issues: List[Dict[str, str]] = []
    
    # --- PII Detection ---
    
    # Email addresses (not in standard signature blocks)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails_found = re.findall(email_pattern, email_text)
    # Filter out common corporate domains that might be okay
    suspicious_emails = [e for e in emails_found if not e.endswith(('@company.com', '@example.com'))]
    if suspicious_emails:
        issues.append({
            "type": "pii",
            "description": f"External email addresses found: {', '.join(suspicious_emails[:3])}",
            "severity": "high"
        })
    
    # Phone numbers
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
    if re.search(phone_pattern, email_text):
        issues.append({
            "type": "pii",
            "description": "Phone number detected in email body",
            "severity": "high"
        })
    
    # SSN patterns
    ssn_pattern = r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'
    if re.search(ssn_pattern, email_text):
        issues.append({
            "type": "pii",
            "description": "Possible SSN pattern detected",
            "severity": "critical"
        })
    
    # Credit card patterns (basic)
    cc_pattern = r'\b(?:\d{4}[-.\s]?){3}\d{4}\b'
    if re.search(cc_pattern, email_text):
        issues.append({
            "type": "pii",
            "description": "Possible credit card number detected",
            "severity": "critical"
        })
    
    # --- Marketing Compliance ---
    
    # Promotional language without unsubscribe
    promo_keywords = ['discount', 'offer', 'deal', 'promotion', 'limited time', 
                      'act now', 'special price', 'sale', 'buy now', 'free trial']
    has_promo = any(kw.lower() in email_text.lower() for kw in promo_keywords)
    has_unsubscribe = 'unsubscribe' in email_text.lower()
    
    if has_promo and not has_unsubscribe:
        issues.append({
            "type": "marketing",
            "description": "Promotional content detected without unsubscribe option",
            "severity": "high"
        })
    
    # --- Legal Language Issues ---
    
    # Unapproved guarantees
    guarantee_keywords = ['guarantee', 'guaranteed', '100%', 'promise', 'assured']
    if any(kw.lower() in email_text.lower() for kw in guarantee_keywords):
        issues.append({
            "type": "legal",
            "description": "Unapproved guarantee or promise language detected",
            "severity": "medium"
        })
    
    # Missing disclaimer for advice
    advice_keywords = ['we recommend', 'you should', 'our advice', 'suggested action']
    if any(kw.lower() in email_text.lower() for kw in advice_keywords):
        if 'disclaimer' not in email_text.lower() and 'not financial advice' not in email_text.lower():
            issues.append({
                "type": "legal",
                "description": "Advisory language detected without appropriate disclaimer",
                "severity": "medium"
            })
    
    # --- Confidentiality Issues ---
    
    # Internal-only markers that shouldn't be in outbound emails
    confidential_markers = ['INTERNAL ONLY', 'CONFIDENTIAL', 'DO NOT DISTRIBUTE', 
                           'NOT FOR EXTERNAL', 'RESTRICTED', 'PRIVATE']
    for marker in confidential_markers:
        if marker.lower() in email_text.lower():
            issues.append({
                "type": "confidentiality",
                "description": f"Confidentiality marker '{marker}' found - should not be in outbound email",
                "severity": "critical"
            })
            break
    
    # Project codenames (common patterns)
    # Match "Project X" or "Operation X" where X is a proper noun (codename)
    # Exclude common generic words like Update, Status, Report, Plan, etc.
    codename_pattern = r'\b(?:Project|Operation)\s+([A-Z][a-z]+)\b'
    generic_words = {'update', 'status', 'report', 'plan', 'summary', 'overview', 
                     'meeting', 'review', 'proposal', 'timeline', 'progress'}
    codename_matches = re.findall(codename_pattern, email_text)
    suspicious_codenames = [c for c in codename_matches if c.lower() not in generic_words]
    if suspicious_codenames:
        issues.append({
            "type": "confidentiality", 
            "description": f"Possible internal project codename detected: {', '.join(suspicious_codenames)}",
            "severity": "medium"
        })
    
    # Internal system names
    internal_systems = ['jira', 'confluence', 'slack channel', 'internal wiki', 
                        'sharepoint', 'intranet']
    for system in internal_systems:
        if system.lower() in email_text.lower():
            issues.append({
                "type": "confidentiality",
                "description": f"Reference to internal system '{system}' detected",
                "severity": "low"
            })
            break
    
    return {
        "issues": issues,
        "pass": len(issues) == 0,
        "total_issues": len(issues),
        "summary": "Email passed compliance check" if len(issues) == 0 else f"Found {len(issues)} compliance issue(s)"
    }
