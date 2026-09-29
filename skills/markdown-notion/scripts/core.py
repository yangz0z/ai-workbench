"""문서 변환과 데이터베이스 속성 매핑"""

import datetime as dt
import hashlib
import json
import math
import re
import uuid
from urllib.parse import urlsplit

import yaml
from markdown_it import MarkdownIt


class Error(Exception):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def notion_id(value):
    path = urlsplit(value).path if '://' in value else value
    match = re.search(r'([0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})/?$', path)
    if not match:
        raise Error('Notion URL 또는 ID 형식을 확인하세요.')
    return str(uuid.UUID(match.group(1)))


def convert(source, links=None):
    links = links or {}
    warnings = []
    source = source.replace('\r\n', '\n').lstrip('\ufeff')
    meta = {}
    if source.startswith('---\n'):
        match = re.match(r'\A---\n(.*?)\n---(?:\n|$)', source, re.S)
        if not match:
            raise Error('frontmatter의 닫는 ---가 없습니다.')
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            raise Error('frontmatter YAML 형식을 확인하세요.') from None
        if not isinstance(meta, dict):
            raise Error('frontmatter는 키와 값으로 구성해야 합니다.')
        source = source[match.end():]
    parser = MarkdownIt('commonmark', {'html': True}).enable('table')
    tokens = parser.parse(source)
    lines = source.splitlines(keepends=True)
    protected = set()
    replacements = {}
    for i, token in enumerate(tokens):
        if token.type in ('html_block', 'html_inline'):
            raise Error('직접 작성한 HTML은 지원하지 않습니다. Markdown으로 바꿔주세요.')
        if token.type in ('fence', 'code_block'):
            start, end = token.map
            protected.update(range(start, end))
            language = token.info.strip().split()[0] if token.info.strip() else ''
            if language in ('dataview', 'dataviewjs'):
                replacements[start] = (end, '')
                warnings.append('Dataview 쿼리 제외')
            elif language == 'mermaid':
                warnings.append('Mermaid를 코드로 보존')
        if token.type == 'table_open':
            start, end = token.map
            j = i + 1
            while tokens[j].type != 'table_close':
                j += 1
            table = parser.renderer.render(tokens[i:j + 1], parser.options, {})
            table = table.replace('<thead>', '').replace('</thead>', '').replace('<tbody>', '').replace('</tbody>', '')
            table = re.sub(r'<th(?: style="[^"]*")?>', '<td>', table).replace('</th>', '</td>')
            table = re.sub(r'<td style="[^"]*">', '<td>', table)
            replacements[start] = (end, table)
        for child in token.children or []:
            if child.type == 'html_inline':
                raise Error('직접 작성한 HTML은 지원하지 않습니다.')
            if child.type in ('image', 'link_open'):
                url = child.attrGet('src' if child.type == 'image' else 'href') or ''
                if urlsplit(url).scheme not in ('http', 'https', 'mailto') and not url.startswith('#'):
                    raise Error('로컬 이미지·첨부파일·상대 링크는 지원하지 않습니다. 공개 URL 또는 위키링크를 사용하세요.')

    def wiki(match):
        value = match.group(1)
        target, _, label = value.partition('|')
        label = label or target
        url = links.get(target.removesuffix('.md'))
        if url:
            return f'[{label}]({url})'
        warnings.append('미게시 위키링크를 텍스트로 변환')
        return label

    def inline(text):
        parts = re.split(r'(`+[^`]*`+|<code>.*?</code>)', text, flags=re.S)
        for i in range(0, len(parts), 2):
            if re.search(r'!\[\[', parts[i]):
                raise Error('Obsidian 임베드·로컬 첨부파일은 지원하지 않습니다.')
            parts[i] = re.sub(r'\[\[([^\]\n]+)\]\]', wiki, parts[i])
            if re.search(r'`?\$?=\s*dv\.', parts[i]):
                warnings.append('인라인 Dataview는 실행하지 않음')
        return ''.join(parts)

    output = []
    i = 0
    while i < len(lines):
        if i in replacements:
            end, value = replacements[i]
            output.append(inline(value))
            i = end
        else:
            output.append(lines[i] if i in protected else inline(lines[i]))
            i += 1
    body = ''.join(output).strip()
    if not meta.get('title'):
        heading = next((tokens[i + 1].content for i, t in enumerate(tokens[:-1]) if t.type == 'heading_open' and t.tag == 'h1'), None)
        if heading:
            meta = {**meta, 'title': heading}
    if not body:
        raise Error('게시할 본문이 없습니다.')
    if len(body.encode()) > 400_000:
        raise Error('본문이 너무 큽니다. 문서를 나눠 게시하세요.')
    return meta, body, sorted(set(warnings))


