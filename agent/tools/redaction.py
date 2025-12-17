"""PII redaction tool for sanitizing email content."""

import re
from typing import Dict


def redact_pii(text: str) -> Dict[str, str]:
    """
    Automatically redact PII from text.
    
    IMPORTANT: Does NOT redact recipient information (names in greetings like "Dear Mr. X")
    since you're writing TO that person - their name is appropriate to include.
    
    Args:
        text: The text to redact
        
    Returns:
        Dict with 'redacted_text' and 'redactions_made' summary
    """
    redacted = text
    redactions = []
    
    # --- Identify recipient name in greeting (DO NOT redact) ---
    # Common greeting patterns: "Dear Mr. X", "Hi Mr. X", "Hello Ms. X"
    greeting_pattern = r'^(?:Dear|Hi|Hello|Hey)\s+(Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
    greeting_match = re.search(greeting_pattern, text, re.MULTILINE)
    recipient_name = greeting_match.group(0) if greeting_match else None
    
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
    
    # --- Names with titles (but NOT in greetings - those are recipients) ---
    # Only redact names that appear in contexts like "Account holder: Mr. X" or 
    # "I reviewed the account for Mr. X" - NOT "Dear Mr. X"
    name_pattern = r'\b(Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
    name_matches = list(re.finditer(name_pattern, redacted))
    
    for match in name_matches:
        original = match.group(0)
        
        # Skip if this is the recipient name in the greeting
        if recipient_name and original in recipient_name:
            continue
            
        # Check if this appears right after a greeting word (also skip)
        start_pos = match.start()
        prefix = redacted[max(0, start_pos-10):start_pos].lower()
        if any(g in prefix for g in ['dear ', 'hi ', 'hello ', 'hey ']):
            continue
        
        title = match.group(1)
        redacted = redacted.replace(original, f'{title} [REDACTED_NAME]', 1)
        redactions.append(f"Name with title: {original}")
    
    return {
        "redacted_text": redacted,
        "redactions_made": redactions,
        "count": len(redactions),
        "summary": f"Redacted {len(redactions)} PII item(s)" if redactions else "No PII found to redact"
    }
