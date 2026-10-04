# Local validation

Verified on Windows with Python 3.12 and Node 24:

- 15 backend unit and API integration checks pass, including idempotent demo seeding, source provenance, public corpus hashes and all 1,930 original CUAD annotation offsets.
- Synthetic evaluation: 10 cases; status accuracy 100%, citation validity 100%, retrieval recall@5 100% in demo mode. The dataset is intentionally tiny and is not a real-world performance claim.
- Frontend TypeScript check and optimized Next.js production build pass.
- Browser walkthrough: select uploaded sample, run policy review, see five deviations and five verified quotes, open source evidence panel.
- Expanded browser walkthrough: filter Common Paper collection, search AI Addendum, choose Privacy & AI playbook, run a real-contract evidence review, verify abstention; search a CUAD hosting agreement, filter Governing Law annotations, and inspect the linked source passage.
- Public-corpus retrieval evaluation: 81.96% answer recall@5 across 460 mappable source excerpts from eight CUAD labels and 60 contracts. Twelve multi-passage excerpts are excluded. This is not held out and does not measure legal accuracy.
- Compose configuration validates. Container startup and Postgres execution are unverified because Docker Desktop's engine was unavailable.
- Structured provider wiring and refusal behavior are tested with a mock. Live provider calls are unverified; no API key was supplied.

The local preview uses SQLite and demo mode. Dependency versions are recorded in `frontend/package-lock.json` and `backend/requirements.lock.txt`.
