#!/usr/bin/env python3
"""Narrow, immutable-review-bound adapter for two observed research rows.

This is not a generic source-semantic adjudicator. Original source semantics were
independently reviewed upstream; this adapter authenticates the exact reviewed
bytes, verifies the scoped decisions, and preserves every downstream hold.
"""
from pathlib import Path
from datetime import date
from decimal import Decimal
import argparse,copy,gzip,hashlib,json,os,tempfile

ROOT=Path(__file__).resolve().parents[1]
MANIFEST_SHA256='8d1153317a3defdcf1157adbd032282f1ff7ef86bff3a3a20c7b31decb47825d'
VERSION='0.3.0'
APPROVED={
 'https://republic.com/phantom-phood': {'native_id':2045,'domain':'phantomphood.com','hq':'149 New Montgomery Street','series':'Series 2023','series_page':46},
 'https://republic.com/stockcard': {'native_id':1759,'domain':'stockcard.io','hq':'2372 Morse Ave','series':'Series 2022','series_page':59}}

class AdmissionError(ValueError):pass
def require(condition,reason):
    if not condition:raise AdmissionError(reason)
def sha(data):return hashlib.sha256(data).hexdigest()
def encode(value):return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()

def frozen_schema_errors(record,schema):
    """Validate every keyword used by the pinned schema, without third-party deps.

    This is intentionally not a general JSON Schema implementation. A new schema
    keyword fails closed until this reviewed adapter is explicitly revised.
    """
    allowed={'type','minLength','format','enum','minimum','maximum','exclusiveMinimum','items','uniqueItems'}
    errors=[]
    for name in schema['required']:
        if name not in record:errors.append(name+':missing')
    type_check={'null':lambda v:v is None,'string':lambda v:isinstance(v,str),'integer':lambda v:(isinstance(v,int) and not isinstance(v,bool)) or (isinstance(v,float) and v.is_integer()),'number':lambda v:isinstance(v,(int,float)) and not isinstance(v,bool),'array':lambda v:isinstance(v,list)}
    for name,rules in schema['properties'].items():
        require(set(rules)<=allowed,'unsupported_frozen_schema_keyword:'+name)
        if name not in record:continue
        value=record[name]
        types=rules.get('type',[]);types=[types] if isinstance(types,str) else types
        if types and not any(type_check[t](value) for t in types):errors.append(name+':type');continue
        if 'enum' in rules and value not in rules['enum']:errors.append(name+':enum')
        if value is None:continue
        if isinstance(value,str):
            if len(value)<rules.get('minLength',0):errors.append(name+':length')
            if rules.get('format')=='date':
                try:
                    parsed=date.fromisoformat(value)
                    if parsed.isoformat()!=value:errors.append(name+':date_format')
                except ValueError:errors.append(name+':date_format')
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            for key,good in [('minimum',lambda x:value>=x),('maximum',lambda x:value<=x),('exclusiveMinimum',lambda x:value>x)]:
                if key in rules and not good(rules[key]):errors.append(name+':'+key)
        if isinstance(value,list):
            if rules.get('uniqueItems') and len(value)!=len(set(value)):errors.append(name+':duplicate')
            if 'items' in rules:
                require(set(rules['items'])=={'enum'},'unsupported_array_schema')
                if any(x not in rules['items']['enum'] for x in value):errors.append(name+':item')
    return errors

