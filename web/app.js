/**
 * Outbound Email Guard - Main Application
 */

class EmailGuard {
    constructor() {
        this.maxIterations = 5;
        this.currentIteration = 0;
        this.history = [];

        // DOM Elements
        this.elements = {
            emailTo: document.getElementById('email-to'),
            emailSubject: document.getElementById('email-subject'),
            emailBody: document.getElementById('email-body'),
            checkBtn: document.getElementById('check-btn'),
            btnText: document.querySelector('.btn-text'),
            btnLoader: document.querySelector('.btn-loader'),
            statusSection: document.getElementById('status-section'),
            statusTimeline: document.getElementById('status-timeline'),
            issuesSection: document.getElementById('issues-section'),
            issuesList: document.getElementById('issues-list'),
            issuesCount: document.getElementById('issues-count'),
            issuesIcon: document.getElementById('issues-icon'),
            policySection: document.getElementById('policy-section'),
            policyTabs: document.getElementById('policy-tabs'),
            policyContent: document.getElementById('policy-content'),
            resultSection: document.getElementById('result-section'),
            resultTitle: document.getElementById('result-title'),
            resultBadge: document.getElementById('result-badge'),
            resultTo: document.getElementById('result-to'),
            resultSubject: document.getElementById('result-subject'),
            resultBody: document.getElementById('result-body'),
            copyBtn: document.getElementById('copy-btn'),
            useBtn: document.getElementById('use-btn'),
            historySection: document.getElementById('history-section'),
            historyList: document.getElementById('history-list'),
        };

        this.init();
    }

    init() {
        // Event Listeners
        this.elements.checkBtn.addEventListener('click', () => this.startComplianceCheck());
        this.elements.copyBtn.addEventListener('click', () => this.copyToClipboard());
        this.elements.useBtn.addEventListener('click', () => this.useCompliantVersion());

        // Demo data (optional - remove in production)
        this.loadDemoData();
    }

    loadDemoData() {
        // Pre-fill with demo data for testing
        this.elements.emailTo.value = 'client@example.com';
        this.elements.emailSubject.value = 'Your Account Update - Act Now!';
        this.elements.emailBody.value = `Dear Customer,

Congratulations! You've been selected as a winner in our promotion.

Your account details:
- SSN: 123-45-6789
- Card: 4111-2222-3333-4444
- Phone: 555-123-4567

This is a limited time offer - act now to claim your free money!

This information is confidential and internal only.

Best regards,
Sales Team`;
    }

    async startComplianceCheck() {
        this.setLoading(true);
        this.resetUI();
        this.currentIteration = 0;
        this.history = [];

        const emailText = this.elements.emailBody.value;

        this.showSection('statusSection');
        this.addStatus('Starting compliance check...', 'active');

        await this.complianceLoop(emailText);
    }

    async complianceLoop(emailText) {
        this.currentIteration++;

        if (this.currentIteration > this.maxIterations) {
            this.addStatus('Maximum iterations reached. Manual review required.', 'error');
            this.showFinalResult(emailText, false);
            this.setLoading(false);
            return;
        }

        // Step 1: Check compliance
        this.updateLastStatus(`Iteration ${this.currentIteration}: Checking compliance...`, 'active');
        await this.delay(500);

        const complianceResult = await API.checkCompliance(emailText);

        // Add to history
        this.history.push({
            iteration: this.currentIteration,
            text: emailText,
            issues: complianceResult.issues,
            pass: complianceResult.pass
        });

        this.updateHistory();

        if (complianceResult.pass && complianceResult.issues.length === 0) {
            // All clear!
            this.addStatus('Compliance check passed!', 'completed');
            this.showFinalResult(emailText, true);
            this.setLoading(false);
            return;
        }

        // Show issues
        this.showIssues(complianceResult.issues);
        this.addStatus(`Found ${complianceResult.issues.length} issue(s)`, 'completed');

        // Step 2: Fetch relevant policies
        const categories = [...new Set(complianceResult.issues.map(i => i.category))];
        this.addStatus('Fetching relevant policies...', 'active');
        await this.delay(300);

        const policies = await Promise.all(categories.map(cat => API.getPolicy(cat)));
        this.showPolicies(policies);
        this.updateLastStatus(`Loaded ${policies.length} policy document(s)`, 'completed');

        // Step 3: Rewrite email
        this.addStatus('Rewriting email for compliance...', 'active');
        await this.delay(500);

        const rewriteResult = await API.rewriteEmail(emailText, complianceResult.issues);
        this.updateLastStatus(`Applied ${rewriteResult.changes.length} change(s)`, 'completed');

        // Step 4: Redact PII
        this.addStatus('Redacting sensitive information...', 'active');
        await this.delay(300);

        const redactResult = await API.redactPII(rewriteResult.rewritten);
        this.updateLastStatus(`Redacted ${redactResult.redactions.length} item(s)`, 'completed');

        // Step 5: Re-check (recursive loop)
        this.addStatus('Re-checking compliance...', 'active');
        await this.delay(300);

        await this.complianceLoop(redactResult.redacted);
    }

