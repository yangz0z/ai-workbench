import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prototype import Error, Store, publish, recover, inspect_page, read_html, notion_id

PAGE='11111111-1111-4111-8111-111111111111'
OLD='22222222-2222-4222-8222-222222222222'
NEW='33333333-3333-4333-8333-333333333333'

class API:
 def __init__(self):
  self.blocks={};self.calls=[];self.fail=None
 def block(self,id):
  return {'id':id,'type':'embed','parent':{'type':'page_id','page_id':PAGE},'last_edited_time':'first','embed':{'url':'https://private.invalid/signed?secret=hidden'}}
 def request(self,method,path,payload=None):
  self.calls.append((method,path,payload))
  if self.fail==(method,path): raise Error('응답 불명')
  if path.startswith('pages/'): return {'id':PAGE,'in_trash':False}
  if method=='GET' and '/children' in path: return {'results':list(copy.deepcopy(self.blocks).values()),'has_more':False}
  if method=='GET': return copy.deepcopy(self.blocks[path.split('/')[1]])
  if method=='PATCH':
   self.blocks[NEW]=self.block(NEW);return {'results':[self.blocks[NEW]]}
  if method=='DELETE': self.blocks.pop(path.split('/')[1]);return {}

class PrototypeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.store=Store(Path(self.tmp.name)/'state');self.file=Path(self.tmp.name)/'example.html';self.file.write_text('<!doctype html><html lang="ko"><body>예시</body></html>')
  self.api=API();self.upload=patch('prototype.upload_html',return_value='44444444-4444-4444-8444-444444444444');self.mock=self.upload.start();self.addCleanup(self.upload.stop)
 def publish(self): return publish(self.api,self.store,self.file,PAGE,'default','start')
 def existing(self):
  self.api.blocks[OLD]=self.api.block(OLD)
  recover(self.api,self.store,PAGE,'default',OLD,False)
 def test_create_at_start_and_idempotence(self):
  self.assertEqual(self.publish()['status'],'created')
  self.assertEqual(self.publish()['status'],'unchanged');self.assertEqual(self.mock.call_count,1)
  self.assertEqual([c for c in self.api.calls if c[0]=='PATCH'][0][2]['position'],{'type':'start'})
 def test_update_creates_before_delete(self):
  self.existing();self.assertEqual(self.publish()['status'],'updated')
  writes=[c for c in self.api.calls if c[0] in ('PATCH','DELETE')]
  self.assertEqual([c[0] for c in writes],['PATCH','DELETE'])
  self.assertEqual(writes[0][2]['position']['after_block']['id'],OLD)
 def test_pending_blocks_retry(self):
  self.api.fail=('PATCH',f'blocks/{PAGE}/children')
  with self.assertRaises(Error):self.publish()
  self.api.fail=None
  with self.assertRaisesRegex(Error,'pending'):self.publish()
  self.assertEqual(self.mock.call_count,1)
 def test_delete_failure_records_both_ids(self):
  self.existing();self.api.fail=('DELETE',f'blocks/{OLD}')
  with self.assertRaises(Error):self.publish()
  state=self.store.load()['entries'][PAGE]
  self.assertEqual(state['block_id'],OLD);self.assertEqual(state['new_block_id'],NEW);self.assertEqual(state['status'],'pending')
 def test_conflict_no_upload(self):
  self.existing();self.api.blocks[OLD]['last_edited_time']='changed'
  with self.assertRaisesRegex(Error,'변경'):self.publish()
  self.mock.assert_not_called()
 def test_deleted_remote_no_recreate(self):
  self.existing();self.api.blocks[OLD]['in_trash']=True
  with self.assertRaises(Error):self.publish()
  self.mock.assert_not_called()
 def test_existing_embed_requires_adoption(self):
  self.api.blocks[OLD]=self.api.block(OLD)
  with self.assertRaises(Error):self.publish()
  self.mock.assert_not_called()
 def test_adopt_wrong_parent(self):
  self.api.blocks[OLD]=self.api.block(OLD);self.api.blocks[OLD]['parent']['page_id']=NEW
  with self.assertRaises(Error):recover(self.api,self.store,PAGE,'default',OLD,False)
 def test_absent_recovery_refuses_remaining_embed(self):
  self.api.blocks[OLD]=self.api.block(OLD)
  with self.assertRaises(Error):recover(self.api,self.store,PAGE,'default',None,True)
 def test_recovery_does_not_hide_known_duplicate(self):
  self.existing();self.api.fail=('DELETE',f'blocks/{OLD}')
  with self.assertRaises(Error):self.publish()
  with self.assertRaises(Error):recover(self.api,self.store,PAGE,'default',NEW,False)
  self.api.blocks.pop(OLD);recover(self.api,self.store,PAGE,'default',NEW,False)
  self.assertEqual(self.store.load()['entries'][PAGE]['block_id'],NEW)
 def test_insert_response_lost_does_not_adopt_old_with_duplicate(self):
  self.existing()
  original=self.api.request
  def lost(method,path,payload=None):
   result=original(method,path,payload)
   if method=='PATCH': raise Error('응답 유실')
   return result
  self.api.request=lost
  with self.assertRaises(Error):self.publish()
  with self.assertRaises(Error):recover(self.api,self.store,PAGE,'default',OLD,False)
 def test_inspect_hides_signed_urls(self):
  self.api.blocks[OLD]=self.api.block(OLD)
  self.assertNotIn('secret',str(inspect_page(self.api,PAGE)))
 def test_profile_mismatch_before_writes(self):
  self.existing()
  with self.assertRaises(Error):publish(self.api,self.store,self.file,PAGE,'other','start')
  self.mock.assert_not_called()
 def test_input_validation(self):
  self.assertEqual(notion_id('https://www.notion.so/Test-'+PAGE.replace('-','')),PAGE)
  with self.assertRaises(Error):notion_id('https://evil.invalid/'+PAGE)
  self.file.write_bytes(b'\xff')
  with self.assertRaises(Error):read_html(self.file)
 def test_state_lock(self):
  with self.store.locked():
   with self.assertRaises(Error):
    with Store(self.store.directory).locked():pass

if __name__=='__main__': unittest.main()