def load_bundle(manifest_path=ROOT/'inputs/frozen-input-manifest.json',source_root=None,source_map_path=None):
    raw=Path(manifest_path).read_bytes();require(sha(raw)==MANIFEST_SHA256,'frozen_manifest_changed')
    manifest=json.loads(raw);data={};bytes_by_key={}
    if source_root is None:
        source_root=next((p for p in [ROOT,*ROOT.parents] if (p/'data/phase1d').is_dir()),None)
    if source_map_path is None and source_root is None:
        convenience=ROOT.parent/'admission-adapter-local-source-map.json'
        if convenience.is_file():source_map_path=convenience
    local_map=json.loads(Path(source_map_path).read_text())['sources'] if source_map_path else {}
    for key,item in manifest['inputs'].items():
        if item['kind']=='packaged':
            path=ROOT/item['path'];encoding='raw';expected=item['sha256']
        elif source_root is not None:
            path=Path(source_root)/item['repository_path'];encoding=item['encoding'];expected=item['raw_sha256']
        else:
            require(item['repository_path'] in local_map,'source_root_or_map_required:'+key)
            entry=local_map[item['repository_path']];path=Path(source_map_path).parent/entry['path'];encoding=entry['encoding'];expected=item['raw_sha256']
        try:content=path.read_bytes()
        except FileNotFoundError as exc:raise AdmissionError('source_missing:'+key) from exc
        if encoding=='gzip':content=gzip.decompress(content)
        require(sha(content)==expected,'source_digest_changed:'+key)
        bytes_by_key[key]=content
        if key in {'matrix','decisions','review','source_fields','schema','jev_final_request','jev_final_response','independent_source_checks','portable_normalization_review','normalization_report'}:data[key]=json.loads(content)
    data['manifest']=manifest;data['raw']=bytes_by_key
    return data