    showIssues(issues) {
        this.showSection('issuesSection');

        const criticalCount = issues.filter(i => i.severity === 'critical').length;
        const totalCount = issues.length;

        this.elements.issuesCount.textContent = totalCount;
        this.elements.issuesCount.className = criticalCount > 0 ? 'badge' : 'badge success';
        this.elements.issuesIcon.textContent = criticalCount > 0 ? '🚨' : '⚠️';

        this.elements.issuesList.innerHTML = issues.map(issue => `
            <li class="issue-item ${issue.severity === 'critical' ? 'critical' : ''}">
                <span class="issue-icon">${issue.severity === 'critical' ? '🚨' : '⚠️'}</span>
                <div class="issue-content">
                    <div class="issue-title">${this.escapeHtml(issue.title)}</div>
                    <div class="issue-description">${this.escapeHtml(issue.description)}</div>
                    <span class="issue-category">${this.escapeHtml(issue.category)}</span>
                </div>
            </li>
        `).join('');
    }

    showPolicies(policies) {
        this.showSection('policySection');

        // Create tabs
        this.elements.policyTabs.innerHTML = policies.map((policy, index) => `
            <button class="policy-tab ${index === 0 ? 'active' : ''}"
                    data-category="${policy.category}"
                    onclick="app.selectPolicy('${policy.category}')">
                ${this.escapeHtml(policy.title || policy.category)}
            </button>
        `).join('');

        // Store policies for tab switching
        this.policies = policies;

        // Show first policy
        if (policies.length > 0) {
            this.elements.policyContent.textContent = policies[0].content;
        }
    }

    selectPolicy(category) {
        // Update active tab
        document.querySelectorAll('.policy-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.category === category);
        });

        // Show policy content
        const policy = this.policies.find(p => p.category === category);
        if (policy) {
            this.elements.policyContent.textContent = policy.content;
        }
    }

    showFinalResult(emailText, passed) {
        this.showSection('resultSection');

        this.elements.resultTitle.textContent = passed ? 'Compliant Email' : 'Review Required';
        this.elements.resultBadge.textContent = passed ? 'Passed' : 'Needs Review';
        this.elements.resultBadge.className = `status-badge ${passed ? 'passed' : 'failed'}`;

        this.elements.resultTo.value = this.elements.emailTo.value;
        this.elements.resultSubject.value = this.elements.emailSubject.value;
        this.elements.resultBody.value = emailText;

        // Update issues section to show success
        if (passed) {
            this.elements.issuesIcon.textContent = '✅';
            this.elements.issuesSection.querySelector('h2').innerHTML = `
                <span id="issues-icon">✅</span>
                No Compliance Issues
            `;
            this.elements.issuesList.innerHTML = `
                <li class="issue-item" style="border-left-color: var(--success);">
                    <span class="issue-icon">✅</span>
                    <div class="issue-content">
                        <div class="issue-title">All Clear</div>
                        <div class="issue-description">Email passed all compliance checks and is safe to send.</div>
                    </div>
                </li>
            `;
        }
    }

    updateHistory() {
        this.showSection('historySection');

        this.elements.historyList.innerHTML = this.history.map((item, index) => `
            <div class="history-item">
                <div class="history-item-header">
                    <span class="history-item-title">Iteration ${item.iteration}</span>
                    <span class="history-item-badge ${item.pass ? 'pass' : 'fail'}">
                        ${item.issues.length} issue(s)
                    </span>
                </div>
                <div class="history-item-preview">${this.escapeHtml(item.text.substring(0, 100))}...</div>
            </div>
        `).join('');
    }

    addStatus(message, state = 'pending') {
        const statusItem = document.createElement('div');
        statusItem.className = `status-item ${state}`;
        statusItem.innerHTML = `
            <span class="status-message">${this.escapeHtml(message)}</span>
            <span class="status-time">${this.getTimeString()}</span>
        `;
        this.elements.statusTimeline.appendChild(statusItem);

        // Scroll to latest status
        statusItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    updateLastStatus(message, state) {
        const lastItem = this.elements.statusTimeline.lastElementChild;
        if (lastItem) {
            lastItem.className = `status-item ${state}`;
            lastItem.querySelector('.status-message').textContent = message;
        }
    }

    async copyToClipboard() {
        const text = `To: ${this.elements.resultTo.value}
Subject: ${this.elements.resultSubject.value}

${this.elements.resultBody.value}`;

        try {
            await navigator.clipboard.writeText(text);
            const originalText = this.elements.copyBtn.textContent;
            this.elements.copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                this.elements.copyBtn.textContent = originalText;
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    }

    useCompliantVersion() {
        this.elements.emailTo.value = this.elements.resultTo.value;
        this.elements.emailSubject.value = this.elements.resultSubject.value;
        this.elements.emailBody.value = this.elements.resultBody.value;

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Flash the email input section
        const emailSection = document.querySelector('.email-input-section');
        emailSection.style.boxShadow = '0 0 0 3px var(--success)';
        setTimeout(() => {
            emailSection.style.boxShadow = '';
        }, 1500);
    }

    showSection(sectionId) {
        this.elements[sectionId].classList.remove('hidden');
    }

    hideSection(sectionId) {
        this.elements[sectionId].classList.add('hidden');
    }

    resetUI() {
        // Hide all result sections
        ['statusSection', 'issuesSection', 'policySection', 'resultSection', 'historySection']
            .forEach(id => this.hideSection(id));

        // Clear status timeline
        this.elements.statusTimeline.innerHTML = '';
    }

    setLoading(loading) {
        this.elements.checkBtn.disabled = loading;
        this.elements.btnText.classList.toggle('hidden', loading);
        this.elements.btnLoader.classList.toggle('hidden', !loading);
    }

    getTimeString() {
        return new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize app when DOM is ready
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new EmailGuard();
});
