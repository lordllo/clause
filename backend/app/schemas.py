from typing import Literal
from pydantic import BaseModel, Field

class Rule(BaseModel):
    id: str = Field(pattern=r"^[a-z_]+$", max_length=64)
    name: str = Field(min_length=1, max_length=120)
    instruction: str = Field(min_length=1, max_length=1000)
    keywords: list[str] = Field(min_length=1, max_length=20)
    severity: Literal["high", "medium", "low"] = "medium"

class Policy(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    rules: list[Rule] = Field(min_length=1, max_length=20)

class Finding(BaseModel):
    rule_id: str
    status: Literal["deviation", "compliant", "needs_review"]
    explanation: str
    action: str
    clause_id: str | None
    quote: str | None

class Analysis(BaseModel):
    findings: list[Finding]

DEFAULT_POLICY = Policy(name="Procurement baseline", rules=[
    Rule(id="governing_law", name="Governing law", instruction="Governing law must be New York.", keywords=["governed", "governing", "law"], severity="medium"),
    Rule(id="renewal", name="Renewal notice", instruction="Auto-renewal cancellation window must be at least 30 days.", keywords=["renew", "cancellation", "notice"], severity="medium"),
    Rule(id="liability", name="Liability cap", instruction="Liability cap must not exceed 12 months of fees.", keywords=["liability", "cap", "fees"], severity="high"),
    Rule(id="data_usage", name="Customer data", instruction="Customer data must not be used for model training.", keywords=["training", "train", "machine-learning", "customer data"], severity="high"),
    Rule(id="breach", name="Breach notification", instruction="Vendor must notify security breaches within 72 hours.", keywords=["breach", "security", "hours"], severity="high"),
])
