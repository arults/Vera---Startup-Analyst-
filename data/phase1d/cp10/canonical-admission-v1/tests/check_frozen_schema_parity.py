"""Optional local diagnostic against jsonschema; not a runtime/CI dependency."""
from pathlib import Path
import copy,importlib.util,json
from jsonschema import Draft202012Validator,FormatChecker
P=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('admission_adapter',P/'scripts/admission_adapter.py');A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
b=A.load_bundle();validator=Draft202012Validator(b['schema'],format_checker=FormatChecker());row=b['matrix']['proposals'][0]['proposal'];results=[]
def evaluate(label,record):
    expected=not list(validator.iter_errors(record))
    try:actual=not A.frozen_schema_errors(record,b['schema'])
    except (TypeError,ValueError,KeyError):actual=False
    results.append({'case':label,'jsonschema_valid':expected,'adapter_valid':actual,'agree':expected==actual})
for prop in b['schema']['properties']:
    for index,value in enumerate([None,True,False,0,1,-1,1.5,2023.0,'','bad','2023-02-29','2024-02-29','20230214',[],{},['wefunder'],['wefunder','wefunder'],[{},{}]]):
        candidate=copy.deepcopy(row);candidate[prop]=value;evaluate(prop+':value-'+str(index),candidate)
for prop in b['schema']['required']:
    candidate=copy.deepcopy(row);candidate.pop(prop);evaluate('missing:'+prop,candidate)
for index,r in enumerate(b['matrix']['proposals']):evaluate('accepted:'+str(index),r['proposal'])
candidate=copy.deepcopy(row);candidate['permitted_extra_field']={'arbitrary':'metadata'};evaluate('additional_properties_permitted',candidate)
assert all(r['agree'] for r in results)
report={'scope':'Finite diagnostic coverage of all pinned schema properties and every required-field omission; not proof of a generic JSON Schema implementation.','reference':'jsonschema Draft202012Validator with FormatChecker','cases':len(results),'agreements':sum(r['agree'] for r in results),'mismatches':[],'results':results}
print(json.dumps(report,indent=2))
