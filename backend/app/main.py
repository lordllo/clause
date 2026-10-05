import hashlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from fastapi import FastAPI, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from .db import initialize, Session, Document, Clause, Review, PolicyRecord, SampleRecord
from .demo import seed, summary, annotation_view
from .schemas import Policy, DEFAULT_POLICY
from .parsing import parse
from .analysis import analyze
from .presets import PRESETS
from .hosting import public_demo, validate_hosting, identity, cleanup, throttle, owner, remember, permitted, require_document, upload_quota
from .db import DATA_DIR

@asynccontextmanager
async def lifespan(app):
    validate_hosting()
    initialize()
    if os.getenv('DEMO_SEED', 'true').lower() == 'true':
        seed()
    yield

app = FastAPI(title="Clause API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("WEB_ORIGIN", "http://localhost:3000")], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

@app.middleware('http')
async def demo_boundary(request: Request, call_next):
    if public_demo():
        request.state.demo_owner, cookie = identity(request.cookies.get('clause_demo'))
        if request.method == 'POST':
            origin = request.headers.get('origin')
            if origin and (urlsplit(origin).scheme,urlsplit(origin).netloc) != (request.url.scheme,request.url.netloc):
                return JSONResponse({'detail':'Cross-origin demo writes are disabled.'},status_code=403)
            length = request.headers.get('content-length')
            if length is None: return JSONResponse({'detail':'Content-Length required for demo uploads.'},status_code=411)
            try: size=int(length)
            except ValueError: return JSONResponse({'detail':'Invalid content length.'},status_code=400)
            limit=11*1024*1024 if request.url.path.endswith('/documents') else 64*1024
            if size < 0 or size > limit: return JSONResponse({'detail':'Request exceeds demo size limit.'},status_code=413)
            if not throttle(request): return JSONResponse({'detail':'Demo request limit reached. Try again in a minute.'},status_code=429)
        await run_in_threadpool(cleanup)
    response = await call_next(request)
    if public_demo():
        response.set_cookie('clause_demo',cookie,max_age=3600,httponly=True,secure=os.getenv('DEMO_COOKIE_SECURE','true')=='true',samesite='lax',path='/')
        response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    return response

@app.get("/health")
def health():
    return {"status": "ok", "provider": os.getenv("ANALYSIS_PROVIDER", "demo"), 'public_demo':public_demo()}

@app.get("/policies/default")
def default_policy():
    return DEFAULT_POLICY

@app.get('/policies/presets')
def presets():
    return PRESETS

@app.get("/policies")
def policies(request: Request):
    with Session() as s:
        return [{"id": p.id, **p.body} for p in s.scalars(select(PolicyRecord)) if permitted(s,p.id,request)]

@app.post("/policies", status_code=201)
def save_policy(policy: Policy, request: Request):
    if len({r.id for r in policy.rules}) != len(policy.rules):
        raise HTTPException(422, "Rule IDs must be unique")
    with Session() as s:
        p = PolicyRecord(id=str(uuid4()), body=policy.model_dump())
        s.add(p); remember(s,p.id,'policy',request); s.commit()
        return {"id": p.id, **p.body}

@app.get("/documents")
def documents(request: Request):
    with Session() as s:
        samples = {x.document_id:summary(x) for x in s.scalars(select(SampleRecord))}
        return [{"id": d.id, "name": d.name, "created_at": d.created_at, 'sample':samples.get(d.id)} for d in s.scalars(select(Document).order_by(Document.created_at.desc())) if d.id in samples or permitted(s,d.id,request)]

@app.get('/samples')
def samples():
    with Session() as s:
        return [summary(x) for x in s.scalars(select(SampleRecord))]

@app.post("/documents", status_code=201)
def upload(file: UploadFile, request: Request):
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
    path = Path(DATA_DIR) / 'uploads' / (id + suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    try:
        with Session() as s:
            upload_quota(s,request)
            s.add(Document(id=id, name=name, digest=hashlib.sha256(content).hexdigest(), source_path=str(path)))
            s.flush()
            s.add_all([Clause(document_id=id, **c) for c in clauses]); remember(s,id,'document',request); s.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"id": id, "name": name, "clause_count": len(clauses)}

@app.get("/documents/{id}")
def document(id: str, request: Request):
    with Session() as s:
        require_document(s,id,request)
        d = s.get(Document, id)
        if not d: raise HTTPException(404, "Document not found")
        clauses = [{"id": c.id, "page": c.page, "heading": c.heading, "text": c.text} for c in s.scalars(select(Clause).where(Clause.document_id == id))]
        reviews = [{"id": r.id, "created_at": r.created_at, "policy_snapshot": r.policy, **r.result} for r in s.scalars(select(Review).where(Review.document_id == id).order_by(Review.created_at.desc())) if permitted(s,r.id,request)]
        sample = s.scalar(select(SampleRecord).where(SampleRecord.document_id == id))
        return {"id": id, "name": d.name, "clauses": clauses, "reviews": reviews,
            'sample':summary(sample) if sample else None,
            'annotations':annotation_view(sample.metadata_json, clauses) if sample else []}

@app.get("/documents/{id}/source")
def source(id: str, request: Request):
    with Session() as s:
        require_document(s,id,request)
        d = s.get(Document, id)
        if not d: raise HTTPException(404, "Document not found")
        return FileResponse(d.source_path, filename=d.name, media_type="application/octet-stream")

@app.post("/documents/{id}/reviews", status_code=201)
def review(id: str, policy: Policy, request: Request):
    if len({r.id for r in policy.rules}) != len(policy.rules):
        raise HTTPException(422, "Rule IDs must be unique")
    with Session() as s:
        require_document(s,id,request)
        if not s.get(Document, id): raise HTTPException(404, "Document not found")
        clauses = [{"id": c.id, "page": c.page, "heading": c.heading, "text": c.text} for c in s.scalars(select(Clause).where(Clause.document_id == id))]
        try:
            sample = s.scalar(select(SampleRecord).where(SampleRecord.document_id == id))
            result = analyze(policy, clauses, conservative=bool(sample and not sample.metadata_json.get('fictional')))
        except Exception as exc:
            logging.getLogger("clause").exception("Review failed")
            raise HTTPException(502, "Analysis failed. Check provider configuration and retry.") from exc
        r = Review(id=str(uuid4()), document_id=id, policy=policy.model_dump(), result=result)
        s.add(r); remember(s,r.id,'review',request); s.commit()
        return {"id": r.id, "policy_snapshot": r.policy, **result}

# Single-origin hosting: export Next.js at build time and serve it with this API.
# The local two-process development API remains available at its original paths.
static_dir = os.getenv('STATIC_DIR')
if static_dir:
    hosted = FastAPI(title='Clause hosted demo', lifespan=lifespan)
    hosted.mount('/api', app)
    hosted.mount('/', StaticFiles(directory=static_dir, html=True), name='frontend')
else:
    hosted = app
