"""PII redaction tool for sanitizing email content."""

import re
from typing import Dict


def redact_pii(text: str) -> Dict[str, str]:
    """
    Automatically redact PII from text.
    
    Args:
        text: The text to redact
        
    Returns:
        Dict with 'redacted_text' and 'redactions_made' summary
    """
    redacted = text
    redactions = []
    
    # --- Email addresses ---
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails_found = re.findall(email_pattern, redacted)
    # Keep corporate emails, redact external ones
    for email in emails_found:
        if not email.endswith(('@company.com', '@example.com')):
            redacted = redacted.replace(email, '[REDACTED_EMAIL]')
            redactions.append(f"Email: {email}")
    
    # --- Phone numbers ---
    # Matches various phone formats: (123) 456-7890, 123-456-7890, 123.456.7890, +1 123 456 7890
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
    phones_found = re.findall(phone_pattern, redacted)
    for phone in phones_found:
        redacted = redacted.replace(phone, '[REDACTED_PHONE]')
        redactions.append(f"Phone: {phone}")
    
    # --- SSN ---
    # Matches: 123-45-6789, 123 45 6789, 123.45.6789
    ssn_pattern = r'\b(\d{3})[-.\s]?(\d{2})[-.\s]?(\d{4})\b'
    ssn_matches = re.finditer(ssn_pattern, redacted)
    for match in ssn_matches:
        original = match.group(0)
        # Only redact if it looks like SSN (not phone or other number)
        # SSN: first 3 digits can't be 000, 666, or 900-999
        first_three = match.group(1)
        if first_three not in ['000', '666'] and not first_three.startswith('9'):
            redacted = redacted.replace(original, '[REDACTED_SSN]', 1)
            redactions.append(f"SSN: ***-**-{match.group(3)}")
    
    # --- Credit card numbers ---
    # Matches: 1234-5678-9012-3456, 1234 5678 9012 3456
    cc_pattern = r'\b(\d{4})[-.\s]?(\d{4})[-.\s]?(\d{4})[-.\s]?(\d{4})\b'
    cc_matches = re.finditer(cc_pattern, redacted)
    for match in cc_matches:
        original = match.group(0)
        last_four = match.group(4)
        redacted = redacted.replace(original, f'[REDACTED_CC_****{last_four}]', 1)
        redactions.append(f"Credit Card: ****-****-****-{last_four}")
    
    # --- Names (heuristic: Title Case names in certain contexts) ---
    # This is intentionally conservative - only catches "Mr./Ms./Mrs./Dr. Name"
    name_pattern = r'\b(Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
    name_matches = re.finditer(name_pattern, redacted)
    for match in name_matches:
        original = match.group(0)
        title = match.group(1)
        redacted = redacted.replace(original, f'{title} [REDACTED_NAME]', 1)
        redactions.append(f"Name with title: {original}")
    
    return {
        "redacted_text": redacted,
        "redactions_made": redactions,
        "count": len(redactions),
        "summary": f"Redacted {len(redactions)} PII item(s)" if redactions else "No PII found to redact"
    }
