import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from core import Error
from runtime import Client, NoRedirect, authenticate


class RuntimeTest(unittest.TestCase):
    def test_http_error_does_not_expose_secret_or_body(self):
        token = 'test-secret-do-not-output'
        client = Client(token)
        client._opener = Mock()
        client._opener.open.side_effect = urllib.error.HTTPError('https://api.notion.com/v1/pages', 400, token, {}, io.BytesIO(token.encode()))
        with self.assertRaises(Error) as caught:
            client.request('POST', 'pages', {'markdown': 'private-body'})
        self.assertNotIn(token, str(caught.exception))
        self.assertNotIn('private-body', str(caught.exception))
        client._opener.open.assert_called_once()

    def test_redirect_never_forwards_authorization(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example/'))

    def test_auth_rejects_noninteractive_input(self):
        with patch('runtime.sys.stdin.isatty', return_value=False), patch('runtime.getpass.getpass') as prompt:
            with self.assertRaises(Error):
                authenticate('personal')
            prompt.assert_not_called()

    def test_keychain_error_does_not_print_token(self):
        with patch('runtime.sys.stdin.isatty', return_value=True), patch('runtime.getpass.getpass', return_value='test-secret'), patch('runtime.keychain') as backend:
            backend.return_value.set_password.side_effect = RuntimeError('test-secret')
            with self.assertRaises(Error) as caught:
                authenticate('personal')
            self.assertNotIn('test-secret', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
