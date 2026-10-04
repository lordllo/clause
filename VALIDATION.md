# Local validation

Verified on Windows with Python 3.12 and Node 24:

- Backend unit and API integration checks pass.
- Synthetic evaluation: 10 cases; status accuracy 100%, citation validity 100%, retrieval recall@5 100% in demo mode. The dataset is intentionally tiny and is not a real-world performance claim.
- Frontend TypeScript check and optimized Next.js production build pass.
- Browser walkthrough: select uploaded sample, run policy review, see five deviations and five verified quotes, open source evidence panel.
- Compose configuration validates. Container startup and Postgres execution are unverified because Docker Desktop's engine was unavailable.
- Structured provider wiring and refusal behavior are tested with a mock. Live provider calls are unverified; no API key was supplied.

The local preview uses SQLite and demo mode. Dependency versions are recorded in `frontend/package-lock.json` and `backend/requirements.lock.txt`.
