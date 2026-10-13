"""CP9 regression fixtures are synthetic tests, never empirical observations."""
import gzip,json,unittest
from bs4 import BeautifulSoup
from src.phase1d.reconcile_cp9_timelines import decode,milestones,ROOT,BASE,OUT
from src.phase1d.capture_cp9_documents_posts import public_visible
from src.phase1d.capture_cp9_evidence import safe,sha

def card(day,year,title):
 return '<article class="offerings-updates-shared-milestone_card"><div class="offerings-updates-shared-milestone_card__date-day-month">'+day+'</div><div class="offerings-updates-shared-milestone_card__date-year">'+year+'</div><div class="offerings-updates-shared-milestone_card__title">'+title+'</div></article>'
def payload(first=('Dec 21','2020'),last=('Apr 16','2021')):
 html='<div class="offerings-show-update_section">'+card(*first,'Launched 🚀')+card(*last,'Successfully raised $100')+'</div>'
 return json.dumps({'update_section':html}).encode()
def parse(raw):
 html,soup=decode(raw);return milestones(html,soup)

class CP9Tests(unittest.TestCase):
 def test_first_live_not_close_year(self):self.assertEqual(parse(payload())[:2],('2020-12-21','2021-04-16'))
 def test_bad_json_rejected(self):
  with self.assertRaises(ValueError):decode(b'<html>Not JSON</html>')
 def test_missing_envelope_rejected(self):
  with self.assertRaises(ValueError):decode(b'{}')
 def test_wrong_envelope_type_rejected(self):
  with self.assertRaises(ValueError):decode(b'{"update_section":12}')
 def test_wrong_native_wrapper_rejected(self):
  with self.assertRaises(ValueError):decode(b'{"update_section":"<html>login</html>"}')
 def test_duplicate_milestone_rejected(self):
  x=json.loads(payload());x['update_section']+=card('Dec 22','2020','Launched again')
  with self.assertRaises(ValueError):parse(json.dumps(x).encode())
 def test_reverse_chronology_rejected(self):
  with self.assertRaises(ValueError):parse(payload(('Dec 21','2021'),('Apr 16','2020')))
 def test_after_cutoff_rejected(self):
  with self.assertRaises(ValueError):parse(payload(('Dec 21','2020'),('Apr 16','2027')))
 def test_missing_date_rejected(self):
  x=json.loads(payload());x['update_section']=x['update_section'].replace('date-year','missing-year')
  with self.assertRaises((ValueError,KeyError)):parse(json.dumps(x).encode())
 def test_hidden_form_text_excluded(self):
  out=public_visible(b'<body><p>PUBLIC EVENT</p><form><textarea>SECRET HIDDEN DRAFT</textarea></form><script>token</script></body>')
  self.assertIn('PUBLIC EVENT',out);self.assertNotIn('SECRET',out);self.assertNotIn('token',out)
 def test_hidden_css_excluded(self):
  out=public_visible(b'<body><div hidden>HIDDEN1</div><div class="u-hidden">HIDDEN2</div><p style="display: none">HIDDEN3</p><p>VISIBLE</p></body>')
  self.assertEqual(out,'VISIBLE')
 def test_public_visible_not_erased(self):self.assertIn('Revenue increased',public_visible(b'<article><p>Revenue increased</p></article>'))
 def test_outside_host_rejected(self):self.assertFalse(safe('https://republic.com.attacker.example/'))
 def test_userinfo_rejected(self):self.assertFalse(safe('https://name:password@republic.com/trusst'))
 def test_actual_frozen_timeline_hashes_and_oracles(self):
  rows=json.loads((BASE/'native_update_fragment_candidates.json').read_text())
  self.assertEqual(len(rows),122)
  for row in rows:
   raw=gzip.decompress((ROOT/row['source_path']).read_bytes());self.assertEqual(sha(raw),row['source_sha256']);self.assertEqual(len(parse(raw)[2]),2)
 def test_corrected_view_does_not_promote_or_claim_census(self):
  if not (OUT/'summary.json').exists():self.skipTest('Reconciled view is not present on this earlier commit')
  x=json.loads((OUT/'summary.json').read_text());self.assertFalse(x['census_complete']);self.assertFalse(x['rates_promoted']);self.assertFalse(x['research_plateau']);self.assertEqual(x['new_live_requests_this_reconciliation'],0)
if __name__=='__main__':unittest.main()
