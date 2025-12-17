/**
 * API Configuration & Functions
 * Connects to the FastAPI backend server
 */

const API = {
    BASE_URL: '/api',

    /**
     * Check email compliance
     * @param {string} emailText - The email body text to check
     * @returns {Promise<{issues: Array, pass: boolean}>}
     */
    async checkCompliance(emailText) {
        const response = await fetch(`${this.BASE_URL}/check-compliance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_text: emailText }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Get policy by category
     * @param {string} category - Policy category (pii, marketing, legal, confidentiality)
     * @returns {Promise<{category: string, title: string, content: string}>}
     */
    async getPolicy(category) {
        const response = await fetch(`${this.BASE_URL}/policy/${category}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Redact PII from text
     * @param {string} text - Text containing potential PII
     * @returns {Promise<{original: string, redacted: string, redactions: Array}>}
     */
    async redactPII(text) {
        const response = await fetch(`${this.BASE_URL}/redact-pii`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Simple rewrite (applies redaction)
     * @param {string} emailText - Original email text
     * @param {Array} issues - List of compliance issues to fix
     * @returns {Promise<{rewritten: string, changes: Array}>}
     */
    async rewriteEmail(emailText, issues) {
        const response = await fetch(`${this.BASE_URL}/rewrite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_text: emailText, issues }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Run the full agent with SSE streaming
     * @param {string} emailText - Email to review
     * @param {function} onEvent - Async callback for each event (will be awaited)
     * @returns {Promise<void>}
     */
    async runAgentStream(emailText, onEvent) {
        const response = await fetch(`${this.BASE_URL}/run-agent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_text: emailText }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        // IMPORTANT: Await the callback so UI updates before reading next event
                        await onEvent(data);
                    } catch (e) {
                        console.error('Failed to parse SSE data:', e);
                    }
                }
            }
        }
    },

    /**
     * Run the full agent synchronously (no streaming)
     * @param {string} emailText - Email to review
     * @returns {Promise<{final_email: string, passed: boolean, iterations: Array}>}
     */
    async runAgentSync(emailText) {
        const response = await fetch(`${this.BASE_URL}/run-agent-sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_text: emailText }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Health check
     * @returns {Promise<{status: string}>}
     */
    async healthCheck() {
        const response = await fetch(`${this.BASE_URL}/health`);
        return await response.json();
    }
};

// Export for module systems (optional)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
