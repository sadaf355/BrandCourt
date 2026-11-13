# BrandCourt Product Roadmap

This document outlines the product roadmap for BrandCourt across near-term, medium-term, and long-term milestones, building upon the initial governance engine foundation.

---

## 1. Near-Term Priorities (Months 1–3)

### 1.1 Post-Publish Monitoring & Fact-Expiry Alerts
- **Who it is for:** Compliance Officers, Brand Safety Managers, and Legal Teams.
- **Problem solved:** Content approved today may become non-compliant tomorrow when supporting clinical trial data or product certifications expire.
- **Scope & What it takes:**
  - Automated webhooks and scheduled daily cron worker to evaluate live URLs/social posts against expired facts.
  - Active alerting via Slack, Microsoft Teams, and email when a fact backing live copy enters the 90-day expiry window or expires.
  - Automated notification to assign owners to refresh claims or schedule content takedowns.

### 1.2 PDF & Slide-Deck Review Engine
- **Who it is for:** B2B Marketing, Sales Enablement, and Medical Affairs Teams.
- **Problem solved:** Large enterprise collateral, medical slide decks, and whitepapers are shared in PDF/PPTX formats and currently require manual per-page compliance audits.
- **Scope & What it takes:**
  - Native integration with `pypdf` and `python-pptx` to extract slide text, footnotes, table claims, and slide speaker notes.
  - Page-by-page bounding box annotations surfacing claim court findings directly on rendered slide previews.
  - Batch export of annotated compliance PDFs with audit trails.

### 1.3 Google Docs & Microsoft Word Native Add-ins
- **Who it is for:** Copywriters, Agency Creatives, and Content Strategists.
- **Problem solved:** Creators work in Word and Google Docs; forcing them to context-switch to a web portal creates friction and slows turnaround.
- **Scope & What it takes:**
  - Google Workspace Add-on (Apps Script / TypeScript) and Office 365 Add-in (Office.js).
  - In-document sidebar displaying real-time Claim Court findings, vague rule warnings, and suggested replacements as copy is typed.
  - One-click copy replacement with intent preservation checks before submission.

---

## 2. Medium-Term Enhancements (Months 4–6)

### 2.1 Browser Plug-in & API for Autonomous AI Agents
- **Who it is for:** Growth Teams using generative AI copy tools, Social Media Managers, and Engineering Teams building autonomous marketing agents.
- **Problem solved:** AI agents generating hundreds of marketing variants daily can bypass human compliance gates without automated guardrails.
- **Scope & What it takes:**
  - Chrome / Chromium Extension providing overlay inspections on CMS platforms (WordPress, Shopify, Meta Business Suite).
  - Clean REST & gRPC API (`/api/v1/agent/evaluate`) with API key authentication, rate limits, and sub-second evaluation for LLM tool-calling (MCP server / LangChain / CrewAI integrations).
  - Automated blocking responses when an autonomous agent attempts to publish copy with Critical claim violations.

### 2.2 Deeper Indic Language Support (Hindi, Marathi & Hinglish)
- **Who it is for:** Regional Brand Teams and Multilingual Marketing Campaigns in India.
- **Problem solved:** Indian regional advertising heavily blends Devanagari and Latin scripts (Hinglish) with nuanced idiomatic phrasing that generic keyword filters miss.
- **Scope & What it takes:**
  - Tokenization and transliteration pipeline for Romanized Hindi/Marathi and Devanagari script normalisation.
  - Domain-specific Indic NLP dictionaries for cosmetic, medical, and FMCG regulatory guidelines (ASCI codes in translation).
  - Human-in-the-loop escalation workflows specifically tagged for fluent regional reviewers.

### 2.3 Sector-Specific Rule Packs (Finance, Health & Education)
- **Who it is for:** Specialized Enterprise Sectors (Fintech, Healthcare/Pharma, EdTech).
- **Problem solved:** General advertising rules do not cover strict statutory disclosures mandated by SEBI/RBI, CDSCO/FDA, or consumer protection bodies.
- **Scope & What it takes:**
  - **Finance (Fintech/BFSI):** SEBI mutual fund disclaimer rules, RBI lending disclosures, interest rate transparency, risk disclosures.
  - **Health & Pharma:** Schedule J disease claims, Drugs & Magic Remedies Act prohibitions, telemedicine guidelines, ingredient disclosure standards.
  - **Education & EdTech:** ASCI Guidelines for Educational Coaching Institutions, job placement guarantee verifications, student ranking authenticity rules.

---

## 3. Long-Term Vision (Months 7–12)

### 3.1 Multi-Brand & Agency Workspaces
- **Who it is for:** Advertising Agencies, Holding Companies, and Brand Conglomerates.
- **Problem solved:** Agencies manage dozens of distinct client brands with strict data isolation, unique rulebooks, and conflicting precedent histories.
- **Scope & What it takes:**
  - Tenant-level data partitioning with role-based cross-workspace access control (Agency Account Director vs. Brand Client Approver).
  - Brand-specific precedent ledgers preventing rule leakage between competing accounts.
  - Unified agency billing and consolidated multi-brand compliance analytics.

### 3.2 Enterprise Readiness (Single Sign-On & Self-Hosting)
- **Who it is for:** Fortune 500 Enterprises, Regulated Entities, and IT Security Officers.
- **Problem solved:** Enterprise deployment requires SAML/OIDC SSO, strict data sovereignty, on-premise model execution, and comprehensive SIEM integration.
- **Scope & What it takes:**
  - SAML 2.0 / OIDC integrations (Okta, Azure AD, Ping Identity) with automated SCIM user provisioning.
  - Air-gapped self-hosting package via Kubernetes Helm charts with support for local on-premise LLMs (Ollama / vLLM) with zero telemetry egress.
  - Audit log streaming to enterprise SIEM platforms (Splunk, Datadog, AWS CloudWatch) meeting SOC 2 Type II and ISO 27001 requirements.

