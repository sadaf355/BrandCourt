# Disclosures, Models, Libraries & Asset Attributions

## 1. AI Models & Inference Services

| Provider / Engine | Model / Artifact | Purpose | Hosting / Execution | Data Privacy Guarantee |
| :--- | :--- | :--- | :--- | :--- |
| **BrandCourt Deterministic** | Rules Engine v1.0 | Regulatory checks (ASCI), metric normalization, regex scans | In-Process / Local | 100% on-device, zero outbound network calls |
| **Hugging Face / PyTorch** | `sentence-transformers/all-MiniLM-L6-v2` | Guideline semantic similarity and precedent retrieval | Local embeddings | Vector calculations run locally in Python worker |
| **Ollama / Local LLM** | `meta-llama/Llama-3-8B-Instruct` | Ambiguity analysis and compliant fix suggestions | Local / Air-Gapped | Operates exclusively on pre-masked payloads |

---

## 2. Open-Source Libraries & Frameworks

### Backend Stack
- **FastAPI** & **Starlette**: Async REST API endpoints and middleware.
- **SQLAlchemy 2.0 (Async)**: ORM, query construction, and multi-tenant isolation.
- **Alembic**: Relational database migration management.
- **Pydantic v2**: High-performance request/response data validation.
- **Python-JOSE** & **Passlib (Bcrypt)**: JWT authentication and salted credential hashing.
- **Pytest** & **pytest-asyncio**: Automated unit and integration test runners.

### Frontend Stack
- **React 19** & **TypeScript**: Component model and strict typing.
- **Vite**: Modern frontend bundling and local HMR dev server.
- **TanStack Query (React Query)**: Asynchronous server state and cache synchronization.
- **Recharts**: Responsive SVG compliance analytics and KPI charts.
- **Tailwind CSS**: Utility-first styling with dual dark/light theme support.
- **Lucide React**: Clean iconography for compliance navigation and actions.
- **Playwright** & **Axe-Core**: End-to-end browser automation and WCAG 2.1 AA accessibility verification.

---

## 3. Templates & Starter Content

- **Starter India Rules Pack**: Heuristic guideline rules modeled on publicly available advertising codes (ASCI/ASI). Designed to assist human review workflows; does not constitute formal legal counsel.
- **Aurora Brand Workspace**: Fictional cosmetic and skincare brand created purely for demonstration and compliance workflow verification.

---

## 4. Photography Attributions

All imagery on the public landing page is royalty-free and sourced under the Unsplash Free License:

1. **Creative and Marketing Team Reviewing Content**
   - **Path**: `frontend/public/landing/team.webp`
   - **Source**: [Unsplash photo-1522071820081-009f0129c71c](https://images.unsplash.com/photo-1522071820081-009f0129c71c)
   - **Photographer**: Annie Spratt
   - **Licence**: Unsplash License (free to use for commercial and non-commercial purposes)

2. **Skincare Product Flat-Lay**
   - **Path**: `frontend/public/landing/skincare.webp`
   - **Source**: [Unsplash photo-1556228720-195a672e8a03](https://images.unsplash.com/photo-1556228720-195a672e8a03)
   - **Photographer**: Content Pixie
   - **Licence**: Unsplash License (free to use for commercial and non-commercial purposes)

3. **Creative Workspace Desk**
   - **Path**: `frontend/public/landing/desk.webp`
   - **Source**: [Unsplash photo-1499750310107-5fef28a66643](https://images.unsplash.com/photo-1499750310107-5fef28a66643)
   - **Photographer**: Andrew Neel
   - **Licence**: Unsplash License (free to use for commercial and non-commercial purposes)

---

## 5. Platform Scope & Governance Disclaimer

BrandCourt operates strictly as an internal compliance verification, claim audit, and decision tracking system. **It does not connect to, manage, or publish content to any third-party advertising or social media platforms.**
