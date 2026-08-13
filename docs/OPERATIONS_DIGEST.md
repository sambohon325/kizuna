# Daily Operations Digest

The Operations Producer turns the website administrator's queues into one private daily brief. It is designed to reduce interruptions while keeping consequential decisions with the owner.

## What the digest includes

- urgent AI decisions that need a person;
- the number of customers blocked or at risk;
- active support volume and the most common support categories;
- beta applications by workflow state;
- editorial work awaiting factual review;
- completed and automatic operations actions; and
- recorded AI token use for the period.

The digest intentionally excludes customer email addresses, application narratives, private ticket descriptions, and production content. Open the administrator when a summary needs investigation.

## Prepare and send

1. Open **Website admin → Daily digest**.
2. Select **Prepare today's digest**.
3. Read or edit the private preview.
4. Select **Review & send**.

Delivery requires working SMTP settings and `KIZUNA_OPERATIONS_DIGEST_EMAIL`. A prepared digest remains in history if delivery fails, and its failure state is recorded for review.

## Safety boundary

Preparing a digest never sends email. Sending is a separate, explicit action. The first release does not run an unattended schedule; scheduling should be enabled only after delivery, redaction, and operational accuracy have been verified in production.
