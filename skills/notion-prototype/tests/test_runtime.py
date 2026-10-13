import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prototype import Client, Error, NoRedirect, authenticate, read_html, upload_html, children
from notion_prototype import main

class RuntimeTests(unittest.TestCase):
 def test_upload_saves_id_before_send(self):
  events=[];client=Mock();upload_id='44444444-4444-4444-8444-444444444444'
  client.request.return_value={'id':upload_id}
  def send(method,path,data,kind):
   self.assertEqual(events,[upload_id]);self.assertIn(b'name="file"',data);self.assertIn('한글'.encode(),data);self.assertIn('multipart/form-data',kind)
   return {'status':'uploaded'}
  client.send.side_effect=send
  self.assertEqual(upload_html(client,'한글'.encode(),events.append),upload_id)
 def test_http_error_never_prints_token_or_body(self):
  client=Client('SECRET_TOKEN');client._opener.open=Mock(side_effect=HTTPError('https://api.notion.com',403,'SECRET_BODY',{},None))
  with self.assertRaises(Error) as caught:client.request('GET','pages/example')
  self.assertNotIn('SECRET',str(caught.exception));self.assertIn('403',str(caught.exception));self.assertEqual(client._opener.open.call_count,1)
 def test_redirect_blocked(self):
  self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://other.invalid'))
 def test_auth_not_agent_terminal(self):
  with patch('prototype.sys.stdin.isatty',return_value=False),patch('prototype.keychain') as keychain:
   with self.assertRaises(Error):authenticate('default')
   keychain.assert_not_called()
 def test_preview_without_credentials(self):
  with tempfile.TemporaryDirectory() as directory:
   file=Path(directory)/'preview.html';file.write_text('<html>예시</html>')
   output=io.StringIO()
   with patch('notion_prototype.read_token') as token,contextlib.redirect_stdout(output):
    self.assertEqual(main(['preview',str(file)]),0)
    token.assert_not_called()
   self.assertIn('valid_file',output.getvalue());self.assertNotIn('<html>',output.getvalue())
 def test_oversize_and_empty(self):
  with tempfile.TemporaryDirectory() as directory:
   file=Path(directory)/'example.html'
   for value in (b'',b'x'*(5*1024*1024+1)):
    file.write_bytes(value)
    with self.assertRaises(Error):read_html(file)
 def test_pagination(self):
  client=Mock();cursor='55555555-5555-4555-8555-555555555555'
  client.request.side_effect=[{'results':[{'id':'one'}],'has_more':True,'next_cursor':cursor},{'results':[{'id':'two'}],'has_more':False}]
  self.assertEqual(len(children(client,'11111111-1111-4111-8111-111111111111')),2)
  self.assertIn(cursor,client.request.call_args.args[1])

if __name__=='__main__':unittest.main()