def validate_bundle(b):
    require(sha(encode(b['manifest']))==MANIFEST_SHA256,'parsed_manifest_changed')
    for key,item in b['manifest']['inputs'].items():
        require(key in b['raw'] and sha(b['raw'][key])==item.get('sha256',item.get('raw_sha256')),'loaded_input_digest_changed:'+key)
        if key in b and key not in {'manifest','raw'}:
            require(b[key]==json.loads(b['raw'][key]),'parsed_input_changed:'+key)
    m=b['matrix'];d=b['decisions'];review=b['review'];mh=sha(b['raw']['matrix'])
    normalization=b['portable_normalization_review']
    require(normalization['semantic_equivalence_accepted'],'portable_semantic_equivalence_not_accepted')
    for key in ['matrix','decisions']:
        require(normalization['inputs'][key]['portable_sha256']==sha(b['raw'][key]),'portable_review_hash_mismatch:'+key)
        require(normalization['inputs'][key]==b['normalization_report']['inputs'][key] or all(normalization['inputs'][key][x]==b['normalization_report']['inputs'][key][x] for x in ['upstream_original_sha256','portable_sha256']),'normalization_lineage_mismatch:'+key)
    require(normalization['inputs']['matrix']['upstream_original_sha256']==review['matrix_sha256']==d['matrix_sha256'],'review_matrix_hash_mismatch')
    require(d['review_sha256']==sha(b['raw']['review']),'decision_review_hash_mismatch')
    require(d['final_jev_sha256']==sha(b['raw']['jev_final_response']),'decision_jev_hash_mismatch')
    require(not review['exact_corrections_required'],'review_has_required_corrections')
    require(d['status']=='TWO_INDEPENDENTLY_REVIEWED_JEV_ACCEPTED_BOUNDED_RECOMMENDATIONS','decision_not_accepted')
    require(b['jev_final_response']['structuredContent']['answers']['record_disposition']['choice']=='accept_two_bounded_observed_rounds','jev_not_accepted')
    require(not d['phase_complete'] and not d['global_plateau'] and d['new_production_rounds_admitted']==d['numeric_rates_promoted']==0,'forbidden_global_promotion')
    require(len(m['proposals'])==len(d['recommendations'])==len(review['checks'])==2,'extra_or_missing_reviewed_row')
    require(sorted(r['campaign_url'] for r in m['proposals'])==sorted(APPROVED),'unapproved_campaign')
    require(sorted(r['campaign_url'] for r in d['recommendations'])==sorted(APPROVED),'unapproved_decision_campaign')
    require(len({r['proposal']['round_id'] for r in m['proposals']})==2,'duplicate_canonical_round')
    require(len({r['native_offering_id'] for r in m['proposals']})==2,'duplicate_native_representation')
    for r in m['proposals']:
        url=r['campaign_url'];cfg=APPROVED[url];p=r['proposal'];slug=url.rsplit('/',1)[1]
        rec=next(x for x in d['recommendations'] if x['campaign_url']==url)
        rv=next((x for x in review['checks'] if x['campaign']==url),None)
        require(rv and rv['bounded_identity_and_round_independently_accepted'] and rv['layer_b_predicate'],'independent_identity_or_funding_review_missing')
        require(rec['proposal']==p,'reviewed_decision_row_mismatch')
        require(not rec['production_admitted'] and not rec['estimation_eligible'] and not p['estimation_eligible'],'record_promotion_forbidden')
        require(r['native_offering_id']==cfg['native_id'] and p['source_url']==url,'native_or_source_identity_changed')
        require(r['native_state']=='finalized','reviewed_finalized_evidence_changed')
        criteria={c['id']:c for c in r['criteria']}
        require(all(criteria[k]['status'].startswith('PASS') for k in ['native_campaign','company_identity','instrument_series','economic_round','launch_cohort','funded_completion','amendments_aliases','primary_field']),'reviewed_stage_not_passed')
        require('domain' in criteria['company_identity']['evidence'] and 'headquarters' in criteria['company_identity']['evidence'],'reviewed_medium_bundle_missing')
        require('Portal CIK is not issuer CIK' in criteria['company_identity']['evidence'],'intermediary_issuer_scope_lost')
        require(not frozen_schema_errors(p,b['schema']),'original_schema_failure')
        require(p['status']=='funded_completed' and p['completion_date'],'aggregate_completed_status_missing')
        require(date.fromisoformat(p['first_live_date']).year==p['offering_year'] and 2020<=p['offering_year']<=2025,'launch_cohort_invalid')
        require(p['first_live_date']<=p['completion_date']<='2026-10-10','completion_chronology_invalid')
        launches=[day for day,text in r['native_milestones'] if text.startswith('Launched')]
        completions=[day for day,text in r['native_milestones'] if text.startswith('Successfully raised')]
        require(launches==[p['first_live_date']] and completions==[p['completion_date']],'milestone_date_mismatch')
        fields=next(x for x in b['source_fields'] if x['campaign_url']==url)
        ff={x['field']:x for x in fields['fields']}
        require(ff['issuer_name']['value']==p['legal_name'],'issuer_identity_mismatch')
        require(ff['security_series']['value']==cfg['series'] and cfg['series'] in p['instrument_type'],'instrument_series_mismatch')
        require(p['comparable_valuation'] is None,'safe_cap_used_as_priced_valuation')
        require(p['valuation_cap']==ff['valuation_cap_usd']['value'] and p.get('valuation_cap_scope','').startswith('Original offered instrument only;'),'offered_cap_scope_changed')
        require(p.get('cohost_platforms')==[] and p.get('cohost_platforms_scope','').startswith('None positively identified'),'cohost_absence_scope_changed')
        amount=Decimal(r['source_amounts']['timeline_successfully_raised_usd'])
        require(amount>0 and amount>=Decimal(ff['target_offering_amount_usd']['value']),'positive_completed_funding_missing')
        require(Decimal(str(p['amount_raised']))==amount,'raised_amount_precision_changed')
        require(r['known_frame_size']==693 and r['known_frame_identity_matches']==[url],'bounded_collision_review_changed')
        for kind in ['native_parent','native_timeline','form_c']:
            src=r['sources'][kind];require(sha(b['raw'][slug+'__'+kind])==src['raw_sha256'],'bound_source_hash_mismatch:'+kind)
        if slug=='phantom-phood':
            require(r['source_amounts']['campaign_hero_usd']=='39645' and r['source_amounts']['phantom_footer_usd']=='39646' and str(amount)=='39645.69','phantom_display_precision_lost')
            require('conditional' in r['round_scope_note'] and any('Whether the conditional' in x for x in r['unknowns']),'conditional_financing_scope_lost')
    return True

