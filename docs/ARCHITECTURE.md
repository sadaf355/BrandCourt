# BrandCourt System Architecture

BrandCourt is engineered as a secure, role-governed compliance verification platform for enterprise marketing and regulated product claims.

```
+-----------------------------------------------------------------------+
|                            Frontend Layer                             |
|  React 19 + TypeScript + Vite + TailwindCSS + Recharts + Playwright   |
+-----------------------------------------------------------------------+
                                  |  REST / JWT Auth
+-----------------------------------------------------------------------+
|                            API & Gateway                              |
|          FastAPI + Pydantic v2 + Dependency-injected RBAC             |
+-----------------------------------------------------------------------+
                                  |
    +-----------------------------+-----------------------------+
    |                             |                             |
+-------------------+   +--------------------+   +----------------------+
| Layer 1: Rules    |   | Layer 2: Semantics |   | Layer 3: LLM Judge   |
| Deterministic     |   | Vector Embeddings  |   | Ollama / Llama-3     |
| Regex + ASCI Pack |   | sentence-transf.   |   | Masked PII only      |
+-------------------+   +--------------------+   +----------------------+
                                  |
+-----------------------------------------------------------------------+
|                        Data Persistence Layer                         |
|   PostgreSQL / SQLite + SQLAlchemy 2.0 (Async) + Alembic Migrations  |
+-----------------------------------------------------------------------+
```

---

## 1. 3-Layer Claim Court Engine

1. **Layer 1: Deterministic Engine**
   - High-throughput regex, unit conversions (e.g., SPF, %, ml), and regulatory pattern rules (e.g., ASCI guidelines).
   - Fast-fails obvious claim non-compliances before calling external services.

2. **Layer 2: Semantic Retrieval**
   - Employs `sentence-transformers/all-MiniLM-L6-v2` embeddings for semantic guideline retrieval and precedent matching.
   - Computes cosine similarity against the company's active rule database and approved historical precedents.

3. **Layer 3: Ambiguity Analysis & Fix Proposal**
   - Calls local LLMs (e.g., `Llama-3-8B-Instruct` via Ollama) or hosted models strictly over **pre-masked payloads**.
   - Assesses edge-case phrasing, checks intent preservation, and generates conservative compliant fixes.

---

## 2. Privacy & Masking Architecture

BrandCourt enforces an air-gapped privacy boundary on all text processed by language models:
- **Pre-masking Pipeline**: PII, unpublished SKU names, proprietary formulas, and designated brand secrets are tokenized (e.g., `[SECRET_FORMULA_1]`) prior to model ingestion.
- **AI Audit Trail (`ai_calls` table)**:
  - Every call stores: `provider`, `model`, `purpose`, `input_chars`, `masked_entities`, `masking_confirmed`, and `duration_ms`.
  - Stored records are surfaced transparently in the **Model Settings** log and compiled into the final **Compliance PDF/JSON Report**.

---

## 3. Data Model & Role-Based Governance

- **Multi-Tenancy**: Every entity (`ContentItem`, `Rule`, `Fact`, `Precedent`) enforces strict foreign-key partitioning by `workspace_id`.
- **Revision Locking**:
  - `ContentRevision.locked_at`: Sets an immutable timestamp upon approval.
  - `ContentRevision.approved_snapshot`: Preserves a frozen JSON copy of the content and all resolved findings.
- **Role Hierarchy**:
  - `creator` < `reviewer` < `manager` < `admin`
  - High-impact India-pack rules (`IN-*`) and final content approvals are gated to `manager` or `admin` roles.
  - Model privacy configuration is restricted strictly to `admin`.

---

## 4. Reporting Pipeline

- **Stateless PDF Generation**:
  - Built using a zero-dependency, pure-Python PDF/1.4 binary generator (`backend/app/services/reports.py`).
  - Guarantees zero C-library or external webkit dependencies.
- **Integrity Gating**:
  - Downloads are strictly blocked unless the revision status is `approved` and `locked_at` is non-null.

