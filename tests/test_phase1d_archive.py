import unittest
from src.phase1d.normalize_republic_us_archive import month_bounds, cents, normalize, research_state
URL='https://republic.com/api/offerings/republic_note_public_deals'
def source(rows):return {'captured_at':'2026-10-09T05:15:56Z','responses':[{'url':URL,'status':200,'body':rows}]}
def row(**kwargs):return dict({'slug':'example-2020','name':'Example','deadline':'Feb 2020','raised_cents':0,'valuation_cap_cents':100000000,'instrument':'Crowd SAFE'},**kwargs)
class ArchiveTests(unittest.TestCase):
 def test_leap_bounds(self):self.assertEqual(month_bounds('Feb 2020'),('2020-02-01','2020-02-29'))
 def test_nonleap_bounds(self):self.assertEqual(month_bounds('Feb 2021'),('2021-02-01','2021-02-28'))
 def test_unresolved_date(self):
  for x in [None,'2020','bad 2020','Jan 9999','Jan 2020 extra']:self.assertEqual(month_bounds(x),(None,None))
 def test_cents_keep_zero(self):self.assertEqual(cents(0),0);self.assertIsNone(cents(None))
 def test_bad_cents(self):
  for x in [True,False,1.1,-1,'100']:
   with self.assertRaises(ValueError):cents(x)
 def test_valid_row(self):
  cs,qs,s=normalize(source([row()]),'hash');self.assertEqual(len(cs),1);self.assertFalse(qs);self.assertEqual(s['gates']['passed'],15)
 def test_empty_fails_evidence_gate(self):
  cs,qs,s=normalize(source([]),'hash');self.assertFalse(s['gates']['checks']['nonempty_source'])
 def test_auth_ignored(self):
  doc=source([row()]);doc['responses'][0]['url']='https://republic.com/api/global-auth/sessions/whoami';self.assertEqual(normalize(doc,'h')[2]['source_rows'],0)
 def test_403_ignored(self):
  doc=source([row()]);doc['responses'][0]['status']=403;self.assertEqual(normalize(doc,'h')[2]['source_rows'],0)
 def test_bad_body_fails(self):
  doc=source({});
  with self.assertRaises(ValueError):normalize(doc,'h')
 def test_invalid_slug_quarantined(self):
  cs,qs,s=normalize(source([row(slug='../login')]),'h');self.assertFalse(cs);self.assertEqual(len(qs),1)
 def test_bad_money_quarantined(self):
  cs,qs,s=normalize(source([row(raised_cents=True)]),'h');self.assertEqual(s['rejected_rows'],1)
 def test_no_date_or_valuation_substitution(self):
  cs,_,_=normalize(source([row()]),'h');c=cs[0]
  for f in ['first_live_date','successful_close_date','offering_year','priced_valuation_cents','canonical_company_id']:self.assertIsNone(c[f])
  self.assertFalse(c['estimation_eligible'])
 def test_same_name_not_company_match(self):
  cs,_,_=normalize(source([row(),row(slug='second')]),'h');self.assertEqual(len(cs),2);self.assertTrue(all(c['canonical_company_id'] is None for c in cs))
 def test_duplicates_retained_flagged(self):
  cs,_,s=normalize(source([row(),row()]),'h');self.assertEqual(len(cs),2);self.assertEqual(s['duplicate_source_rows'],2);self.assertEqual(len({c['candidate_id'] for c in cs}),2)
 def test_conflicting_slug_flagged(self):
  cs,_,s=normalize(source([row(),row(raised_cents=500)]),'h');self.assertEqual(s['conflicting_slugs'],1);self.assertTrue(all(c['slug_conflict'] for c in cs))
 def test_deterministic(self):self.assertEqual(normalize(source([row()]),'h'),normalize(source([row()]),'h'))
 def test_zero_capture_not_success(self):
  self.assertEqual(research_state({'capture_count':0,'errors':[{'error':'403'}]}),'ACCESS_BLOCKED')
  self.assertEqual(research_state({'capture_count':0,'errors':[]}), 'NO_EVIDENCE')
 def test_capture_not_census(self):self.assertEqual(research_state({'capture_count':1}), 'PARTIAL_NATIVE_EVIDENCE_NOT_CENSUS')
if __name__=='__main__':unittest.main()