def build_ledger(b):
    validate_bundle(b);m=b['matrix'];companies=[];rounds=[];stages=[];unresolved=[]
    for r in sorted(m['proposals'],key=lambda x:x['campaign_url']):
        p=r['proposal'];url=r['campaign_url'];cfg=APPROVED[url]
        fields=next(x for x in b['source_fields'] if x['campaign_url']==url)
        ff={x['field']:x for x in fields['fields']}
        identity={'legal_name':p['legal_name'],'domain':cfg['domain'],'headquarters':cfg['hq'],'proof_scope':'Exact reviewed parent-to-document match; not complete cross-platform identity discovery.','anchors':[{'source':'form_c','physical_page':1,'exact_anchor':p['legal_name']},{'source':'form_c','physical_page':1,'exact_anchor':cfg['domain']},{'source':'form_c','physical_page':1,'exact_anchor':cfg['hq']},{'source':'form_c','physical_page':8,'exact_anchor':url}],'review_sha256':sha(b['raw']['review'])}
        portable_sources={}
        for kind in ['native_parent','native_timeline','form_c']:
            src=r['sources'][kind];portable_sources[kind]={k:v for k,v in src.items() if k not in {'local_path','original_field_ledger'}}
            portable_sources[kind]['repository_path']=b['manifest']['inputs'][url.rsplit('/',1)[1]+'__'+kind]['repository_path']
        portable_sources['frozen_rules']={'spec_repository_path':'docs/PHASE_1C_SPEC.md','spec_sha256':sha(b['raw']['spec']),'schema_repository_path':'schema/phase1c_round.schema.json','schema_sha256':sha(b['raw']['schema'])}
        companies.append({'canonical_company_id':p['canonical_company_id'],'identity_status':'MANUAL_MEDIUM_BUNDLE_SECOND_REVIEW_ACCEPTED','identity_evidence':identity,'source_evidence':portable_sources})
        core={k:copy.deepcopy(v) for k,v in p.items() if k not in {'valuation_cap','valuation_cap_scope','cohost_platforms_scope','canonical_id_scope','amount_raised_scope'}}
        # Existing RoundRecord consumers cannot mistake original offered caps for operative caps.
        core['valuation_cap']=None;core['comparable_valuation']=None
        core.update({'offered_valuation_cap':{'amount_usd':ff['valuation_cap_usd']['value'],'scope':'ORIGINAL_OFFERED_INSTRUMENT_ONLY','source_sha256':r['sources']['form_c']['raw_sha256'],'physical_pdf_page':ff['valuation_cap_usd']['physical_pdf_page'],'exact_anchor':ff['valuation_cap_usd']['anchor'],'operative_individual_terms_verified':False},'funding_observation':{'status':'PLATFORM_OBSERVED_AGGREGATE_COMPLETED','amount_usd_decimal':r['source_amounts']['timeline_successfully_raised_usd'],'amount_scope':p['amount_raised_scope'],'all_source_displays':r['source_amounts'],'native_milestones':r['native_milestones'],'native_state':r['native_state'],'native_offering_id':r['native_offering_id'],'individual_executed_contracts_verified':False},'cohost_review':{'status':'NONE_POSITIVELY_IDENTIFIED_IN_BOUNDED_KNOWN_FRAME','known_frame_size':r['known_frame_size'],'matched_urls':r['known_frame_identity_matches'],'complete_cross_platform_deduplication':False},'round_scope_note':r['round_scope_note'],'document_field_anchors':fields['fields'],'source_evidence':r['sources'],'identity_evidence':identity,'canonical_id_scope':p['canonical_id_scope'],'admission_status':'CANONICAL_OBSERVED_RESEARCH_LAYER_B_ADMITTED','research_layer_b_eligible':True,'production_admitted':False,'estimation_eligible':False,'historical_census_complete':False,'outcome_adjudication':'UNKNOWN_NOT_PERFORMED','unknowns':r['unknowns']})
        core['source_evidence']=portable_sources
        rounds.append(core)
        stages.append({'round_id':p['round_id'],'stages':{'source_integrity':'VERIFIED_EXACT_REVIEWED_BYTES','company_identity':'ACCEPTED_SECOND_REVIEW','observed_economic_round':'ACCEPTED_BOUNDED_SOURCE_SCOPE','launch_and_completion':'ACCEPTED_NATIVE_MILESTONES','aggregate_funded_status':'ACCEPTED_PLATFORM_OBSERVED','primary_field':'ACCEPTED_SECOND_REVIEW','canonical_research_ledger':'ADMITTED_LOCAL_ONLY','outcomes':'UNKNOWN_NOT_ADJUDICATED','historical_coverage':'INCOMPLETE','estimator':'SUPPRESSED'}})
        for reason in r['unknowns']:unresolved.append({'round_id':p['round_id'],'status':'UNKNOWN','issue':reason,'does_not_erase_earlier_accepted_stages':True})
    return {'schema_version':'vera.phase1d.canonical-research-ledger.v'+VERSION,'adapter_scope':'EXACT_TWO_REVIEWED_ROWS_ONLY','input_manifest_sha256':MANIFEST_SHA256,'reviewed_matrix_sha256':sha(b['raw']['matrix']),'upstream_original_matrix_sha256':b['portable_normalization_review']['inputs']['matrix']['upstream_original_sha256'],'portable_normalization_review_sha256':sha(b['raw']['portable_normalization_review']),'independent_review_sha256':sha(b['raw']['review']),'source_semantic_validation':'Bound upstream independent semantic review plus separately reviewed path-only normalization and original source hashes; adapter does not claim a fresh full source audit.','canonical_companies':companies,'canonical_rounds':rounds,'stage_ledger':stages,'unresolved_ledger':unresolved,'cohost_bridges':[],'amendment_bridges':[],'bridge_scope':'No positive pairwise relation established; no same-round evidence invented from absence of a known match.','counts':{'canonical_research_companies':2,'canonical_research_rounds':2,'research_layer_b_rows':2,'production_admissions':0,'estimation_eligible_rows':0},'promotion_gates':{'historical_census_complete':False,'outcome_coverage_complete':False,'rates_promoted':False,'priors_changed':False,'phase_complete':False,'global_plateau':False},'synthetic_test_rows_included':False}

def atomic_create(path,payload):
    """Publish a complete new file without ever replacing an existing release."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        require(path.read_bytes()==payload,'immutable_output_conflict')
        return 'UNCHANGED_IDENTICAL_REPLAY'
    fd,name=tempfile.mkstemp(prefix='.admission-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        try:os.link(name,path)
        except FileExistsError:
            require(path.read_bytes()==payload,'immutable_output_race_conflict')
            return 'UNCHANGED_IDENTICAL_REPLAY'
        return 'CREATED_IMMUTABLE_RELEASE'
    finally:Path(name).unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'releases/v0.3.0/canonical-research-ledger.json');parser.add_argument('--source-root',type=Path);parser.add_argument('--source-map',type=Path);args=parser.parse_args()
    b=load_bundle(source_root=args.source_root,source_map_path=args.source_map);payload=encode(build_ledger(b));result=atomic_create(args.output,payload)
    # Verify all frozen dependencies again after the operation.
    load_bundle(source_root=args.source_root,source_map_path=args.source_map)
    print(json.dumps({'result':result,'path':str(args.output),'sha256':sha(payload),'research_rows':2,'production_admissions':0,'estimation_eligible':0}))
if __name__=='__main__':main()
