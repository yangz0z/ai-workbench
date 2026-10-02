import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from core import Error, convert, properties, notion_id


class ConversionTest(unittest.TestCase):
    def test_frontmatter_and_code_are_preserved(self):
        meta, body, warnings = convert('---\ntitle: 회고\ntags: [개발]\n---\n# 회고\n\n[[문서|다른 글]]\n\n```python\nprint("[[문서]]")\n```\n')
        self.assertEqual(meta['title'], '회고')
        self.assertIn('다른 글', body)
        self.assertIn('print("[[문서]]")', body)
        self.assertNotIn('tags:', body)

    def test_local_images_block_publish(self):
        with self.assertRaises(Error):
            convert('# 제목\n![이미지](assets/a.png)')

    def test_dataview_requires_notice(self):
        _, body, warnings = convert('# 제목\n```dataview\nTABLE status\n```')
        self.assertNotIn('TABLE status', body)
        self.assertTrue(warnings)

    def test_table_uses_notion_table_markup(self):
        _, body, _ = convert('# 제목\n\n| 항목 | 값 |\n| --- | --- |\n| A | B |')
        self.assertIn('<table>', body)
        self.assertIn('<td>A</td>', body)

    def test_table_inline_code_keeps_wiki_literal(self):
        _, body, _ = convert('# 제목\n\n| 코드 |\n| --- |\n| `[[그대로]]` |')
        self.assertIn('<td>`[[그대로]]`</td>', body)

    def test_table_cells_use_notion_markdown_not_html_tags(self):
        # Notion 본문 교체 API는 표 칸 안의 HTML 태그(<code>, <strong> 등)를 거부함
        _, body, _ = convert('# 제목\n\n| 항목 | 값 |\n| --- | --- |\n| `next_start_at` | **굵게**, *기울임*, [링크](https://example.com) |')
        self.assertIn('<td>`next_start_at`</td>', body)
        self.assertIn('<td>**굵게**, *기울임*, [링크](https://example.com)</td>', body)
        for tag in ('<code>', '<strong>', '<em>', '<a '):
            self.assertNotIn(tag, body)

    def test_table_cell_escapes_angle_brackets_and_pipes(self):
        _, body, _ = convert('# 제목\n\n| 식 |\n| --- |\n| a < b \\| c `x<y` |')
        self.assertIn('<td>a &lt; b | c `x<y`</td>', body)

    def test_multiselect_requires_list(self):
        schema = {'이름': {'type': 'title'}, '태그': {'type': 'multi_select', 'multi_select': {'options': [{'name': '개발'}]}}}
        with self.assertRaises(Error):
            properties({'title': '회고', 'tags': '개발'}, {'title': '이름', 'tags': '태그'}, schema)

    def test_invalid_date_rejected(self):
        schema = {'이름': {'type': 'title'}, '작성일': {'type': 'date'}}
        with self.assertRaises(Error):
            properties({'title': '회고', 'created': '2026-99-99'}, {'title': '이름', 'created': '작성일'}, schema)

    def test_url_id_ignores_view_id(self):
        self.assertEqual(notion_id('https://www.notion.so/Title-0123456789abcdef0123456789abcdef?v=ffffffffffffffffffffffffffffffff'), '01234567-89ab-cdef-0123-456789abcdef')

    def test_mapping_uses_actual_schema(self):
        schema = {'이름': {'id': 'title', 'type': 'title'}, '주제': {'id': 'x', 'type': 'multi_select', 'multi_select': {'options': [{'name': '개발'}]}}}
        value = properties({'title': '회고', 'tags': ['개발']}, {'title': '이름', 'tags': '주제'}, schema)
        self.assertEqual(value['주제'], {'multi_select': [{'name': '개발'}]})

    def test_unknown_select_option_is_not_created(self):
        schema = {'이름': {'type': 'title'}, '분류': {'type': 'select', 'select': {'options': [{'name': '회고'}]}}}
        with self.assertRaises(Error):
            properties({'title': '제목', 'type': 'note'}, {'title': '이름', 'type': '분류'}, schema)


if __name__ == '__main__':
    unittest.main()