def rich_text(value):
    text = str(value)
    return [{'type': 'text', 'text': {'content': text[i:i + 2000]}} for i in range(0, len(text), 2000)]


def validate_mapping(mapping, schema):
    if 'title' not in mapping or schema.get(mapping['title'], {}).get('type') != 'title':
        raise Error('title을 데이터베이스의 제목 속성에 연결해야 합니다.')
    if len(set(mapping.values())) != len(mapping):
        raise Error('여러 필드를 같은 Notion 속성에 연결할 수 없습니다.')
    allowed = {'title', 'rich_text', 'select', 'multi_select', 'status', 'date', 'checkbox', 'number', 'url'}
    for target in mapping.values():
        if schema.get(target, {}).get('type') not in allowed:
            raise Error(f'속성이 없거나 지원하지 않는 타입입니다: {target}')


def properties(meta, mapping, schema):
    validate_mapping(mapping, schema)
    result = {}
    for field, target in mapping.items():
        if field not in meta:
            continue
        value = meta[field]
        prop = schema[target]
        kind = prop['type']
        if kind == 'title' and (not isinstance(value, str) or not value.strip()):
            raise Error('제목은 비어 있지 않은 문자열이어야 합니다.')
        if kind in ('title', 'rich_text'):
            if isinstance(value, (list, dict)):
                raise Error(f'{field}: 문자열이 필요합니다.')
            encoded = rich_text('' if value is None else value)
            if len(encoded) > 100:
                raise Error(f'{field}: 속성 값이 너무 깁니다.')
        elif kind in ('select', 'multi_select', 'status'):
            values = value if kind == 'multi_select' else ([] if value is None else [value])
            if values is None:
                values = []
            options = {o['name'] for o in prop[kind].get('options', [])}
            if not isinstance(values, list) or any(not isinstance(v, str) or v not in options for v in values):
                raise Error(f'{field}: Notion에 이미 등록된 선택값을 사용하세요.')
            encoded = [{'name': v} for v in dict.fromkeys(values)]
            if kind != 'multi_select':
                encoded = encoded[0] if encoded else None
        elif kind == 'date':
            if value is None or value == '':
                encoded = None
            else:
                text = value.isoformat() if isinstance(value, (dt.date, dt.datetime)) else str(value)
                try:
                    dt.datetime.fromisoformat(text)
                except ValueError:
                    raise Error(f'{field}: ISO 날짜 형식이 필요합니다.') from None
                encoded = {'start': text}
        elif kind == 'checkbox':
            if not isinstance(value, bool):
                raise Error(f'{field}: true 또는 false가 필요합니다.')
            encoded = value
        elif kind == 'number':
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise Error(f'{field}: 유한한 숫자가 필요합니다.')
            encoded = value
        else:
            if value is not None and (not isinstance(value, str) or urlsplit(value).scheme not in ('https', 'http')):
                raise Error(f'{field}: HTTP(S) URL이 필요합니다.')
            encoded = value
        result[target] = {kind: encoded}
    if mapping['title'] not in result:
        raise Error('문서 제목이 없습니다.')
    return result
