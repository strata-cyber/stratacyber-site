+++
title = "How to read a Strata Cyber advisory"
summary = "TLP, severity, probability, confidence and personal data: what each part of our advisories means and what it asks of you."
date = 2026-11-26
kind = "Method"
author = "Jefferson Andrade"
tlp = "CLEAR"
+++

Every advisory we publish follows the same format. That is not about looks: it lets the reader see within seconds **who they can share it with**, **how serious it is**, **whether personal data is involved** and **what to do first**. This note explains each part.

## The TLP label: who you can share it with

The Traffic Light Protocol (TLP 2.0, maintained by FIRST) sits at the top of every report and advisory. It says how far the information may travel, not how serious it is.

| Label | Who may receive it |
|---|---|
| `TLP:RED` | Only the named recipients. Do not pass it on. |
| `TLP:AMBER+STRICT` | Your organization only. |
| `TLP:AMBER` | Your organization and its clients who need to know to protect themselves. |
| `TLP:GREEN` | Your community (sector, ISAC, partners), but not public channels. |
| `TLP:CLEAR` | Anyone. It can be published. |

TLP colors are the FIRST standard, always on black. That is why they do not follow our brand palette.

## Severity: how serious it is for you

Severity sums up the likely impact **for the recipient**, given their exposure and existing controls. We use five levels: <span class="sev sev-critical">Critical</span> <span class="sev sev-high">High</span> <span class="sev sev-medium">Medium</span> <span class="sev sev-low">Low</span> <span class="sev sev-info">Info</span>

The same event can be *High* for a bank and *Low* for a manufacturer. When an advisory is written for a specific client, severity is assessed against their environment.

## Probability and confidence are different things

Every key judgment states two things:

- **Probability**: the chance that something happens, in fixed ranges.
- **Confidence**: how much we trust the evidence and reasoning behind the estimate.

> We assess with moderate confidence that ransomware groups are likely (55–80%) to target the sector within 90 days.

We always use the same words for the same ranges. The scale comes from the US Intelligence Community's analytic standards (ICD 203):

| Term | Range |
|---|---|
| Almost no chance | 1–5% |
| Very unlikely | 5–20% |
| Unlikely | 20–45% |
| Roughly even chance | 45–55% |
| Likely | 55–80% |
| Very likely | 80–95% |
| Almost certain | 95–99% |

Confidence has three levels, following common intelligence practice:

| Confidence | What it means |
|---|---|
| High | Good-quality evidence from several independent sources. Still not a certainty. |
| Moderate | Credible and plausible, but not corroborated enough for high confidence. |
| Low | Evidence is scarce, fragmentary or from sources we cannot verify. |

!!! note "Why we never say “definitely”"
    Intelligence works with incomplete information. Writing “this will definitely happen” hides the risk of being wrong from the person who has to decide. A fixed range lets you compare advisories and hold us to account over time.

## Personal data: when the clock starts

If an advisory describes activity that could expose personal data, it says so explicitly and points to the data protection questions you need to answer. Notification deadlines can start running as soon as you know personal data was affected:

- **GDPR**: the supervisory authority, without undue delay and where feasible within 72 hours of becoming aware (Art. 33), unless the breach is unlikely to put people at risk. The people affected must also be told when the risk to them is high (Art. 34).
- **LGPD**: the ANPD and the people affected, within three business days of learning that the incident affected personal data, when it may cause them relevant risk or harm (ANPD Resolution CD/ANPD 15/2024).

Whether to notify is the controller's decision, taken with the DPO and based on the risk to the people affected, not the risk to the company. The advisory gives you the facts to make that call quickly.

## Indicators come “defanged”

Malicious domains, URLs and IP addresses appear with brackets, or `hxxp` instead of `http`. This prevents accidental clicks and stops mail filters from treating the advisory itself as a threat.

```
login-portal-bank[.]example
hxxps://login-portal-bank[.]example/login
198.51.100[.]23
```

To use the indicators for blocking or hunting, remove the brackets in the destination tool, never in a browser.

## What to do now

Every advisory ends in numbered actions, in priority order. The first is always the one that cuts the most risk in the least time. If you only have five minutes, do the first one.
