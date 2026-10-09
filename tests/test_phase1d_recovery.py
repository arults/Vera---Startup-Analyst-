import json, tempfile, unittest
from pathlib import Path
from src.phase1d.recover_republic_us import (canonical_candidate,safe_next,public_api_url,
 store_snapshot,load_snapshot,new_manifest,record_capture,checkpoint,verify,sha256)
class RecoveryTests(unittest.TestCase):
 def test_company_profile_reachable(self): self.assertEqual(canonical_candidate('/companies/example'),'https://republic.com/companies/example')
 def test_portfolio_not_company(self): self.assertIsNone(canonical_candidate('/companies/portfolio'))
 def test_campaign_normalization(self): self.assertEqual(canonical_candidate('https://www.republic.com/example-2020/?utm=x#terms'),'https://republic.com/example-2020')
 def test_external_rejected(self): self.assertIsNone(canonical_candidate('https://evil.example/a'))
 def test_auth_not_candidates(self):
  for u in ['/login','/api/offerings/x','/companies/search']: self.assertIsNone(canonical_candidate(u))
 def test_unsafe_urls(self):
  for u in ['http://republic.com/a','javascript:alert(1)','https://x:y@republic.com/a','https://republic.com:123/a']: self.assertIsNone(canonical_candidate(u))
 def test_updates_not_rounds(self): self.assertIsNone(canonical_candidate('/example/updates/1'))
 def test_same_directory_next(self):
  self.assertTrue(safe_next('?page=2','https://republic.com/funded-ventures'))
  self.assertFalse(safe_next('/login','https://republic.com/funded-ventures'))
  self.assertFalse(safe_next('https://evil.example/funded-ventures','https://republic.com/funded-ventures'))
 def test_public_api_strict(self):
  self.assertTrue(public_api_url('https://republic.com/api/offerings/republic_note_public_deals'))
  self.assertFalse(public_api_url('https://republic.com/api/global-auth/sessions/whoami'))
  self.assertFalse(public_api_url('https://republic.com/api/offerings/republic_note_public_deals?token=x'))
 def test_same_url_different_bodies(self):
  m=new_manifest('x')
  for raw in [b'one',b'two']: record_capture(m,{'url':'x','kind':'directory_dom','sha256':sha256(raw),'candidate_urls':[]})
  self.assertEqual(len(m['captures']),2)
 def test_identical_dedup(self):
  m=new_manifest('x');c={'url':'x','kind':'directory_dom','sha256':sha256(b'x'),'candidate_urls':[]}
  self.assertTrue(record_capture(m,c));self.assertFalse(record_capture(m,c))
 def test_page_not_union_count(self):
  m=new_manifest('x')
  for i,urls in enumerate([['/one','/two'],['/three']]): record_capture(m,{'url':str(i),'kind':'directory_dom','sha256':sha256(str(i).encode()),'candidate_urls':urls})
  self.assertEqual([c['candidate_count'] for c in m['captures']],[2,1]);self.assertEqual(len(m['candidate_urls']),3)
 def test_snapshot_roundtrip(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);h=store_snapshot(p,b'source');self.assertEqual(load_snapshot(p,h),b'source');self.assertEqual(store_snapshot(p,b'source'),h)
 def test_corruption_fails(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);h=store_snapshot(p,b'x');f=p/'snapshots'/f'{h}.json';r=json.loads(f.read_text());r['bytes']=999;f.write_text(json.dumps(r))
   with self.assertRaises(ValueError):load_snapshot(p,h)
 def test_digest_path_traversal(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):load_snapshot(Path(d),'../../x')
 def test_checkpoint_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);m=new_manifest('x');checkpoint(p,m);first=(p/'checkpoints/000001.json').read_bytes();checkpoint(p,m)
   self.assertEqual((p/'checkpoints/000001.json').read_bytes(),first);self.assertTrue((p/'checkpoints/000002.json').exists())
 def test_empty_does_not_promote(self):
  with tempfile.TemporaryDirectory() as d:
   m=new_manifest('x');self.assertEqual(verify(Path(d),m)['passed'],10);self.assertFalse(m['rates_promoted']);self.assertEqual(m['census_status'],'CENSUS_INCOMPLETE')
 def test_tampered_count_fails(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);m=new_manifest('x');h=store_snapshot(p,b'x');record_capture(m,{'url':'x','kind':'directory_dom','sha256':h,'candidate_urls':['/one'],'captured_at':'2026-10-09'})
   m['captures'][0]['candidate_count']=100;self.assertFalse(verify(p,m)['checks']['per_page_not_cumulative'])
 def test_promotion_fails(self):
  with tempfile.TemporaryDirectory() as d:
   m=new_manifest('x');m['rates_promoted']=True;self.assertFalse(verify(Path(d),m)['checks']['no_rate_promotion'])
if __name__=='__main__':unittest.main()
