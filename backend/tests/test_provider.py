from types import SimpleNamespace
import pytest
from app import analysis
from app.schemas import Analysis, Finding, DEFAULT_POLICY

def test_structured_provider_and_verification(monkeypatch):
    clause = {'id':'source','page':3,'heading':'Law','text':'This agreement is governed by the laws of California.'}
    finding = Finding(rule_id='governing_law', status='deviation', explanation='Wrong jurisdiction',action='Request New York.',clause_id='source',quote=clause['text'])
    calls=[]
    def parse(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_parsed=Analysis(findings=[finding]))
    monkeypatch.setenv('ANALYSIS_PROVIDER','openai')
    monkeypatch.setattr(analysis,'OpenAI',lambda **kwargs: SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    policy=DEFAULT_POLICY.model_copy(deep=True);policy.rules=policy.rules[:1]
    result=analysis.analyze(policy,[clause])
    assert result['provider']=='openai'
    assert result['findings'][0]['citation_verified']
    assert result['findings'][0]['page']==3
    assert calls[0]['text_format'] is Analysis

def test_provider_refusal_fails(monkeypatch):
    monkeypatch.setenv('ANALYSIS_PROVIDER','openai')
    monkeypatch.setattr(analysis,'OpenAI',lambda **kwargs: SimpleNamespace(responses=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(output_parsed=None))))
    policy=DEFAULT_POLICY.model_copy(deep=True);policy.rules=policy.rules[:1]
    with pytest.raises(ValueError):
        analysis.analyze(policy,[{'id':'a','page':1,'heading':'Law','text':'Governing law is California.'}])
