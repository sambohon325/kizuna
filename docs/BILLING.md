# Billing and public trial readiness

Kizuna uses hosted payment surfaces so card details never touch the application server. The Account workspace asks the backend for a Stripe Checkout URL, then redirects the creator to Stripe. Existing customers manage payment methods, invoices, subscription changes, and cancellation through the Stripe customer portal.

The success URL is informational only. Entitlements change only when the public webhook endpoint receives a valid, recent Stripe signature over the unmodified request body. Processed event IDs are stored uniquely, so a webhook retry cannot apply the same event twice. Active or trialing subscriptions receive Creator access. Incomplete, past-due, or ended subscriptions become review-only with trial export restrictions retained.

## Safe rollout

1. Keep public trial signup disabled.
2. Create a Stripe test-mode recurring product and price.
3. Activate and brand the Stripe customer portal.
4. Add the three Stripe variables to Coolify and mark both secrets as secrets.
5. Register `https://app.kizuna.technology/api/billing/stripe/webhook` for `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, and `invoice.payment_failed`.
6. Complete a test checkout and confirm the Account workspace changes only after the webhook.
7. Test portal return, cancellation, payment failure, and repeated webhook delivery.
8. Configure a production Turnstile widget restricted to the app hostname and verify failed tokens cannot register.
9. Run a real database restore drill before opening signup.

Use Stripe test keys until the product, pricing, tax, refund, cancellation, privacy, and support policies have been reviewed. Never commit Stripe or Turnstile secrets.
