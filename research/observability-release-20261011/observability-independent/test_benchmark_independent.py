"""Independent, synthetic-only benchmark matching/corruption checks."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
PATH=Path(sys.argv.pop(1)) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else Path(__file__).with_name('synthetic_benchmark.py')
sys.path.insert(0,str(PATH.parent))
spec=importlib.util.spec_from_file_location('benchmark_independent',PATH);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class Checks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.baseline=b.run_benchmark(Path(cls.tmp.name)/'baseline')
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):self.a=copy.deepcopy(self.baseline);self.c=copy.deepcopy(self.baseline)
 def invalid(self,**kw):
  with self.assertRaises(b.vo.TraceError):b.compare(self.a,self.c,**kw)
 def test_same_basis_comparison(self):self.assertEqual(b.compare(self.a,self.c)['regressions'],0)
 def test_no_real_research_claim(self):
  self.assertEqual(self.a['research_quality'],'not_evaluated');self.assertTrue(self.a['synthetic']);self.assertEqual(self.a['metrics_adapter'],'not_run')
 def test_changed_dataset_rejected(self):self.c['dataset_ref']='ver:other';self.invalid()
 def test_changed_evaluator_rejected(self):self.c['evaluator_ref']='ver:other';self.invalid()
 def test_changed_config_requires_explicit_switch(self):self.c['config_ref']='ver:other';self.invalid()
 def test_explicit_config_comparison_retains_change(self):
  self.c['config_ref']='ver:other'
  for row in self.c['cases']:row['config_ref']='ver:other'
  self.assertTrue(b.compare(self.a,self.c,allow_config_change=True)['config_changed'])
 def test_changed_model_rejected(self):self.c['cases'][0]['model_ref']='ver:other';self.invalid()
 def test_changed_input_rejected(self):self.c['cases'][0]['input_ref']='ver:other';self.invalid()
 def test_missing_case_rejected(self):self.c['cases'].pop();self.invalid()
 def test_duplicate_case_rejected(self):self.c['cases'].append(copy.deepcopy(self.c['cases'][0]));self.invalid()
 def test_empty_checks_rejected(self):
  self.a['cases'][0]['checks']={};self.c['cases'][0]['checks']={};self.invalid()
 def test_boolean_only_checks(self):self.c['cases'][0]['checks']['local_work_executed']=1;self.invalid()
 def test_boolean_only_pass_flag(self):self.c['cases'][0]['passed']=1;self.invalid()
 def test_inconsistent_top_pass_rejected(self):self.c['passed']=False;self.invalid()
 def test_regression_identified(self):
  self.c['cases'][0]['checks']['local_work_executed']=False;self.c['cases'][0]['passed']=False;self.c['passed']=False
  result=b.compare(self.a,self.c);self.assertEqual(result['regressions'],1)
if __name__=='__main__':unittest.main(verbosity=2)
