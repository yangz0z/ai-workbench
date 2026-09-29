import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from core import Error
from publishing import move, publish, recover, register
from runtime import Store

A = '11111111-1111-1111-1111-111111111111'
B = '22222222-2222-2222-2222-222222222222'
DATABASE = '33333333-3333-3333-3333-333333333333'
SCHEMA = {'이름': {'type': 'title'}}


class FakeClient:
    def __init__(self):
        self.pages = {}
        self.calls = []
        self.fail_create = False
        self.fail_body = False

    def request(self, method, path, payload=None):
        self.calls.append((method, path, copy.deepcopy(payload)))
        if path.startswith('databases/'):
            return {'data_sources': [{'id': A, 'name': '업무'}]}
        if path.startswith('data_sources/'):
            return {'properties': copy.deepcopy(SCHEMA)}
        if method == 'POST':
            if self.fail_create:
                raise Error('응답 유실')
            page_id = f'{len(self.pages) + 1:08d}-0000-0000-0000-000000000000'
            self.pages[page_id] = {'id': page_id, 'url': 'https://www.notion.so/' + page_id, 'parent': payload['parent'], 'properties': payload['properties'], 'markdown': payload['markdown']}
            return copy.deepcopy(self.pages[page_id])
        page_id = path.split('/')[1]
        page = self.pages[page_id]
        if method == 'PATCH':
            if path.endswith('/markdown'):
                if self.fail_body:
                    raise Error('본문 갱신 실패')
                page['markdown'] = payload['replace_content']['new_str']
            else:
                page['properties'] = payload['properties']
        return copy.deepcopy(page)


class PublishingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / 'vault'
        self.vault.mkdir()
        self.file = self.vault / 'note.md'
        self.file.write_text('---\ntitle: 회고\n---\n# 회고\n첫 본문')
        self.store = Store(self.root / 'config', self.root / 'state')
        self.store.save_config({'root': str(self.vault), 'targets': {name: {'data_source_id': source, 'mapping': {'title': '이름'}, 'profile': 'default'} for name, source in [('A', A), ('B', B)]}})
        self.client = FakeClient()

    def writes(self):
        return [c for c in self.client.calls if c[0] != 'GET']

    def test_two_targets_create_separate_pages_and_repeat_is_noop(self):
        first = publish(self.client, self.store, 'A', 'note.md')
        second = publish(self.client, self.store, 'B', 'note.md')
        self.assertNotEqual(first['url'], second['url'])
        self.assertEqual(publish(self.client, self.store, 'A', 'note.md')['status'], 'unchanged')
        self.assertEqual(len(self.writes()), 2)

    def test_update_keeps_page_id(self):
        before = publish(self.client, self.store, 'A', 'note.md')
        self.file.write_text('# 바뀐 제목\n바뀐 본문')
        after = publish(self.client, self.store, 'A', 'note.md')
        self.assertEqual(after['url'], before['url'])
        self.assertEqual(after['status'], 'updated')
        self.assertEqual(len(self.client.pages), 1)
        self.assertEqual(next(iter(self.client.pages.values()))['markdown'], '# 바뀐 제목\n바뀐 본문')

    def test_empty_optional_title_uses_filename(self):
        self.file.write_text('---\ntitle:\n---\n제목 없는 본문')
        publish(self.client, self.store, 'A', 'note.md')
        title = next(iter(self.client.pages.values()))['properties']['이름']['title']
        self.assertEqual(title[0]['text']['content'], 'note')

    def test_remote_change_blocks_overwrite_even_when_local_unchanged(self):
        publish(self.client, self.store, 'A', 'note.md')
        next(iter(self.client.pages.values()))['markdown'] = '노션에서 수정'
        with self.assertRaisesRegex(Error, 'Notion에서 수정'):
            publish(self.client, self.store, 'A', 'note.md')
        self.assertEqual(len(self.writes()), 1)

    def test_unknown_create_cannot_repeat_until_recovered(self):
        self.client.fail_create = True
        with self.assertRaises(Error):
            publish(self.client, self.store, 'A', 'note.md')
        self.client.fail_create = False
        with self.assertRaisesRegex(Error, '미확정'):
            publish(self.client, self.store, 'A', 'note.md')
        self.assertEqual(len(self.writes()), 1)
        recover(self.client, self.store, 'A', 'note.md', confirmed_absent=True)
        self.assertEqual(publish(self.client, self.store, 'A', 'note.md')['status'], 'created')

    def test_partial_update_requires_recovery(self):
        first = publish(self.client, self.store, 'A', 'note.md')
        self.file.write_text('# 새 제목\n새 내용')
        self.client.fail_body = True
        with self.assertRaises(Error):
            publish(self.client, self.store, 'A', 'note.md')
        self.client.fail_body = False
        with self.assertRaisesRegex(Error, '미확정'):
            publish(self.client, self.store, 'A', 'note.md')
        recover(self.client, self.store, 'A', 'note.md', first['url'])
        self.assertEqual(publish(self.client, self.store, 'A', 'note.md')['status'], 'updated')

    def test_new_version_preserves_previous_reference(self):
        first = publish(self.client, self.store, 'A', 'note.md')
        second = publish(self.client, self.store, 'A', 'note.md', new_version=True)
        self.assertNotEqual(first['url'], second['url'])
        self.assertEqual(next(iter(self.store.state()['entries'].values()))['history'][0]['url'], first['url'])

    def test_move_retains_existing_page(self):
        first = publish(self.client, self.store, 'A', 'note.md')
        self.file.rename(self.vault / 'moved.md')
        move(self.store, 'A', 'note.md', 'moved.md')
        self.assertEqual(publish(self.client, self.store, 'A', 'moved.md')['url'], first['url'])
        self.assertEqual(len(self.writes()), 1)

    def test_outside_vault_symlink_is_rejected(self):
        outside = self.root / 'secret.md'
        outside.write_text('private')
        self.file.unlink()
        self.file.symlink_to(outside)
        with self.assertRaises(Error):
            publish(self.client, self.store, 'A', 'note.md')
        self.assertEqual(self.writes(), [])

    def test_register_discovers_source_and_title(self):
        result = register(self.client, self.store, '새대상', DATABASE, {})
        self.assertEqual(result['mapping'], {'title': '이름'})
        self.assertEqual(self.store.config()['targets']['새대상']['data_source_id'], A)

    def test_recover_wrong_database_is_rejected(self):
        first = publish(self.client, self.store, 'A', 'note.md')
        with self.assertRaises(Error):
            recover(self.client, self.store, 'B', 'note.md', first['url'])

    def test_local_state_is_private(self):
        publish(self.client, self.store, 'A', 'note.md')
        self.assertEqual((self.store.state_dir / 'state.json').stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
