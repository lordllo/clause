# Public demo corpus

The bundled snapshots contain **71 public documents**: 11 Common Paper standards and a category-balanced selection of 60 full-context contracts from CUAD v1. These are accompanied by two fictional Clause fixtures stored in `fixtures/`. No real document has been presented as a fictional vendor contract.

## Common Paper

Source: https://github.com/CommonPaper and https://commonpaper.com/standards/

Copyright and attribution: Common Paper and its drafting committee. The standard agreements are released under **Creative Commons Attribution 4.0 International**: https://creativecommons.org/licenses/by/4.0/

Included standards: Mutual NDA, Cloud Service Agreement, Data Processing Agreement, Service Level Agreement, Professional Services Agreement, AI Addendum, Business Associate Agreement, Software License Agreement, Pilot Agreement, Partnership Agreement, and Design Partner Agreement.

Modification notice: Markdown and inline HTML formatting were converted to plain text. Hyperlink targets were retained. Terms were not rewritten and cover-page variables remain unfilled. These are published standards, not executed agreements.

## CUAD

Source: The Atticus Project, https://www.atticusprojectai.org/cuad/ and https://github.com/The-Atticus-Project/cuad

Attribution: Dan Hendrycks, Collin Burns, Anya Chen, and Spencer Ball, **CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review**, NeurIPS Datasets and Benchmarks, 2021. Curated by The Atticus Project with attorney-supervised annotations.

The publisher identifies CUAD v1 as released under **CC BY 4.0**. Individual source contracts are historical publicly filed agreements. The demo includes the full `context` text of each selected contract and its original annotation excerpts and offsets. It does not include fabricated SEC filing links; use the preserved original CUAD title to identify the historical filing. The manifest links to the pinned upstream dataset and records the upstream archive SHA-256.

Modification notice: Text was extracted from `CUADv1.json` without rewriting contractual language. Readable display titles are derived from source Document Name and Parties labels. Original titles, annotation offsets, and publisher attribution are preserved in `manifest.json`. Original pagination is unavailable and the UI labels these documents as extracted text. Parser passage boundaries are application-derived.

## Traceability and refresh

Each public manifest entry records title, original title, publisher, collection, category, pinned upstream commit, source/download URLs, license, attribution, transformations, retrieval time, document SHA-256, and source annotations. The source link for a CUAD document points to the dataset, not a purported original filing.

Run `backend/.venv/Scripts/python.exe scripts/fetch_samples.py` (or the Unix equivalent) from the repository root to reproduce the pinned snapshots. It uses the commits in the existing manifest, makes no authenticated request, and verifies any supplied archive cache against the pinned download. To upgrade upstream versions, review and deliberately update the pins. Startup performs no downloads or provider calls.

Annotations identify clauses for diligence; they are not policy-compliance findings or current legal advice. Common Paper templates contain variables and external cover-page references. CUAD contracts may have outdated terms, redactions, and extraction artifacts. Use the original source and legal review for substantive decisions.
