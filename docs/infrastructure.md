# Infrastructure experiment notes

## Render Free

- One Docker-based FastAPI web service; no database or custom domain.
- The service uses Render's assigned `onrender.com` TLS URL.
- Cost for this design: $0/month on Render's Free web-service plan, subject to the plan's 750 free instance hours each month.
- Free services spin down after 15 minutes without inbound traffic and typically take about one minute to wake. This is why the first request is measured separately.
- First request after idle must be recorded without an artificial warm-up.
- Transcript failures are grouped separately from endpoint startup/unreachability.
- The local filesystem and in-memory cache are disposable by design.
- Source: <https://render.com/docs/free>

## Azure comparison

- Microsoft, not Rutgers or this repository, makes the eligibility decision during signup. The published requirements are age 18 or older, full-time attendance at an accredited degree-granting two- or four-year institution, and verification through the institution's email address. A current Rutgers student who meets those conditions appears eligible, but eligibility is not confirmed until Microsoft accepts the school-email verification.
- Azure for Students currently requires no credit card and includes a $100 credit usable within 12 months. We do not need to consume that credit for this experiment.
- The initial comparison target would be Linux App Service F1 at a listed $0/month, not a paid dedicated plan. F1 provides shared compute, 60 CPU minutes per day, 1 GB RAM, and 1 GB storage, with no SLA and no production support.
- F1 is suitable only as a second acquisition experiment because of its shared compute and daily CPU quota. Render remains first because its repository blueprint already exists and its free allowance is less restrictive for a short recruiting-season demo.
- Azure credit does not make transcript access reliable; Azure egress IPs may still be blocked by YouTube.
- No Azure resource should be created until student eligibility is confirmed and its selected plan shows an estimated $0 charge.
- Sources: <https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p> and <https://azure.microsoft.com/en-us/pricing/details/app-service/linux/>
