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

The India rules pack is starter guidance for internal review, not legal advice or a substitute for current regulatory review. GlowSerum/Aurora is fictional demonstration data and must not be represented as a real brand or clinical evidence.

## Landing-page imagery

The landing page contains image assets under `frontend/public/landing/`. Review the source and applicable licence information before replacing, redistributing or reusing those assets outside this repository.

## Product scope

BrandCourt does not connect to, manage or publish content to third-party advertising or social-media platforms. It supports internal review, governance and export workflows only.
