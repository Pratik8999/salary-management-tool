# AI Usage

Claude (via Claude Code) was used throughout this assessment as a pair-programmer — driving scaffolds, drafting first cuts of TDD pairs, and producing migration / Dockerfile boilerplate — while every design decision, schema call, and trade-off was made by the human author and reviewed before each commit. The repo's commit history is the audit trail: each commit is small, single-concern, and was reviewed before being applied.

This file documents how AI was used so a reviewer can judge what's mine vs. what's the assistant's. It is not a transcript — the working notes (`ai_agent_prompt.md`, `finalized_feature_list.md`) are deliberately kept local, since they describe the personal brief I gave the agent rather than the product itself.

---

## Where AI helped

| Phase | What I asked AI for | What I kept ownership of |
|---|---|---|
| **Repo scaffold** | "Set up a FastAPI + SQLAlchemy + Alembic project under `backend/` with `uv`; React + Vite + Tailwind + shadcn/ui under `frontend/`." | Choosing the tech stack and monorepo layout, deciding sync over async SQLA. |
| **Test infrastructure** | "Wire up `pytest`, `pytest-asyncio`, `httpx.AsyncClient`, and a transactional per-test fixture against a real Postgres test DB." | Insisting on a real DB over mocks, the per-test rollback fixture pattern. |
| **TDD pairs** | "Write failing tests for `POST /auth/login` covering valid creds → token, bad creds → 401, inactive user → 403. Don't implement yet." then "Now make those tests pass." | The specific error-message contract ("Email does not exist" vs "Password is incorrect" — a deliberate choice, not the security-mush generic message). |
| **Alembic migrations** | "Generate a migration that lifts the `department` string column into a `departments` table with FK + backfill." | Deciding the FK was needed in the first place (the string column was a drift smell I noticed and called out). |
| **Frontend pages** | "Build an Employees list page with paginated search, calling `GET /api/employees`. Use shadcn `Table` and `Button`." | Visual hierarchy, when to add filters vs. search, the choice to drop the global avg-salary KPI because it mixes currencies. |
| **Docker prod stack** | "Multi-stage Dockerfile for the frontend (node build → nginx serve) and a `docker-compose.prod.yml` overlay exposing only port 80." | The nginx `proxy_pass /api/*` decision so the SPA is same-origin, the choice to bake migrations into the backend's entrypoint. |
| **Refactors** | "Move the country→currency map from the frontend into a backend reference module exposed at `/api/countries`." | Noticing the layering smell in the first place — AI happily kept the hardcoded map until I called it out. |
| **EC2 deploy** | "Install Docker via the official script, generate a JWT secret with `secrets.token_hex(32)`, write `.env`, bring the prod stack up, seed 5k." | Choosing the instance size, deciding which ports to open in the Security Group, choosing to keep secrets only on the server. |

---

## Representative prompts (paraphrased, not raw)

- "TDD: write failing tests first for the User model — password is hashed on set, `verify_password` works, role enum validates. Don't implement yet."
- "Add a `/api/employees` list endpoint with `q`, `country`, `department_id` filters and offset-based pagination. Order by `created_at DESC` by default."
- "I want a reference catalog of countries with ISO 4217 codes — propose where it should live and why."
- "The dashboard's 'Average salary' KPI averages across mixed currencies. Walk me through whether to keep it, drop it, or change it. Don't write code yet."
- "Build a `SuccessBanner` component that auto-dismisses after 3.5s, then wire it into employee create, employee edit, user create/update, department actions, and document upload/delete."
- "We're getting `PermissionError: '/data/documents'` on upload in prod. Diagnose."
- "Rebuild only the frontend container after the EmployeesPage change, then smoke `/api/health` and the new dashboard insight endpoints."

Each of those produced a draft I then reviewed, adjusted, and committed. Roughly half the AI-generated diffs were modified before commit.

---

## What AI did **not** do

- **Decide what to build.** The product scope and the feature trade-offs (drop the salary-band alerts, drop the global avg-salary tile, keep `country` as a string instead of an FK, soft-delete employees) are mine.
- **Pick the tech stack.** FastAPI + Postgres + React + Vite + Tailwind + shadcn/ui was decided up front, before the assistant was involved per-phase.
- **Write the commits.** Commit message tone and grouping ("one concern per commit", conventional prefixes, lightly-handwritten body voice) are mine — the assistant was instructed to match that voice.
- **Approve destructive actions.** EC2 access, Docker volume resets, password rotations — every irreversible action was confirmed by me before it ran.
- **Touch the private working spec.** `ai_agent_prompt.md` and `finalized_feature_list.md` are gitignored and describe my brief to the assistant; they are not part of the product.

---

## How to verify

Run `git log --oneline` — every commit is small enough to scan in one sitting. The pattern `test(...)` → `feat(...)` repeating across the backend phases is the TDD trail. Each commit body explains the *why*, not just the *what*, which is the signal that a human shaped it.
