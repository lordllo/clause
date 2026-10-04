import hashlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import select
from .db import initialize, Session, Document, Clause, Review, PolicyRecord
from .schemas import Policy, DEFAULT_POLICY
from .parsing import parse
from .analysis import analyze

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title="Clause API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("WEB_ORIGIN", "http://localhost:3000")], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

@app.get("/health")
def health():
    return {"status": "ok", "provider": os.getenv("ANALYSIS_PROVIDER", "demo")}

@app.get("/policies/default")
def default_policy():
    return DEFAULT_POLICY

@app.get("/policies")
def policies():
    with Session() as s:
        return [{"id": p.id, **p.body} for p in s.scalars(select(PolicyRecord))]

@app.post("/policies", status_code=201)
def save_policy(policy: Policy):
    if len({r.id for r in policy.rules}) != len(policy.rules):
        raise HTTPException(422, "Rule IDs must be unique")
    with Session() as s:
        p = PolicyRecord(id=str(uuid4()), body=policy.model_dump())
        s.add(p); s.commit()
        return {"id": p.id, **p.body}

@app.get("/documents")
def documents():
    with Session() as s:
        return [{"id": d.id, "name": d.name, "created_at": d.created_at} for d in s.scalars(select(Document).order_by(Document.created_at.desc()))]

@app.post("/documents", status_code=201)
def upload(file: UploadFile):
    content = file.file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Upload limit is 10 MB")
    name = (file.filename or "document").replace("\\", "/").split("/")[-1][:255]
    suffix = Path(name).suffix.lower()
    try:
        clauses = parse(content, suffix)
    except Exception as exc:
        raise HTTPException(422, "Document could not be parsed. Use a readable PDF, DOCX, or UTF-8 TXT (max 200 PDF pages).") from exc
    id = str(uuid4())
    path = Path("data/uploads") / (id + suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    try:
        with Session() as s:
            s.add(Document(id=id, name=name, digest=hashlib.sha256(content).hexdigest(), source_path=str(path)))
            s.flush()
            s.add_all([Clause(document_id=id, **c) for c in clauses]); s.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"id": id, "name": name, "clause_count": len(clauses)}

@app.get("/documents/{id}")
def document(id: str):
    with Session() as s:
        d = s.get(Document, id)
        if not d: raise HTTPException(404, "Document not found")
        clauses = [{"id": c.id, "page": c.page, "heading": c.heading, "text": c.text} for c in s.scalars(select(Clause).where(Clause.document_id == id))]
        reviews = [{"id": r.id, "created_at": r.created_at, "policy_snapshot": r.policy, **r.result} for r in s.scalars(select(Review).where(Review.document_id == id).order_by(Review.created_at.desc()))]
        return {"id": id, "name": d.name, "clauses": clauses, "reviews": reviews}

@app.get("/documents/{id}/source")
def source(id: str):
    with Session() as s:
        d = s.get(Document, id)
        if not d: raise HTTPException(404, "Document not found")
        return FileResponse(d.source_path, filename=d.name, media_type="application/octet-stream")

@app.post("/documents/{id}/reviews", status_code=201)
def review(id: str, policy: Policy):
    if len({r.id for r in policy.rules}) != len(policy.rules):
        raise HTTPException(422, "Rule IDs must be unique")
    with Session() as s:
        if not s.get(Document, id): raise HTTPException(404, "Document not found")
        clauses = [{"id": c.id, "page": c.page, "heading": c.heading, "text": c.text} for c in s.scalars(select(Clause).where(Clause.document_id == id))]
        try:
            result = analyze(policy, clauses)
        except Exception as exc:
            logging.getLogger("clause").exception("Review failed")
            raise HTTPException(502, "Analysis failed. Check provider configuration and retry.") from exc
        r = Review(id=str(uuid4()), document_id=id, policy=policy.model_dump(), result=result)
        s.add(r); s.commit()
        return {"id": r.id, "policy_snapshot": r.policy, **result}
