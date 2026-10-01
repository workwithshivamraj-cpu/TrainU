# Commercial packaging and assumptions

## Initial offer

Position TrainU as an approved training knowledge workspace for a team with a clear content owner. Demonstrate one real question, the quoted evidence and the original clip/document. Lead with onboarding and support knowledge reuse; do not promise model accuracy, unmeasured time savings or unlimited ingestion.

The most practical first offer is a contract-based pilot with manually managed onboarding and invoicing. The application has plan metadata and usage views, but no integrated checkout/subscription billing. Plan metadata is not comprehensive quota enforcement, and usage rollups should not be treated as an audited invoice ledger.

## Packaging hypothesis

These are product planning options to validate with customers, not live plans or a price list.

| Package | Buyer | Suggested scope | Required before sale |
|---|---|---|---|
| Team pilot | One team lead | One workspace, defined seats/content allowance, assisted setup | Pilot launch gates, measured workload cap, manual invoice/contract |
| Growth | Multiple teams | Larger approved library, more ingestion capacity, support agreement | Enforced usage limits, reliable billing, cost reporting, tested capacity |
| Enterprise | Central IT/enablement | Negotiated security, access and regional requirements | Contract-specific SSO/security/recovery/integration delivery |

Choose actual prices after measuring transcription cost per uploaded minute, embedding/re-embedding cost, model cost per answer, storage/versioning, media egress/CDN, database/worker hosting, support time and target gross margin. Avoid unlimited offers until abuse/cost controls exist. A combined workspace base fee plus included active seats/usage and explicit overage rules is a hypothesis, not a committed billing implementation.

## Pilot onboarding checklist

Agree on the buyer's problem, two or three representative applications, who owns/approves material, permitted data, a support route and a measurable evaluation period. Import only authorized content. Record initial unanswered topics and member feedback. Review useful answers, content coverage, processing failures, cost and retention intent before expanding.

## Customer-facing claims

Supported: organization-scoped roles, approved-content workflow, cited answers, private source playback, a light browser workspace and an optional companion extension when deployed and tested.

Do not claim published app-store availability, enterprise SSO, automated invoices, hard quotas, automatic data erasure, audited compliance, multi-zone availability, an SLA or certified high concurrency until the corresponding implementation and evidence exist. Document service-specific support hours, cancellation, data export and deletion in the actual customer agreement.

## Illustrative economics (29 September 2026)

This is a planning model, not a live price list, quote, or implemented billing policy. Validate the amounts in paid pilots. Illustrative customer price points for an India-first launch are ₹19,900/month for up to 25 active seats, ₹49,900/month for up to 100 seats, and negotiated pricing above that. A 6–8 week assisted pilot could be ₹1.5–3 lakh, credited partly against an annual contract. Quote applicable taxes separately. Consider explicit monthly new-video processing allowances and storage limits; do not sell unlimited ingestion. These prices are hypotheses, not current entitlements in the app.

The largest metered AI expense is transcription, not chat. As a current reference point, OpenAI lists `gpt-4o-mini-transcribe` at $0.003/audio minute, or $0.18 per recorded hour: 20 hours/month is about $3.60 and 100 hours/month is about $18 before retries and other vendors' fees. Its small text embedding model is $0.02 per million input tokens, generally a small ingestion cost. The current API price sheet also lists `gpt-6-luna` at $0.05 per million input tokens and $0.25 per million output tokens; at an illustrative 3,000 input + 500 output tokens per answer, 10,000 answers are about $2.75 of model tokens. These are vendor list-price examples, not the application's measured bill; the local demo currently uses Ollama and has no API-token charge, but local compute, power, and operations are still costs. Model prices and available models change.

These AI line items exclude the costs that dominate early SaaS economics: always-on API/worker compute, managed PostgreSQL and Redis, backups/monitoring, video storage and especially video playback egress, failed/retried jobs, support/onboarding labor, security work, and sales. Budget roughly $300–$1,000/month for a small, non-HA production pilot stack as an initial planning range, then replace it with a region/provider calculator and measured traffic. HA, higher upload/playback volume, and dedicated inference can push this materially higher. It is not a vendor quote or capacity guarantee.

For a conservative forecast, use `monthly cost = fixed hosting + stored GB × storage rate + playback GB × egress rate + video minutes × transcription rate + answer token spend + support hours × loaded hourly cost`. Track these per tenant before offering included allowances. Target at least 70% gross margin after hosting, metered providers, and directly attributable support; do not include product development and sales in that gross-margin calculation. Reprice or cap usage if a customer's video playback, support, or repeated reprocessing breaks the target.

### Market reference points

Adjacent products do not have identical scope. Loom lists Business + AI at $24/user/month and focuses on recording, sharing, and AI-assisted video packaging; Trainual combines SOP/training, role-based learning and AI Q&A but currently asks prospects to request a quote. More directly, Panopto's AI Search offers conversational answers grounded in authorized video-library content with links to exact moments. Microsoft Stream Copilot can answer questions and link timestamps for videos with transcripts, for customers with the required Microsoft 365 Copilot license. This confirms the category is real, but timestamped video Q&A is no longer a unique feature by itself. These products do not prove TrainU's willingness to pay. TrainU should sell a focused workflow: approved procedural knowledge across a team's apps, with human review, audience controls, and cited moments; validate that buyers need this alongside their existing video/LMS suite. Recheck competitor pages before publishing a price list.

Reference pages: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [Loom pricing](https://www.loom.com/pricing), [Trainual plans](https://trainual.com/pricing), [Panopto AI Search](https://www.panopto.com/capabilities/ai-capabilities/ai-search/), [Microsoft Copilot in Stream](https://techcommunity.microsoft.com/blog/streamblog/introducing-copilot-in-microsoft-stream/3929109/), [USD/INR rate history for 29 September 2026](https://wise.com/us/currency-converter/usd-to-inr-rate/history/29-09-2026). At the cited mid-market rate of about ₹95.95 per USD, the suggested ₹19,900 / ₹49,900 / ₹99,900 prices are approximately $207 / $520 / $1,041; exchange rates and taxes move.
