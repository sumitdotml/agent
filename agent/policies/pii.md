# Data Protection & PII Policy (Fintech)

## Overview
Emails should not contain highly sensitive personal data in plain text. Claims about data use and privacy must be consistent with the company's privacy notice and applicable data protection laws.

## What Must Be Protected

### Critical PII (Never in Plain Text)
- Full payment card numbers
- Full government IDs (SSN, passport numbers)
- Passwords or security credentials
- Bank account numbers
- Full date of birth combined with other identifiers

### Sensitive PII (Requires Redaction or Consent)
- Email addresses (external/personal)
- Phone numbers
- Physical addresses
- Partial card numbers (more than last 4 digits)

## Compliance Checks

### Flag and Reject
- Any occurrence of full payment card numbers → Recommend removing or masking (show last 4 only)
- Any occurrence of passwords or full ID numbers → Must be removed
- Full SSN patterns (XXX-XX-XXXX) → Must be redacted

### Flag and Warn
- Statements that suggest selling or sharing customer data in ways inconsistent with privacy expectations
- Personal phone numbers without clear business purpose
- External email addresses (verify appropriateness)

## Remediation Actions
1. **Remove** - Delete PII entirely when not needed
2. **Mask** - Show partial data only (e.g., ****-****-****-1234 for cards)
3. **Replace** - Use reference IDs instead of personal details (e.g., "Case #12345" instead of customer name)
4. **Encrypt** - Use secure channels for necessary PII transmission

## Data Privacy Statements
- Do not claim data protection standards you don't meet
- Be accurate about how customer data is used
- Reference privacy policy for detailed information
