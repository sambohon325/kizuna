# Kizuna AI operations system

Kizuna's operating goal is low-touch administration, not unbounded autonomy. Routine work should be completed by specialized agents. Rare decisions involving money, identity, safety, rights, irreversible changes, or public claims should arrive as a short decision brief with a prepared response.

## Operating model

### Support Concierge

Implemented in the marketing service. It:

- classifies and prioritizes every new ticket;
- summarizes the request without exposing the requester's email to the AI provider;
- detects account, billing, security, legal, deletion, safety, and data-loss language;
- prepares a customer-safe response;
- records provider, confidence, risk, actions, token use, and fallback errors; and
- can automatically email low-risk responses when Autopilot and SMTP are configured.

It may acknowledge, request ordinary diagnostics, route a product issue, and preserve context. It may not change ownership, reveal data, issue credits or refunds, accept liability, promise a deadline, delete an account, or resolve a security incident.

### Beta Coordinator

Implemented in the marketing service. It:

- reviews every application against cohort needs;
- separates Beginner, Intermediate, and Professional testing paths;
- enforces Kizuna's original-work boundary;
- prepares an acknowledgement and cohort recommendation; and
- can pass an approved, low-risk applicant to the Account Steward through a signed service request.

It may acknowledge and score an application. In Assist mode, a person selects **Invite to beta**. In Autopilot, it may invite only low-risk applications above the configured confidence threshold. Known-property, identity, legal, safety, and other escalated applications cannot receive automated access.

### Account Steward

The first Account Steward slice is implemented inside the authenticated application service, where identity and entitlements already live. It:

1. accepts only timestamped HMAC-signed requests from the marketing service;
2. issues single-use, short-lived invitations without returning the raw token to marketing;
3. verifies email ownership by delivering the invitation directly from the app;
4. creates a time-limited beta entitlement and starter production;
5. preserves Beginner, Intermediate, or Professional onboarding context; and
6. records security events for invitation creation and acceptance.

The next Account Steward work is incomplete-onboarding monitoring, useful reminders, reversible profile help, and entitlement lifecycle notices.

Password resets remain user-controlled through one-time links. Ownership transfers, email changes on disputed accounts, account deletion, and suspicious access remain human-gated.

### Growth and Editorial Studio

Planned after support and account lifecycle are stable. It will:

- turn approved product milestones into blog and social drafts;
- maintain an editorial calendar;
- reuse one approved factual source across platform-specific posts;
- check originality, rights, confidentiality, and unsupported claims;
- schedule low-risk evergreen material; and
- measure useful engagement without optimizing for outrage or deceptive claims.

Product announcements, pricing, partnerships, customer stories, incident communications, and legal/policy claims require approval. Routine educational posts may be scheduled automatically after the source material and voice rules are approved.

### Operations Producer

Planned as the coordinating layer. It will send one digest rather than many notifications:

- urgent decisions requiring action;
- customers at risk of being blocked;
- recurring product failures and likely root causes;
- beta progress and cohort health;
- content awaiting factual approval;
- AI and email cost; and
- automatic actions completed since the last digest.

## Autonomy levels

- `off`: records arrive normally; no agent run occurs.
- `assist`: agents classify, summarize, and draft. Nothing external is sent automatically.
- `autopilot`: low-risk work above the configured confidence threshold may execute. High-risk work always enters **Needs you**.

The recommended launch sequence is Assist during internal testing, then Autopilot for acknowledgements, ordinary bug intake, feature requests, feedback, and safe beta correspondence. Expand authority only after reviewing audit history and failure rates.

## Hard escalation rules

The following always require a person or a separately verified workflow:

- refunds, credits, chargebacks, pricing exceptions, and payment disputes;
- account ownership, suspicious access, security incidents, and private-data disclosure;
- deletion, irreversible changes, and restoration from backup;
- legal demands, subpoenas, intellectual-property claims, and threats of litigation;
- harassment, threats, self-harm, or other safety matters;
- fan-fiction or known-property beta requests;
- commitments about uptime, delivery dates, results, partnerships, or liability; and
- publishing confidential roadmap, customer, incident, or financial information.

## Provider boundary

The operations desk is provider-agnostic. It accepts OpenAI, Anthropic, Google, Ollama, or an OpenAI-compatible endpoint through environment configuration. If the provider is missing, offline, malformed, or returns invalid output, Kizuna records the error and falls back to its local policy engine. Provider output cannot weaken hard escalation rules.

Personally identifying contact fields are not included in AI prompts. A future privacy control should allow operators to choose local-only processing for all customer operations.

## Audit and measurement

Each run records the related item, agent, classification, risk, confidence, summary, recommendation, draft, proposed actions, provider, token use, execution state, and fallback error. Email deliveries receive their own delivery record.

Before expanding Autopilot, measure:

- escalation precision and missed high-risk cases;
- useful first-response rate;
- incorrect or unsupported statements;
- reopen rate after an automated response;
- time saved per request;
- provider and email cost; and
- the percentage of the founder's decisions that could become an explicit safe policy.

## Implementation sequence

1. **Current:** support and beta triage, audit trail, provider routing, safe fallback, admin operations desk, and signed beta invitations.
2. **Next:** SMTP delivery verification, inbound reply threading, scheduled worker, Account Steward lifecycle reminders, and daily digest.
3. **Then:** searchable help center and retrieval-assisted answers grounded only in published Kizuna documentation.
4. **Then:** editorial calendar, social connectors, fact approval, and scheduled publishing.
5. **Before scale:** named administrators, MFA, immutable audit export, Redis job queue and limits, privacy retention/deletion, monitoring, incident playbooks, and provider cost budgets.
