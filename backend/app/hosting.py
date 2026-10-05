"""Explicit public-demo mode: bounded, temporary visitor workspaces."""
import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException, Request
from sqlalchemy import select, delete
from .db import DemoAccess, Document, Clause, Review, PolicyRecord, SampleRecord, Session

def public_demo():
    return os.getenv('PUBLIC_DEMO', 'false').lower() == 'true'

TTL = 3600
_limits = {}
_lock = threading.Lock()
_last_cleanup = 0

def validate_hosting():
    if public_demo():
        if os.getenv('ANALYSIS_PROVIDER', 'demo') != 'demo':
            raise RuntimeError('Public demo requires ANALYSIS_PROVIDER=demo.')
        if len(os.getenv('DEMO_SESSION_SECRET', '')) < 32:
            raise RuntimeError('Public demo requires a DEMO_SESSION_SECRET of at least 32 characters.')

def identity(cookie):
    secret = os.getenv('DEMO_SESSION_SECRET', '').encode()
    now = int(time.time())
    if cookie:
        try:
            nonce, issued, signature = cookie.split('.')
            data = f'{nonce}.{issued}'
            valid = hmac.compare_digest(signature, hmac.new(secret, data.encode(), hashlib.sha256).hexdigest())
            if valid and len(nonce) == 64 and 0 <= now-int(issued) < TTL:
                return hashlib.sha256(nonce.encode()).hexdigest(), cookie
        except (ValueError, TypeError):
            pass
    data = f'{secrets.token_hex(32)}.{now}'
    signed = data + '.' + hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()
    return hashlib.sha256(data.split('.')[0].encode()).hexdigest(), signed

def owner(request: Request):
    return getattr(request.state, 'demo_owner', 'local')

def remember(session, id, kind, request):
    if public_demo(): session.add(DemoAccess(resource_id=id, kind=kind, owner=owner(request)))

def permitted(session, id, request):
    if not public_demo(): return True
    access = session.get(DemoAccess, id)
    return bool(access and access.owner in (owner(request), 'public_sample'))

def require_document(session, id, request):
    if public_demo() and not session.scalar(select(SampleRecord).where(SampleRecord.document_id == id)) and not permitted(session,id,request):
        raise HTTPException(404, 'Document not found')

def upload_quota(session, request):
    if not public_demo(): return
    uploads = list(session.scalars(select(DemoAccess).where(DemoAccess.owner==owner(request), DemoAccess.kind=='document')))
    if len(uploads) >= 5: raise HTTPException(429, 'Demo limit: five uploads per one-hour session.')

def throttle(request):
    if request.method != 'POST': return True
    key = (request.client.host if request.client else 'unknown', owner(request))
    now = time.monotonic()
    with _lock:
        if len(_limits) > 10000:
            for stale in [k for k,v in _limits.items() if not v or v[-1] < now-60]: _limits.pop(stale,None)
        if len(_limits) > 10000 and key not in _limits: return False
        queue=_limits.setdefault(key, deque())
        while queue and queue[0] < now-60: queue.popleft()
        if len(queue) >= 20: return False
        queue.append(now)
    return True

def cleanup():
    """Remove only expired visitor-owned demo resources, never original samples."""
    global _last_cleanup
    now=time.monotonic()
    with _lock:
        if now-_last_cleanup < 60: return
        _last_cleanup=now
    cutoff=datetime.now(timezone.utc)-timedelta(seconds=TTL)
    with Session() as session:
        expired=list(session.scalars(select(DemoAccess).where(DemoAccess.owner!='public_sample',DemoAccess.created_at<cutoff)))
        for access in expired:
            if access.kind=='document':
                # Ownership and UUID-generated upload path both verified before deletion.
                document=session.get(Document,access.resource_id)
                if document:
                    path=Path(document.source_path).resolve()
                    root=Path(os.getenv('DATA_DIR','data')).resolve()/'uploads'
                    if path.parent == root and path.stem == document.id:
                        path.unlink(missing_ok=True)
                    session.execute(delete(Review).where(Review.document_id==document.id))
                    session.execute(delete(Clause).where(Clause.document_id==document.id))
                    session.delete(document)
            elif access.kind=='review':
                record=session.get(Review,access.resource_id)
                if record: session.delete(record)
            elif access.kind=='policy':
                record=session.get(PolicyRecord,access.resource_id)
                if record: session.delete(record)
            session.delete(access)
        session.commit()
