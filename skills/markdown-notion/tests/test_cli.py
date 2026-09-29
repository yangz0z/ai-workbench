import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from core import Error
from notion_publish import api_for, dispatch, parser
from publishing import source_path
from runtime import SERVICE, Store


class CliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.docs = self.base / 'my documents'
        self.docs.mkdir()
        self.store = Store(self.base / 'config', self.base / 'state')

    def test_uninitialized_root_rejected(self):
        with self.assertRaisesRegex(Error, 'init --root'):
            source_path(self.store.config(), 'note.md')

    def test_init_accepts_arbitrary_folder_and_preserves_targets(self):
        self.store.save_config({'targets': {'notes': {'profile': 'work'}}})
        args = parser().parse_args(['init', '--root', str(self.docs)])
        dispatch(args, self.store)
        self.assertEqual(self.store.config()['root'], str(self.docs.resolve()))
        self.assertEqual(self.store.config()['targets']['notes']['profile'], 'work')

    def test_profile_selects_credential(self):
        with patch('notion_publish.read_token', return_value='mock-token') as read, patch('notion_publish.Client') as client:
            api_for({'profile': 'work'})
            read.assert_called_once_with('work')
            client.assert_called_once_with('mock-token')

    def test_isolated_storage_namespace(self):
        with patch('runtime.Path.home', return_value=self.base):
            store = Store()
        self.assertEqual(SERVICE, 'markdown-notion')
        self.assertEqual(store.config_dir, self.base / '.config/markdown-notion')
        self.assertEqual(store.state_dir, self.base / '.local/share/markdown-notion')
        self.assertEqual(parser().parse_args(['auth']).profile, 'default')

    def test_cli_preview_without_credentials_and_body_hidden(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/notion_publish.py'
        prefix = [sys.executable, str(script), '--config-dir', str(self.store.config_dir), '--state-dir', str(self.store.state_dir)]
        initialized = subprocess.run([*prefix, 'init', '--root', str(self.docs)], capture_output=True, text=True)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        config = self.store.config()
        config['targets']['notes'] = {'data_source_id': '11111111-1111-1111-1111-111111111111', 'profile': 'unused', 'mapping': {'title': 'Name'}}
        self.store.save_config(config)
        (self.docs / 'note.md').write_text('# Example\nprivate body', encoding='utf-8')
        result = subprocess.run([*prefix, 'preview', 'note.md', '--target', 'notes'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['title'], 'Example')
        self.assertNotIn('private body', result.stdout)
        self.assertFalse(json.loads(result.stdout)['properties_validated'])


if __name__ == '__main__':
    unittest.main()
