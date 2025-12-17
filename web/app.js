/**
 * Outbound Email Guard - Main Application
 * Progressive streaming UI for a natural, agentic experience
 */

class EmailGuard {
    constructor() {
        this.maxIterations = 5;
        this.currentIteration = 0;
        this.history = [];
        this.issues = [];
        this.policies = [];
        this.currentEmailDraft = '';
        this.issueHistory = []; // Track issue counts per iteration: [7, 3, 0]

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
            // Progress panel elements
            agentProgress: document.getElementById('agent-progress'),
            currentIter: document.getElementById('current-iter'),
            progressBar: document.getElementById('progress-bar'),
            progressStatus: document.getElementById('progress-status'),
            progressIssues: document.getElementById('progress-issues'),
        };

        this.init();
    }

    init() {
        this.elements.checkBtn.addEventListener('click', () => this.startComplianceCheck());
        this.elements.copyBtn.addEventListener('click', () => this.copyToClipboard());
        this.elements.useBtn.addEventListener('click', () => this.useCompliantVersion());
        this.loadDemoData();
        this.checkApiHealth();
    }

    async checkApiHealth() {
        try {
            await API.healthCheck();
            console.log('API server is healthy');
        } catch (e) {
            console.warn('API server not available, some features may not work');
        }
    }

    loadDemoData() {
        this.elements.emailTo.value = 'customer@example.com';
        this.elements.emailSubject.value = 'Exclusive Investment Opportunity - Act Now!';
        this.elements.emailBody.value = `Subject: Special Offer for Mr. James Wilson

CONFIDENTIAL

Dear Mr. James Wilson,

We guarantee you'll love our new service! As a valued customer, we're offering you an exclusive deal.

Your account details:
- Email: james.wilson@personalmail.com  
- Phone: 555-987-6543
- Account ID: Based on SSN 321-54-9876

For a limited time, we're offering 30% off on all services. We recommend you sign up today before this offer expires!

As discussed internally on our Jira board, Project Moonshot is launching soon and you'll be among the first to know.

Our advice: Act now to secure your spot!

Best regards,
Marketing Team`;
    }

    async startComplianceCheck() {
        this.setLoading(true);
        this.resetUI();
        this.currentIteration = 0;
        this.history = [];
        this.issues = [];
        this.policies = [];
        this.currentEmailDraft = this.elements.emailBody.value;
        this.issueHistory = [];

        this.showSection('statusSection');
        this.updateProgressPanel(0, 'Starting...', null);
        await this.addStatusAnimated('Starting compliance review...', 'active');

        await this.runAgentWithStreaming(this.currentEmailDraft);
    }

    /**
     * Run agent with SSE streaming - handles granular progressive events
     */
    async runAgentWithStreaming(emailText) {
        let finalEmail = emailText;

        try {
            // The API now awaits each event callback, so events are processed in order
            await API.runAgentStream(emailText, async (event) => {
                console.log('SSE Event:', event.type, event);

                // Handle the event and update UI
                await this.handleProgressiveEvent(event, (email) => {
                    finalEmail = email;
                });
            });

            // Final check and display
            const finalCheck = await API.checkCompliance(finalEmail);
            this.showFinalResult(finalEmail, finalCheck.pass, this.currentIteration);

        } catch (error) {
            console.error('Agent error:', error);
            await this.addStatusAnimated(`Error: ${error.message}`, 'error');
        }

        this.setLoading(false);
    }

    /**
     * Handle each progressive SSE event with appropriate animations
     */
    async handleProgressiveEvent(event, onComplete) {
        switch (event.type) {
            case 'start':
                await this.addStatusAnimated('Processing email...', 'completed');
                break;

            case 'iteration_start':
                this.currentIteration = event.iteration;
                this.updateProgressPanel(event.iteration, 'Analyzing...', null);
                await this.addStatusAnimated(`--- Iteration ${event.iteration} ---`, 'active', 'iteration-marker');
                // Clear previous issues for new iteration (fresh check)
                this.issues = [];
                this.elements.issuesList.innerHTML = '';
                // Add to history
                this.addHistoryEntry(event.iteration, 'starting', 'Starting analysis...');
                break;

            case 'thinking':
                await this.updateLastStatusAnimated(`Thinking: ${event.thought}`, 'active');
                break;

            case 'tool_selected':
                const toolEmoji = this.getToolEmoji(event.tool_name);
                if (event.tool_name === 'check_compliance') {
                    this.updateProgressPanel(this.currentIteration, 'Checking compliance...', null, 'checking');
                }
                await this.addStatusAnimated(`${toolEmoji} Using ${this.formatToolName(event.tool_name)}...`, 'active');
                break;

            case 'tool_executing':
                await this.addStatusAnimated('Executing...', 'active', 'pulse');
                break;

            case 'compliance_check_started':
                await this.updateLastStatusAnimated('Scanning for compliance issues...', 'active');
                // Prepare issues section (but keep it empty)
                this.showSection('issuesSection');
                this.elements.issuesList.innerHTML = '';
                this.elements.issuesCount.textContent = '...';
                break;

            case 'issues_found':
                await this.updateLastStatusAnimated(`Found ${event.total_count} potential issue(s)`, 'warning');
                this.elements.issuesCount.textContent = event.total_count;
                this.elements.issuesCount.className = 'badge';
                this.elements.issuesIcon.textContent = '🔍';
                break;

            case 'issue':
                // Add issue progressively with animation
                await this.addIssueAnimated(event.issue, event.index, event.total);
                break;

            case 'compliance_result':
                const statusText = event.pass
                    ? 'Compliance check PASSED'
                    : `Compliance check: ${event.issues_count} issue(s) to fix`;
                const statusClass = event.pass ? 'completed' : 'warning';
                await this.addStatusAnimated(statusText, statusClass);

                // Track issues for progress panel
                this.issueHistory.push(event.issues_count);
                const progressStatusText = event.pass ? 'Passed!' : `Found ${event.issues_count} issues`;
                const progressStatusClass = event.pass ? 'complete' : 'failed';
                this.updateProgressPanel(this.currentIteration, progressStatusText, event.issues_count, progressStatusClass);

                // Update history entry
                this.updateHistoryEntry(this.currentIteration,
                    event.pass ? 'pass' : 'issues',
                    event.pass ? 'Passed all checks' : `${event.issues_count} issue(s) found`
                );
                break;

            case 'policy_loaded':
                await this.addStatusAnimated('Policy reference loaded', 'completed');
                // Fetch and display the policy progressively
                await this.loadPoliciesForCurrentIssues();
                break;

            case 'redaction_started':
                await this.addStatusAnimated('Redacting sensitive information...', 'active');
                break;

            case 'redaction_item':
                // Could show each redaction but might be too verbose
                break;

            case 'redaction_complete':
                await this.updateLastStatusAnimated(`Redacted ${event.count} sensitive item(s)`, 'completed');
                break;

            case 'rewrite_start':
                await this.addStatusAnimated('Preparing to rewrite email...', 'active');
                break;

            case 'rewriting':
                this.updateProgressPanel(this.currentIteration, 'Rewriting email...', null, 'rewriting');
                await this.updateLastStatusAnimated('Rewriting email to fix issues...', 'active');
                break;

            case 'rewrite_complete':
                this.currentEmailDraft = event.full_text;
                await this.addStatusAnimated('Email rewritten successfully', 'completed');
                this.updateHistoryEntry(this.currentIteration, 'rewrite', 'Email revised');

                // Add new history entry showing the rewrite
                this.addHistoryEntry(this.currentIteration, 'rewrite', event.preview);
                break;

            case 'finalizing':
                await this.addStatusAnimated('Running final compliance check...', 'active');
                break;

            case 'final_check':
                await this.addStatusAnimated('Verifying final email...', 'active');
                break;

            case 'complete':
                if (event.final_email) {
                    onComplete(event.final_email);
                }
                if (event.iteration) {
                    this.currentIteration = event.iteration;
                }
                this.updateProgressPanel(this.currentIteration, 'Complete!', 0, 'complete');
                await this.addStatusAnimated(`Review complete! (${this.currentIteration} iteration${this.currentIteration > 1 ? 's' : ''})`, 'completed');
                break;

            case 'error':
                await this.addStatusAnimated(`Error: ${event.message}`, 'error');
                break;

            case 'done':
                // Stream finished
                break;

            default:
                console.log('Unknown event type:', event.type, event);
        }
    }

    /**
     * Update the progress panel with current iteration state
     */
    updateProgressPanel(iteration, status, issueCount, statusClass = '') {
        // Update iteration number
        this.elements.currentIter.textContent = iteration || 1;

        // Update progress bar (percentage based on iteration)
        const percentage = Math.min((iteration / this.maxIterations) * 100, 100);
        this.elements.progressBar.style.width = `${percentage}%`;

        // Update status text and class
        this.elements.progressStatus.textContent = status;
        this.elements.progressStatus.className = `progress-status ${statusClass}`;

        // Update issue history trail
        this.renderIssueTrail();
    }

    /**
     * Render the issue count trail (e.g., "7 → 3 → 0")
     */
    renderIssueTrail() {
        if (this.issueHistory.length === 0) {
            this.elements.progressIssues.textContent = '-';
            return;
        }

        const trailHtml = this.issueHistory.map((count, idx) => {
            const isLast = idx === this.issueHistory.length - 1;
            const colorClass = count === 0 ? 'count-pass' : 'count-fail';
            return `<span class="${colorClass}">${count}</span>`;
        }).join('<span class="arrow">→</span>');

        this.elements.progressIssues.innerHTML = trailHtml;
    }

    /**
     * Add a status item with typing animation
     */
    async addStatusAnimated(message, state = 'pending', extraClass = '') {
        const statusItem = document.createElement('div');
        statusItem.className = `status-item ${state} ${extraClass} fade-in`;
        statusItem.innerHTML = `
            <span class="status-message"></span>
            <span class="status-time">${this.getTimeString()}</span>
        `;
        this.elements.statusTimeline.appendChild(statusItem);
        statusItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Typing effect
        const messageEl = statusItem.querySelector('.status-message');
        await this.typeText(messageEl, message, 15);

        return statusItem;
    }

    /**
     * Update the last status item with animation
     */
    async updateLastStatusAnimated(message, state) {
        const lastItem = this.elements.statusTimeline.lastElementChild;
        if (lastItem) {
            lastItem.className = `status-item ${state}`;
            const messageEl = lastItem.querySelector('.status-message');
            messageEl.textContent = '';
            await this.typeText(messageEl, message, 10);
        }
    }

    /**
     * Type text character by character
     */
    async typeText(element, text, delay = 20) {
        for (let i = 0; i < text.length; i++) {
            element.textContent += text[i];
            if (delay > 0 && i % 3 === 0) { // Type 3 chars at a time for speed
                await this.delay(delay);
            }
        }
    }

    /**
     * Add an issue with slide-in animation
     */
    async addIssueAnimated(issue, index, total) {
        this.issues.push(issue);

        const issueItem = document.createElement('li');
        issueItem.className = `issue-item ${issue.severity === 'critical' ? 'critical' : ''} slide-in`;
        issueItem.style.animationDelay = `${index * 0.05}s`;

        issueItem.innerHTML = `
            <span class="issue-icon">${issue.severity === 'critical' ? '🚨' : '⚠️'}</span>
            <div class="issue-content">
                <div class="issue-title">${this.escapeHtml(issue.title || issue.type)}</div>
                <div class="issue-description">${this.escapeHtml(issue.description)}</div>
                <span class="issue-category">${this.escapeHtml(issue.category || issue.type)}</span>
            </div>
        `;

        this.elements.issuesList.appendChild(issueItem);

        // Update counter
        this.elements.issuesCount.textContent = this.issues.length;
        const criticalCount = this.issues.filter(i => i.severity === 'critical').length;
        this.elements.issuesIcon.textContent = criticalCount > 0 ? '🚨' : '⚠️';

        // Small delay for staggered effect
        await this.delay(50);
    }

    /**
     * Load policies progressively for found issues
     */
    async loadPoliciesForCurrentIssues() {
        if (this.issues.length === 0) return;

        const categories = [...new Set(this.issues.map(i => i.category))];
        this.showSection('policySection');

        for (const category of categories) {
            try {
                const policy = await API.getPolicy(category);
                this.policies.push(policy);
                this.updatePolicyTabs();
                await this.delay(100);
            } catch (e) {
                console.error('Failed to load policy:', category, e);
            }
        }
    }

    updatePolicyTabs() {
        this.elements.policyTabs.innerHTML = this.policies.map((policy, index) => `
            <button class="policy-tab ${index === 0 ? 'active' : ''}"
                    data-category="${policy.category}"
                    onclick="app.selectPolicy('${policy.category}')">
                ${this.escapeHtml(policy.title || policy.category)}
            </button>
        `).join('');

        if (this.policies.length > 0) {
            this.elements.policyContent.textContent = this.policies[0].content;
        }
    }

    selectPolicy(category) {
        document.querySelectorAll('.policy-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.category === category);
        });

        const policy = this.policies.find(p => p.category === category);
        if (policy) {
            this.elements.policyContent.textContent = policy.content;
        }
    }

    /**
     * Add history entry progressively
     */
    addHistoryEntry(iteration, status, text) {
        this.showSection('historySection');

        const existingEntry = this.elements.historyList.querySelector(`[data-iteration="${iteration}"]`);
        if (existingEntry) {
            // Update existing entry
            const badge = existingEntry.querySelector('.history-item-badge');
            const preview = existingEntry.querySelector('.history-item-preview');
            badge.className = `history-item-badge ${status}`;
            badge.textContent = this.getStatusLabel(status);
            preview.textContent = text.substring(0, 100) + (text.length > 100 ? '...' : '');
            return;
        }

        const historyItem = document.createElement('div');
        historyItem.className = 'history-item fade-in';
        historyItem.dataset.iteration = iteration;
        historyItem.innerHTML = `
            <div class="history-item-header">
                <span class="history-item-title">Iteration ${iteration}</span>
                <span class="history-item-badge ${status}">${this.getStatusLabel(status)}</span>
            </div>
            <div class="history-item-preview">${this.escapeHtml(text.substring(0, 100))}${text.length > 100 ? '...' : ''}</div>
        `;

        this.elements.historyList.appendChild(historyItem);
    }

    updateHistoryEntry(iteration, status, text) {
        const entry = this.elements.historyList.querySelector(`[data-iteration="${iteration}"]`);
        if (entry) {
            const badge = entry.querySelector('.history-item-badge');
            const preview = entry.querySelector('.history-item-preview');
            badge.className = `history-item-badge ${status}`;
            badge.textContent = this.getStatusLabel(status);
            if (text) {
                preview.textContent = text.substring(0, 100) + (text.length > 100 ? '...' : '');
            }
        }
    }

    getStatusLabel(status) {
        const labels = {
            'starting': 'Starting...',
            'issues': 'Issues Found',
            'pass': 'Passed',
            'rewrite': 'Rewritten',
            'fail': 'Failed'
        };
        return labels[status] || status;
    }

    showFinalResult(emailText, passed, finalIteration = null) {
        this.showSection('resultSection');

        const iterInfo = finalIteration ? ` (Iteration ${finalIteration})` : '';

        if (passed) {
            this.elements.resultTitle.textContent = `Compliant Email${iterInfo}`;
            this.elements.resultBadge.textContent = 'PASSED';
            this.elements.resultBadge.className = 'status-badge passed';
        } else {
            this.elements.resultTitle.textContent = `Best Effort${iterInfo}`;
            this.elements.resultBadge.textContent = 'NEEDS REVIEW';
            this.elements.resultBadge.className = 'status-badge failed';
        }

        this.elements.resultTo.value = this.elements.emailTo.value;
        this.elements.resultSubject.value = this.elements.emailSubject.value;
        this.elements.resultBody.value = emailText;

        if (passed) {
            this.showSection('issuesSection');
            this.elements.issuesIcon.textContent = '✅';
            this.elements.issuesCount.textContent = '0';
            this.elements.issuesCount.className = 'badge success';
            this.elements.issuesList.innerHTML = `
                <li class="issue-item" style="border-left-color: var(--success);">
                    <span class="issue-icon">✅</span>
                    <div class="issue-content">
                        <div class="issue-title">All Clear</div>
                        <div class="issue-description">Email passed all compliance checks after ${this.currentIteration} iteration(s) and is safe to send.</div>
                    </div>
                </li>
            `;
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

        window.scrollTo({ top: 0, behavior: 'smooth' });

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
        ['statusSection', 'issuesSection', 'policySection', 'resultSection', 'historySection']
            .forEach(id => this.hideSection(id));

        this.elements.statusTimeline.innerHTML = '';
        this.elements.issuesIcon.textContent = '⚠️';
        this.elements.issuesCount.textContent = '0';
        this.elements.issuesCount.className = 'badge';
        this.elements.issuesList.innerHTML = '';
        this.elements.historyList.innerHTML = '';
        this.elements.policyTabs.innerHTML = '';
        this.elements.policyContent.textContent = '';

        // Reset progress panel
        this.elements.currentIter.textContent = '1';
        this.elements.progressBar.style.width = '0%';
        this.elements.progressStatus.textContent = 'Starting...';
        this.elements.progressStatus.className = 'progress-status';
        this.elements.progressIssues.textContent = '-';
    }

    setLoading(loading) {
        this.elements.checkBtn.disabled = loading;
        this.elements.btnText.classList.toggle('hidden', loading);
        this.elements.btnLoader.classList.toggle('hidden', !loading);
    }

    getToolEmoji(toolName) {
        const emojis = {
            'check_compliance': '🔍',
            'get_policy': '📋',
            'redact_pii': '🔒'
        };
        return emojis[toolName] || '🔧';
    }

    formatToolName(toolName) {
        const names = {
            'check_compliance': 'Compliance Checker',
            'get_policy': 'Policy Lookup',
            'redact_pii': 'PII Redactor'
        };
        return names[toolName] || toolName;
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
        div.textContent = text || '';
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
