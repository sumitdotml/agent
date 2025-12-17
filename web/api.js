/**
 * API Configuration & Functions
 * Replace BASE_URL with your actual API endpoint
 */

const API = {
    BASE_URL: '/api', // Change this to your API base URL

    /**
     * Check email compliance
     * @param {string} emailText - The email body text to check
     * @returns {Promise<{issues: Array, pass: boolean}>}
     */
    async checkCompliance(emailText) {
        try {
            const response = await fetch(`${this.BASE_URL}/check-compliance`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email_text: emailText }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('checkCompliance error:', error);
            // Return mock data for development
            return this._mockCheckCompliance(emailText);
        }
    },

    /**
     * Get policy by category
     * @param {string} category - Policy category (pii, marketing, legal, confidentiality)
     * @returns {Promise<{category: string, content: string}>}
     */
    async getPolicy(category) {
        try {
            const response = await fetch(`${this.BASE_URL}/policy/${category}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('getPolicy error:', error);
            // Return mock data for development
            return this._mockGetPolicy(category);
        }
    },

    /**
     * Redact PII from text
     * @param {string} text - Text containing potential PII
     * @returns {Promise<{original: string, redacted: string, redactions: Array}>}
     */
    async redactPII(text) {
        try {
            const response = await fetch(`${this.BASE_URL}/redact-pii`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('redactPII error:', error);
            // Return mock data for development
            return this._mockRedactPII(text);
        }
    },

    /**
     * Rewrite email to fix compliance issues (calls the agent)
     * @param {string} emailText - Original email text
     * @param {Array} issues - List of compliance issues to fix
     * @returns {Promise<{rewritten: string, changes: Array}>}
     */
    async rewriteEmail(emailText, issues) {
        try {
            const response = await fetch(`${this.BASE_URL}/rewrite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email_text: emailText, issues }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('rewriteEmail error:', error);
            // Return mock data for development
            return this._mockRewriteEmail(emailText, issues);
        }
    },

    // ============================================
    // MOCK FUNCTIONS (for development/demo)
    // Remove these when connecting to real API
    // ============================================

    _mockCheckCompliance(emailText) {
        const issues = [];
        const text = emailText.toLowerCase();

        // Check for PII patterns
        const ssnPattern = /\b\d{3}[-.]?\d{2}[-.]?\d{4}\b/;
        const phonePattern = /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/;
        const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
        const creditCardPattern = /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/;

        if (ssnPattern.test(emailText)) {
            issues.push({
                type: 'pii',
                severity: 'critical',
                title: 'Social Security Number Detected',
                description: 'Email contains what appears to be an SSN. This must be removed or redacted.',
                category: 'pii'
            });
        }

        if (creditCardPattern.test(emailText)) {
            issues.push({
                type: 'pii',
                severity: 'critical',
                title: 'Credit Card Number Detected',
                description: 'Email contains what appears to be a credit card number. This must be removed or redacted.',
                category: 'pii'
            });
        }

        if (phonePattern.test(emailText)) {
            issues.push({
                type: 'pii',
                severity: 'warning',
                title: 'Phone Number Detected',
                description: 'Email contains a phone number. Verify this is appropriate to share.',
                category: 'pii'
            });
        }

        // Check for marketing language
        const marketingKeywords = ['guaranteed', 'free money', 'act now', 'limited time', 'winner', 'congratulations'];
        for (const keyword of marketingKeywords) {
            if (text.includes(keyword)) {
                issues.push({
                    type: 'marketing',
                    severity: 'warning',
                    title: 'Promotional Language Detected',
                    description: `The phrase "${keyword}" may violate marketing compliance guidelines.`,
                    category: 'marketing'
                });
                break;
            }
        }

        // Check for confidentiality markers
        const confidentialKeywords = ['confidential', 'internal only', 'do not share', 'proprietary'];
        for (const keyword of confidentialKeywords) {
            if (text.includes(keyword)) {
                issues.push({
                    type: 'confidentiality',
                    severity: 'warning',
                    title: 'Confidential Content Warning',
                    description: 'Email contains confidentiality markers. Ensure recipient is authorized.',
                    category: 'confidentiality'
                });
                break;
            }
        }

        // Check for legal terms
        const legalKeywords = ['lawsuit', 'attorney', 'legal action', 'sue', 'liability'];
        for (const keyword of legalKeywords) {
            if (text.includes(keyword)) {
                issues.push({
                    type: 'legal',
                    severity: 'warning',
                    title: 'Legal Content Detected',
                    description: 'Email contains legal terminology. Consider legal review before sending.',
                    category: 'legal'
                });
                break;
            }
        }

        return {
            issues,
            pass: issues.filter(i => i.severity === 'critical').length === 0
        };
    },

    _mockGetPolicy(category) {
        const policies = {
            pii: {
                category: 'pii',
                title: 'Personal Identifiable Information (PII) Policy',
                content: `PII Protection Policy:

1. Never include Social Security Numbers in external communications
2. Credit card numbers must be fully masked (show last 4 digits only)
3. Personal phone numbers require explicit consent before sharing
4. Email addresses may be shared for business purposes only
5. Home addresses should not be included in mass communications
6. Medical information requires HIPAA compliance verification
7. Financial account numbers must never be transmitted via email

Violations may result in regulatory fines and disciplinary action.`
            },
            marketing: {
                category: 'marketing',
                title: 'Marketing Communications Policy',
                content: `Marketing Compliance Guidelines:

1. Avoid spam trigger words: "free", "guaranteed", "act now", "winner"
2. All promotional claims must be verifiable
3. Include opt-out/unsubscribe option in all marketing emails
4. Do not use deceptive subject lines
5. CAN-SPAM Act compliance is mandatory
6. Include physical business address in marketing emails
7. Honor opt-out requests within 10 business days

Non-compliance may result in FTC penalties up to $46,517 per email.`
            },
            legal: {
                category: 'legal',
                title: 'Legal Communications Policy',
                content: `Legal Content Guidelines:

1. Do not make threats of legal action without Legal department approval
2. Avoid admitting liability or fault in written communications
3. Attorney-client privileged information requires proper markings
4. Settlement discussions must be approved by Legal
5. Do not discuss ongoing litigation with unauthorized parties
6. Contract terms should be reviewed by Legal before commitment
7. Regulatory inquiries should be escalated immediately

Contact legal@company.com for guidance on sensitive communications.`
            },
            confidentiality: {
                category: 'confidentiality',
                title: 'Confidentiality Policy',
                content: `Information Classification & Handling:

PUBLIC: May be shared freely
INTERNAL: Company employees only
CONFIDENTIAL: Need-to-know basis, NDA required for externals
RESTRICTED: Executive approval required for any sharing

Guidelines:
1. Verify recipient authorization before sharing confidential info
2. Use encryption for sensitive attachments
3. Include appropriate confidentiality notices
4. Do not forward confidential emails without approval
5. Report suspected data breaches immediately
6. Secure disposal of confidential printed materials required`
            }
        };

        return policies[category] || {
            category: category,
            title: 'Policy Not Found',
            content: 'No policy found for this category.'
        };
    },

    _mockRedactPII(text) {
        let redacted = text;
        const redactions = [];

        // Redact SSN
        const ssnPattern = /\b(\d{3})[-.]?(\d{2})[-.]?(\d{4})\b/g;
        redacted = redacted.replace(ssnPattern, (match) => {
            redactions.push({ type: 'SSN', original: match, replacement: '[SSN REDACTED]' });
            return '[SSN REDACTED]';
        });

        // Redact Credit Card
        const ccPattern = /\b(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})\b/g;
        redacted = redacted.replace(ccPattern, (match, p1, p2, p3, p4) => {
            const masked = `****-****-****-${p4}`;
            redactions.push({ type: 'Credit Card', original: match, replacement: masked });
            return masked;
        });

        // Redact Phone (partial - keep area code)
        const phonePattern = /\b(\d{3})[-.]?(\d{3})[-.]?(\d{4})\b/g;
        redacted = redacted.replace(phonePattern, (match, p1, p2, p3) => {
            const masked = `(${p1}) ***-${p3}`;
            redactions.push({ type: 'Phone', original: match, replacement: masked });
            return masked;
        });

        return {
            original: text,
            redacted,
            redactions
        };
    },

    _mockRewriteEmail(emailText, issues) {
        let rewritten = emailText;
        const changes = [];

        // Simple mock rewrites based on issue types
        for (const issue of issues) {
            if (issue.type === 'marketing') {
                const replacements = {
                    'guaranteed': 'expected',
                    'free money': 'potential savings',
                    'act now': 'at your convenience',
                    'limited time': 'current',
                    'winner': 'selected participant',
                    'congratulations': 'we are pleased to inform you'
                };

                for (const [original, replacement] of Object.entries(replacements)) {
                    const regex = new RegExp(original, 'gi');
                    if (regex.test(rewritten)) {
                        changes.push({ original, replacement, reason: 'Marketing compliance' });
                        rewritten = rewritten.replace(regex, replacement);
                    }
                }
            }
        }

        // Apply PII redaction
        const redactResult = this._mockRedactPII(rewritten);
        if (redactResult.redactions.length > 0) {
            rewritten = redactResult.redacted;
            changes.push(...redactResult.redactions.map(r => ({
                original: r.original,
                replacement: r.replacement,
                reason: `${r.type} redaction`
            })));
        }

        return {
            rewritten,
            changes
        };
    }
};

// Export for module systems (optional)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
