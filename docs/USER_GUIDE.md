# BrandCourt User Guide

BrandCourt is an enterprise brand compliance and Claim Court engine designed for multi-stakeholder content governance. It ensures marketing and packaging copy adheres strictly to verified brand facts, regulatory guidelines (e.g., ASCI/ASI starter packs), and precedent decisions before publishing.

---

## 1. Role: Content Creator

Content Creators draft, evaluate, and submit content for compliance verification.

### Submitting Content for Review
1. Navigate to **Content Reviews** (`/app/reviews`).
2. Click **+ New Content**.
3. Fill in:
   - **Content Title**: Name of your asset or campaign.
   - **Channel**: e.g., Instagram, E-commerce, Print Packaging.
   - **Caption / Marketing Copy**: The exact copy proposed.
4. Click **Create Draft**.
5. Once created, click **Submit for Review** to trigger the Claim Court analysis pipeline.

### Understanding Findings & Fix Sandbox
- Findings are highlighted with severity tags:
  - **Critical / Major**: Regulatory red flags, unsupported factual claims, or tone/guideline issues requiring resolution or override before approval.
  - **Advisory**: Guidance notes and minor observations that do not block approval.
- **Fix Sandbox** (`/app/intelligence/fix-verify`):
  - Test candidate copy before resubmitting.
  - Checks if intent and calls-to-action (CTAs) are preserved while eliminating blockers.

---

## 2. Role: Reviewer

Reviewers inspect findings, evaluate factual claims, and determine if an override or dispute is justified.

### Reviewer Queue & Actions
1. Open the **Reviewer Queue** (`/app/reviewer/queue`). Items are priority-sorted by risk and urgency.
2. For each claim finding:
   - **Accept Finding**: Confirms the finding is valid and must be fixed by the creator.
   - **Dispute Finding**: Flags that the rule was incorrectly triggered.
   - **Override Finding**: Overrides the finding with explicit justification.
3. **Mandatory Override Justification**:
   - Every override requires a non-empty written reason (e.g., clinical test reference or contract clause).
4. **Precedent Recording**:
   - If a finding decision should apply systematically to future similar copy, submit it to the **Precedent Ledger** for manager endorsement.

---

## 3. Role: Manager / Approvals Gate

Managers hold the sign-off authority for publication readiness and precedent adoption.

### Content Approvals & Blocked Gate
1. Navigate to **Approvals** (`/app/approvals`).
2. **Blocked Approval Gate**:
   - Content with unaddressed Critical/Major findings **cannot** be approved. The system blocks both the UI button and the backend API (HTTP 422).
3. **Approved & Locked Revision**:
   - When approved, BrandCourt locks the revision timestamp (`locked_at`) and captures an immutable JSON snapshot.
4. **Reopening Content**:
   - Reopening an approved item creates a new revision increment; historical snapshots remain frozen.
5. **Precedent Promotion**:
   - Review pending precedents in the **Precedent Ledger** (`/app/intelligence/precedents`).
   - Approve precedents or promote them directly into draft brand rules.

---

## 4. Role: Guideline Owner / Admin

Admins manage organization-wide guidelines, brand facts, AI models, and compliance reporting.

### Managing Rules and Facts
1. **Brand Rules** (`/app/brand/rules`):
   - Import PDF/DOCX brand manuals or create rules manually.
   - Track rule versions and review draft rules before activation.
2. **Guideline Health** (`/app/brand/guideline-health`):
   - Audit conflicting rules, vague directives, and rules with high override rates.
   - **Accept**, **Edit**, or **Ignore** AI-suggested rewrites.
3. **Brand Facts & Expiry** (`/app/brand/facts`):
   - Manage claims backed by lab tests or clinical trials.
   - Track expiring claims via the 90-day expiry watchlist on the Insights Dashboard.

### Model Settings & Privacy Controls
1. Navigate to **Model Settings** (`/app/settings/models`) (Admin only).
2. **Local Model Toggle**: Switch workspace execution between deterministic checks and local Ollama inference (`MODEL_MODE`).
3. **Data-Flow Audit Log**: Inspect character lengths, purposes, and privacy masking verification for every AI model call.

---

## 5. Compliance Reports

### Generating Reports (JSON & PDF)
- **Gate Requirement**: Reports can only be generated for **approved and locked** revisions.
- Go to **Insights & Reports** (`/app/insights`), choose the approved content item, and click **Download JSON** or **Download PDF**.
- **Report Contents**:
  - Full copy and locked snapshot timestamp.
  - All findings, rule IDs, evidence citations, and reviewer decisions with override reasons.
  - Complete AI Call & Masking Audit Table.
  - Intent Preservation status.

---

## 7. Round 3 Features — Where to Find Them

Three new intelligence features are introduced in Round 3 to streamline guideline auditing, reviewer alignment, and copy correction:

### 1. Guideline Health (`/app/brand/guideline-health`)
- **Location:** Navigate to **Brand Rules** -> **Guideline Health** tab.
- **Functionality:** Scans active brand guidelines for vague wording, missing positive/negative examples, and potential rule contradictions.
- **Workflow:** Review candidate conflict pairs and vague rules. Click **Accept Fix** to generate a safe draft rule version, which can then be formally confirmed by an administrator.

### 2. Precedent Ledger (`/app/intelligence/precedents`)
- **Location:** Navigate to **Intelligence** -> **Precedent Ledger** (or via the Reviewer Queue).
- **Functionality:** Tracks managerial override decisions on prior copy findings to ensure consistent future evaluations.
- **Safety Invariant:** Precedent suggestions automatically surface on matching copy (similarity >= 0.85). **Critical findings cannot be downgraded by precedent** (attempting to do so triggers an HTTP 409 error).

### 3. Fix Verification (`/app/intelligence/fix-verify`)
- **Location:** Navigate to **Intelligence** -> **Fix Sandbox** or click **Verify Fix** on any finding card.
- **Functionality:** Tests proposed copy rewrites on a temporary sandbox revision before committing changes.
- **Safety Invariant:** Evaluates intent similarity, checks that original calls-to-action (CTAs) are preserved, and immediately rejects any candidate fix that introduces new Critical findings.

---

## 8. Governance & Legal Disclosures

> **IMPORTANT**:
> - BrandCourt is an internal compliance and workflow verification engine. It **does not publish** directly to any social or external platform.
> - The Starter India rules pack comprises heuristic checks derived from public guidelines (ASCI/ASI) for human reviewer aid and does not constitute formal legal counsel.

