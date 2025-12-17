Below is a cleaned, link-free version you can drop into docs/fintech_email_compliance.md and commit.

Fintech Email Compliance Rules (v1)
1. Purpose and scope
This document defines the rules the AI agent must use when reviewing fintech-related emails (marketing, product, and service messages) for compliance issues and suggested improvements.
It focuses on communications that describe, offer, or encourage the use of financial products or services (for example: payments, cards, loans, savings, investments, wallets) sent to consumers or small businesses.

2. Email classification
Before applying rules, the agent MUST classify each email.

Audience

retail: consumers or small businesses, or any distribution list with more than 25 recipients.

professional: institutional or expert counterparties.

Purpose

service: operational updates, account changes, incident notices.

marketing: brand, campaigns, offers, newsletters.

financial_promotion: any email that invites or induces a person to buy, subscribe to, or use a financial product or service.

If purpose is marketing or financial_promotion AND audience is retail, the agent MUST apply all rules in sections 3–6.

3. Fair, clear, and not misleading
3.1 Truthful, evidence-based statements
All statements about pricing, returns, fees, and benefits must be accurate and not exaggerated.

Performance claims and promises must be consistent with internal data and applicable marketing rules.

Agent checks / flags

Flag phrases such as “guaranteed returns”, “risk-free”, “no downside”, “always approved”, “everyone qualifies”, unless explicitly backed by clear terms in the same email.

Flag if performance, savings, or return figures appear with no nearby statement of limitations or risk.

Suggest adding short qualifiers such as: “Actual results may vary. Eligibility, fees, and terms apply.”

3.2 Balanced presentation of benefits and risks
Benefits must not be overemphasised while risks, fees, or limitations are hidden or hard to notice.

Key risks and conditions should appear in the main body or near the claim, not only in dense legal footer text.

Agent checks / flags

Flag if the email describes strong upside (for example: “boost your returns”, “pay off debt faster”, “earn more on your savings”) with no mention of relevant risks, fees, or eligibility criteria.

Suggest inserting a short, plain-language risk or conditions sentence near each promotional claim.

3.3 Clarity and appropriate language
Language must be clear, plain, and suitable for the intended audience, especially for retail customers.

Complex products (for example: crypto, derivatives, leveraged trading) must not be described in a way that an average retail user could easily misunderstand.

Agent checks / flags

Flag jargon-heavy descriptions with no explanation (for example: “delta-neutral yield farming strategy”, “leveraged structured note”) for retail audiences.

Suggest replacing or supplementing jargon with a short, simple explanation of what the product does and what could go wrong.

4. Grey-area patterns (warn and improve)
These cases are not automatically non-compliant but need extra care; the agent should add warnings and propose edits rather than outright rejection.

4.1 Educational content plus subtle promotion
Articles, “tips”, or guides that also steer readers towards a product are acceptable only if education and promotion are clearly separated.

Agent behaviour

If the email contains financial tips AND a call-to-action for a specific product, suggest:

A distinct section heading for the promotional part, such as “How our product can help”.

A short, honest explanation of what the product does, plus its main risks or limitations.

4.2 Mixed regulated and unregulated offerings
If the email mentions both regulated products (for example: bank accounts, e-money, lending) and unregulated offerings (for example: budgeting tools, some crypto), it must not imply all are regulated or guaranteed.

Agent behaviour

Flag if the email highlights regulatory status (for example: “regulated”, “insured”, “authorised by X”) but also promotes features that may not be covered by that status.

Suggest clarifying which parts are regulated and which are not, such as: “Our deposit accounts are regulated products; our budgeting tools are not bank products.”

4.3 Testimonials, reviews, and social proof
Testimonials and ratings must not be presented in a misleading way or imply guaranteed outcomes.

Agent behaviour

Flag if testimonials imply certainty (for example: “I doubled my money with no risk”) or omit material context.

Suggest adding context, such as: “Individual results vary and are not guaranteed.”

5. Generic email and marketing requirements
These rules apply to all outbound marketing and promotional emails.

5.1 Sender identity and subject line
The “From” name and email address must honestly represent the sending organisation.

The subject line must not be deceptive or materially inconsistent with the email content.

Agent checks / flags

Flag subject lines that claim something not explained or delivered in the body (for example: “Your account is suspended” for a pure marketing campaign).

Flag subject lines promising specific returns or features that are missing or heavily qualified in the body.

5.2 Unsubscribe and opt-out
Every marketing or financial promotion email must include a clear, easy-to-use unsubscribe or preference link.

Opt-out instructions must be reasonably visible and functional.

Agent checks / flags

Flag if no unsubscribe link or equivalent wording (“unsubscribe”, “manage preferences”) is present.

Suggest inserting a standard line, for example: “If you no longer wish to receive these emails, you can unsubscribe here: [link].”

5.3 Identification and contact information
The email should include the legal name of the sending entity and a physical mailing address, or the equivalent required in the relevant jurisdiction.

Where appropriate, include high-level regulatory or registration information in the footer.

Agent checks / flags

Flag if neither company name nor postal address appears anywhere in the email.

Suggest adding a footer with entity name, address, and, if appropriate, registration or licence references.

6. Data protection and security basics
Emails should not contain highly sensitive personal data in plain text (for example: full payment card numbers, full government IDs, passwords).

Claims about data use and privacy must be consistent with the company’s privacy notice and applicable data protection laws.

Agent checks / flags

Flag any occurrence of full payment card numbers, passwords, or full ID numbers and recommend removing or masking.

Flag statements that suggest selling or sharing customer data in ways that appear inconsistent with typical privacy expectations.

7. Ownership, approval, and logging
Each financial promotion should have an identifiable owner responsible for its content.

A designated approved person (for example: compliance or legal) should sign off material aimed at retail audiences, especially for higher-risk products.

Agent behaviour

For every email, the agent should output:

A list of triggered rules and suggested fixes.

A final status: OK, OK with minor issues, or High-risk issues – escalate to human review.
