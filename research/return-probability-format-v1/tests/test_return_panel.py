"""Synthetic structure tests only; numbers below are not investment estimates."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('validator', ROOT / 'tools/validate_return_panel.py')
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)

class ReturnPanelTests(unittest.TestCase):
    def setUp(self):
        self.panel = json.loads((ROOT / 'examples/return-panel-abstention-v1.json').read_text())

    def synthetic_numeric(self):
        p = copy.deepcopy(self.panel)
        p['analysis_identity'] = 'SYNTHETIC SOFTWARE TEST ONLY; no investment interpretation'
        p['calibration_status'] = 'PARTIALLY_CALIBRATED'
        p['basis_complete'] = False
        p['basis_blocking_gaps'] = ['Synthetic draft fixture, not a publishable estimate.']
        p['provenance'] = {k:'Synthetic test metadata only; not real evidence.' for k in V.PROVENANCE_FIELDS}
        for row, prob in zip(p['thresholds'], [.4, .3, .2, .1]):
            row.update(status='ESTIMATED', probability=prob, blocking_gaps=[], source_ids=['synthetic-test'], assumptions='Synthetic structural fixture, not a real claim.', interval={'lower':prob/2,'upper':prob+.1,'kind':'sensitivity','coverage':None,'method':'Synthetic envelope','interpretation':'Software test only; not confidence or calibrated bounds.'})
        return p

    def test_abstention_valid(self):
        self.assertEqual(V.validate(self.panel), [])
    def test_synthetic_numeric_structure_valid(self):
        self.assertEqual(V.validate(self.synthetic_numeric()), [])
    def test_required_thresholds(self):
        self.panel['thresholds'][1]['threshold'] = 20
        self.assertTrue(V.validate(self.panel))
    def test_unknown_not_zero(self):
        self.panel['thresholds'][0]['probability'] = 0
        self.assertTrue(V.validate(self.panel))
    def test_abstention_requires_gap(self):
        self.panel['thresholds'][0]['blocking_gaps'] = []
        self.assertTrue(V.validate(self.panel))
    def test_uncalibrated_numeric_rejected(self):
        p=self.synthetic_numeric(); p['calibration_status']='UNCALIBRATED'
        self.assertTrue(V.validate(p))
    def test_increasing_probability_rejected(self):
        p=self.synthetic_numeric(); p['thresholds'][1]['probability']=.5
        self.assertTrue(V.validate(p))
    def test_increasing_envelope_rejected(self):
        p=self.synthetic_numeric(); p['thresholds'][1]['interval']['upper']=.9
        self.assertTrue(V.validate(p))
    def test_invalid_domains(self):
        for value in (True, -0.1, 1.1, float('nan'), float('inf'), '0.2'):
            p=self.synthetic_numeric(); p['thresholds'][0]['probability']=value
            self.assertTrue(V.validate(p), repr(value))
    def test_judgment_not_statistical_coverage(self):
        p=self.synthetic_numeric(); p['thresholds'][0]['interval'].update(kind='judgment', coverage=.9)
        self.assertTrue(V.validate(p))
    def test_statistical_coverage_required(self):
        p=self.synthetic_numeric(); p['thresholds'][0]['interval']['kind']='credible'
        self.assertTrue(V.validate(p))
    def test_completed_review_needs_provenance(self):
        self.panel['thresholds'][0]['reviews']['jev']['status']='COMPLETED'
        self.assertTrue(V.validate(self.panel))
    def test_missing_numeric_provenance(self):
        p=self.synthetic_numeric(); del p['provenance']['failures_missingness_censoring']
        self.assertTrue(V.validate(p))
    def test_numeric_blocker_rejected(self):
        p=self.synthetic_numeric(); p['thresholds'][0]['blocking_gaps']=['Missing entry terms']
        self.assertTrue(V.validate(p))
    def test_range_only_allowed(self):
        p=self.synthetic_numeric()
        for row in p['thresholds']: row['probability']=None
        self.assertEqual(V.validate(p), [])
    def test_malformed_enums_return_errors(self):
        for field in ("calibration_status",):
            p=self.synthetic_numeric(); p[field]=[]
            self.assertTrue(V.validate(p))
        for field in ("status",):
            p=self.synthetic_numeric(); p["thresholds"][0][field]={}
            self.assertTrue(V.validate(p))
        p=self.synthetic_numeric(); p["thresholds"][0]["interval"]["kind"]=[]
        self.assertTrue(V.validate(p))
        p=self.synthetic_numeric(); p["thresholds"][0]["reviews"]["jev"]["scope"]={}
        self.assertTrue(V.validate(p))
    def test_abstention_requires_explicit_null_fields(self):
        del self.panel["thresholds"][0]["probability"]
        self.assertTrue(V.validate(self.panel))
    def synthetic_release(self):
        p=self.synthetic_numeric(); p.update(publication_state='RELEASED', basis_complete=True, basis_blocking_gaps=[])
        for row in p['thresholds']:
            for review in row['reviews'].values():
                review.update(status='COMPLETED', scope='company_estimate', result='PASS', reviewer='SYNTHETIC TEST REVIEWER', timestamp='2026-10-11T00:00:00Z', input_version=p['provenance']['input_artifact_version'], model_version=p['provenance']['model_version'], resolution='SYNTHETIC TEST ONLY; no actual company review.', material_blockers=[])
        return p
    def test_release_requires_reviews(self):
        p=self.synthetic_numeric(); p.update(publication_state='RELEASED', basis_complete=True, basis_blocking_gaps=[])
        self.assertTrue(V.validate(p))
    def test_synthetic_release_structure(self):
        self.assertEqual(V.validate(self.synthetic_release()), [])
    def test_release_requires_actual_scope_versions_pass(self):
        for field,value in [('scope','generic_method'),('input_version','stale'),('model_version','stale'),('result','HOLD'),('material_blockers',['Missing terms'])]:
            p=self.synthetic_release(); p['thresholds'][0]['reviews']['jev'][field]=value
            self.assertTrue(V.validate(p),field)
    def test_release_requires_complete_basis(self):
        for field,value in [('basis_complete',False),('basis_complete','true'),('basis_blocking_gaps',['Missing evidence'])]:
            p=self.synthetic_release(); p[field]=value
            self.assertTrue(V.validate(p),field)
    def test_bad_shapes_return_errors(self):
        for p in (None, [], {}, {'thresholds':[None]*4}):
            self.assertTrue(V.validate(p))

if __name__ == '__main__':
    unittest.main()
