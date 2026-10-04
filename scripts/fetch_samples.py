"""Fetch licensed public contracts and write a reproducible, attributed demo corpus.

Run with backend/.venv Python. Network is used only by this explicit maintenance
command; demo startup seeds the checked-in snapshots without network access.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
import html
from datetime import datetime, timezone
import httpx

ROOT = Path(__file__).resolve().parents[1]
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
TEMPLATES = [
    ("Mutual-NDA", "Mutual-NDA.md", "Mutual nondisclosure agreement", "Confidentiality"),
    ("CSA", "CSA.md", "Cloud service agreement", "Cloud & technology"),
    ("DPA", "DPA.md", "Data processing agreement", "Privacy & security"),
    ("SLA", "sla.md", "Service level agreement", "Cloud & technology"),
    ("PSA", "psa.md", "Professional services agreement", "Services & consulting"),
    ("AI-Addendum", "AI-Addendum.md", "AI addendum", "Privacy & security"),
    ("BAA", "BAA.md", "Business associate agreement", "Privacy & security"),
    ("Software-License-Agreement", "Software-License-Agreement.md", "Software license agreement", "License & IP"),
    ("Pilot-Agreement", "Pilot-Agreement.md", "Pilot agreement", "Cloud & technology"),
    ("Partnership-Agreement", "Partnership-Agreement.md", "Partnership agreement", "Partnership & venture"),
    ("Design-Partner-Agreement", "design-partner-agreement.md", "Design partner agreement", "Cloud & technology"),
]

def category(title):
    title = title.lower()
    for keywords, label in [
        (("hosting", "cloud", "software", "technology"), "Cloud & technology"),
        (("service", "consult", "outsourc"), "Services & consulting"),
        (("licens", "intellectual"), "License & IP"),
        (("supply", "manufactur", "purchase"), "Supply & manufacturing"),
        (("distribut", "resell"), "Distribution"),
        (("confiden", "nondisclosure"), "Confidentiality"),
        (("joint", "partner", "alliance"), "Partnership & venture"),
        (("franchise",), "Franchise"),
        (("sponsor", "promot", "market", "endorse"), "Marketing"),
    ]:
        if any(k in title for k in keywords): return label
    return "Other commercial"

def clean_markdown(text):
    # Plain-text normalization only; no legal language is rewritten.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"(?m)^#{1,6}\s*", "", text)
    text = html.unescape(re.sub(r'<[^>]+>', '', text))
    return text.strip() + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cuad-count', type=int, default=60)
    parser.add_argument('--cache', type=Path)
    args = parser.parse_args()
    out = ROOT / 'samples' / 'public'
    out.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).isoformat()
    entries = []
    existing_path = ROOT / 'samples' / 'manifest.json'
    pins = {x['key']: x for x in json.loads(existing_path.read_text())} if existing_path.exists() else {}
    with httpx.Client(follow_redirects=True, timeout=90) as client:
        def commit(repo, key):
            if key in pins: return pins[key]['upstream_commit']
            if key == 'cuad-source':
                previous = next((x for x in pins.values() if x['collection'] == 'CUAD commercial contracts'), None)
                if previous: return previous['upstream_commit']
            r = client.get(f'https://api.github.com/repos/{repo}/commits/main')
            r.raise_for_status()
            return r.json()['sha']
        def write(key, title, text, **metadata):
            raw = text.encode('utf-8')
            (out / f'{key}.txt').write_bytes(raw)
            entries.append({'key':key,'title':title,'file':f'public/{key}.txt',
                'sha256':hashlib.sha256(raw).hexdigest(),'characters':len(text),
                'retrieved_at':retrieved,'license':'CC BY 4.0','license_url':LICENSE,
                'page_provenance':'Extracted text; original page numbers unavailable.', **metadata})
        for repo, filename, title, group in TEMPLATES:
            key = 'commonpaper-' + repo.lower()
            sha = commit('CommonPaper/' + repo, key)
            url = f'https://raw.githubusercontent.com/CommonPaper/{repo}/{sha}/{filename}'
            r = client.get(url); r.raise_for_status()
            write(key, 'Common Paper — ' + title, clean_markdown(r.text),
                publisher='Common Paper', collection='Common Paper standards', category=group,
                source_url=f'https://github.com/CommonPaper/{repo}/blob/{sha}/{filename}',
                download_url=url, upstream_commit=sha, original_title=filename,
                description='Published standard agreement. Bracketed cover-page variables may be unfilled.',
                attribution='Common Paper and its drafting committee. Licensed CC BY 4.0.',
                transformations='Markdown and inline HTML converted to readable plain text; links retained. No terms rewritten.', annotations=[])
            print('Fetched', title)
        sha = commit('The-Atticus-Project/cuad', 'cuad-source')
        url = f'https://raw.githubusercontent.com/The-Atticus-Project/cuad/{sha}/data.zip'
        if args.cache and args.cache.exists():
            archive = args.cache.read_bytes()
            # Cache content is verified against the current pinned remote archive.
            r = client.get(url); r.raise_for_status()
            if hashlib.sha256(archive).digest() != hashlib.sha256(r.content).digest():
                raise ValueError('Cache differs from pinned CUAD snapshot')
        else:
            r = client.get(url); r.raise_for_status(); archive = r.content
        dataset = json.loads(zipfile.ZipFile(io.BytesIO(archive)).read('CUADv1.json'))['data']
        buckets = {}
        for item in sorted(dataset, key=lambda x: x['title']):
            buckets.setdefault(category(item['title']), []).append(item)
        selected = []
        while len(selected) < min(args.cuad_count, len(dataset)):
            for group in sorted(buckets):
                if buckets[group] and len(selected) < args.cuad_count:
                    selected.append(buckets[group].pop(0))
        for item in selected:
            p = item['paragraphs'][0]
            text = p['context']
            annotations = []
            for question in p['qas']:
                label = question['id'].rsplit('__', 1)[-1]
                answers = []
                for a in question['answers']:
                    if text[a['answer_start']:a['answer_start']+len(a['text'])] != a['text']:
                        raise ValueError('CUAD answer offset mismatch')
                    answers.append({'text':a['text'],'start':a['answer_start']})
                annotations.append({'label':label,'answers':answers,'is_impossible':question['is_impossible']})
            key = 'cuad-' + hashlib.sha256(item['title'].encode()).hexdigest()[:12]
            names = next((a['answers'] for a in annotations if a['label']=='Document Name'), [])
            parties = next((a['answers'] for a in annotations if a['label']=='Parties'), [])
            name = ' '.join(names[0]['text'].split()).strip('"')[:120].title() if names else item['title']
            party = next((' '.join(a['text'].split()).strip('"') for a in parties
                if 12 < len(a['text']) < 100
                and re.search(r'\b(?:inc|corp|company|limited|llc|ltd|university|bank|llp|corporation)\b', a['text'], re.I)
                and not re.search(r'collectively|individually|herein|together|hereinafter|referred', a['text'], re.I)), '')[:80]
            title = name + (' — ' + party if party else '')
            write(key, title, text, publisher='The Atticus Project',
                collection='CUAD commercial contracts', category=category(item['title']),
                source_url=f'https://github.com/The-Atticus-Project/cuad/tree/{sha}',
                download_url=url, upstream_commit=sha, archive_sha256=hashlib.sha256(archive).hexdigest(),
                original_title=item['title'],
                description='Public commercial contract from CUAD, with attorney-supervised clause annotations. Historical terms; not a current vendor policy.',
                attribution='The Atticus Project; Hendrycks, Burns, Chen and Ball (2021). CUAD v1, licensed CC BY 4.0.',
                transformations='Full context text extracted from CUADv1.json. Original pagination unavailable; annotation offsets preserved.', annotations=annotations)
        (ROOT / 'samples' / 'manifest.json').write_text(json.dumps(entries, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        print(f'Wrote {len(entries)} attributed public documents')

if __name__ == '__main__': main()
