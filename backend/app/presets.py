from .schemas import DEFAULT_POLICY, Policy, Rule

PRESETS = [
    {'id':'procurement', 'description':'The five baseline rules used in the guided demo.', 'policy':DEFAULT_POLICY},
    {'id':'privacy', 'description':'Explore processor obligations, incident response, AI training, and subprocessors.',
     'policy':Policy(name='Privacy & AI review', rules=[
        Rule(id='training',name='AI training rights',instruction='Customer inputs and outputs must not be used for model training without explicit consent.',keywords=['training','train','input','output'],severity='high'),
        Rule(id='incident',name='Incident response',instruction='Processor must notify the customer of a personal data breach within 72 hours.',keywords=['breach','incident','notification','security'],severity='high'),
        Rule(id='subprocessor',name='Subprocessors',instruction='Subprocessor changes require notice and an opportunity to object.',keywords=['subprocessor','sub-processor','object','notice']),
        Rule(id='deletion',name='Return and deletion',instruction='Customer data must be returned or deleted when the agreement ends, subject to lawful retention.',keywords=['delete','deletion','return','retention']),
        Rule(id='audit',name='Audit rights',instruction='Customer must have a mechanism to verify processor security and compliance.',keywords=['audit','inspection','compliance','certification']),
    ])},
    {'id':'commercial', 'description':'Explore termination, assignment, exclusivity, liability, and IP.',
     'policy':Policy(name='Commercial diligence', rules=[
        Rule(id='termination',name='Termination rights',instruction='Customer should be able to terminate for material breach after a reasonable cure period.',keywords=['termination','terminate','breach','cure']),
        Rule(id='assignment',name='Assignment',instruction='Assignment should require counterparty consent, with reasonable exceptions for reorganizations.',keywords=['assignment','assign','consent']),
        Rule(id='exclusivity',name='Exclusivity',instruction='No exclusive dealing or noncompetition obligation should be imposed without express approval.',keywords=['exclusive','exclusivity','non-compete','competition'],severity='high'),
        Rule(id='liability_review',name='Liability exclusions',instruction='Review liability caps and carve-outs for confidentiality, fraud, and intellectual property.',keywords=['liability','cap','damages','unlimited'],severity='high'),
        Rule(id='ownership',name='IP ownership',instruction='Customer should retain its preexisting intellectual property and receive rights needed for deliverables.',keywords=['ownership','intellectual','license','deliverables']),
    ])},
    {'id':'nda', 'description':'Explore confidentiality scope, use restrictions, duration, and exclusions.',
     'policy':Policy(name='Confidentiality review',rules=[
        Rule(id='scope',name='Confidential information',instruction='The definition should clearly identify protected information and permitted disclosures.',keywords=['confidential','information','disclosure']),
        Rule(id='purpose',name='Permitted use',instruction='Recipient may use confidential information only for the agreed purpose.',keywords=['purpose','use','recipient']),
        Rule(id='exclusions',name='Exclusions',instruction='Public, previously known, independently developed, and lawfully received information should be excluded.',keywords=['public','independent','known','exclusion']),
        Rule(id='duration',name='Duration',instruction='Confidentiality obligations should have a defined duration, with appropriate treatment of trade secrets.',keywords=['duration','term','years','trade secret']),
    ])},
]
