# Models, analysis and asset disclosures

## Analysis methods

| Method | Current implementation | Purpose | Limitations |
|---|---|---|---|
| Deterministic checks | In-process Python rules, pattern checks and claim policy | Repeatable checks against configured brand rules and facts | Heuristics can miss context and require human review |
| Local retrieval | `hashing-trigram-v1` vectors and lexical similarity | Retrieve potentially relevant rules and precedents | Not a pretrained language embedding model; similarity is not proof |
| Optional local model | Ollama chat/NLI and embedding endpoints when configured | Additional ambiguity analysis and retrieval context | Requires a reachable Ollama service and downloaded models; unavailable results must remain uncertain |
| Optional hosted model | OpenAI-compatible chat endpoint when explicitly configured | Schema-constrained model adjudication | Requires an external provider, credentials and appropriate data-processing approval |
| Image text extraction | Tesseract through the Python OCR integration | Extract text from supported raster images | Requires the Tesseract executable; OCR can be incomplete or incorrect |

Model output is validated against an expected schema. Adjudication quotes must match the stored fact text after approved masking restoration. A model response does not independently establish that a claim is true.

## Backend libraries

The backend uses FastAPI, Starlette, Pydantic Settings, SQLAlchemy 2.x, Alembic, asyncpg, aiosqlite, PyJWT, argon2-cffi, httpx, boto3, Pillow, pytesseract, OpenCV, pypdf and python-docx. Automated tests use pytest and httpx.

## Frontend libraries

The frontend uses React, TypeScript, Vite, React Router, TanStack Query, React Hook Form, Zod, Recharts, Lucide React, Three.js, Vitest, Testing Library, Playwright and axe-core. Styling is implemented with the project's CSS design system; Tailwind CSS is not a runtime dependency.

## Starter policy and demo data

The India rules pack is starter guidance for internal review, not legal advice or a substitute for current regulatory review. GlowSerum/Aurora is fictional demonstration data and must not be represented as a real brand or clinical evidence. The demo workspace is a shared public workspace with fictional data that anyone can edit.

## Landing-page imagery

The landing page contains image assets under `frontend/public/landing/`. Review the source and applicable licence information before replacing, redistributing or reusing those assets outside this repository. The sources and licences of the images in frontend/public/landing/ have not been verified.

## Product scope

BrandCourt does not connect to, manage or publish content to third-party advertising or social-media platforms. It supports internal review, governance and export workflows only.

## Deployment limitations

The hosted demo runs APP_ENV=staging with local disk storage, so uploaded files are lost on restart; the free-tier API sleeps when idle; the hosted instance runs MODEL_MODE=deterministic so Ollama variants were not exercised there; the fact-expiry scheduler runs only under Docker Compose, not on the hosted API.

## Round 3 — additional evaluation and product limitations (9 November 2026)

- **Fix suggestions:** cure, guarantee and superlative phrase substitutions are deterministic heuristics. They are suggestions only. Every proposed candidate is re-run through the review engine; a new Critical finding or failed intent check rejects it. This does not guarantee legal compliance or semantic equivalence.
- **Intent score:** similarity is produced by a local hashing/trigram representation and CTA-retention heuristic. It is not a calibrated semantic score and should not be presented as a probability.
- **Evaluation data:** the 52 GlowSerum posts are fictional sample data with historical exposure to rule development. Historical golden-test accuracy is not a clean holdout result. Fresh independent posts are required for a defensible generalisation claim.
- **Ollama:** local-model evaluation was not executed in this delivery environment because no Ollama service/model was reachable. Do not claim live model accuracy until the three variants complete on the same frozen dataset.
- **Images:** expected visual labels are not image evidence. Five actual creative image files must be run through the configured upload, OCR and image-analysis path before image performance is reported.
- **Language coverage:** Hindi/Marathi and mixed-language content may have limited automated coverage. The UI asks for a fluent human review; no broad multilingual accuracy guarantee is made.
- **Workflow scope:** comment resolving, email invitations, member removal and workspace deletion are not exposed as complete end-to-end product actions. Member creation and role changes are distinct from email invitations.
- **Analytics:** channel/creator/week aggregations and approval-duration calculations are based on stored workspace records. Where no real approval history exists, seeded reference values may be shown and must not be mistaken for measured operational performance. Team-level analytics are not supported by the current data model.
- **Accessibility and speed:** axe-core is a dependency, not evidence of a completed audit. The 15-second text and 30-second image targets have not been validated in production-like load tests.
- **Human evidence:** no user sessions, manual-vs-product timing study, or demo video was generated as part of this code update. Do not represent these as completed research.
- **Competitor review:** the competitor pack is based on public vendor materials and is not a hands-on comparison or independent feature verification.
