"""HTML 검증, Notion 통신, 게시 이력과 복구"""
import contextlib
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener
import uuid

VERSION = '2026-03-11'
SERVICE = 'notion-prototype'


class Error(Exception):
    pass


def notion_id(value):
    text = str(value)
    if '://' in text:
        parsed = urlparse(text)
        if parsed.scheme != 'https' or parsed.hostname not in ('notion.so', 'www.notion.so', 'notion.com', 'www.notion.com', 'app.notion.com'):
            raise Error('Notion 페이지 URL 또는 ID를 지정하세요.')
        text = parsed.path.rstrip('/').split('/')[-1]
    match = re.search(r'([0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$', text)
    if not match:
        raise Error('Notion 페이지 URL 또는 ID를 지정하세요.')
    return str(uuid.UUID(match.group(1)))


def read_html(path):
    path = Path(path).expanduser()
    if path.suffix.lower() not in ('.html', '.htm'):
        raise Error('HTML 파일을 지정하세요.')
    with path.open('rb') as stream:
        content = stream.read(5 * 1024 * 1024 + 1)
    if not content or len(content) > 5 * 1024 * 1024:
        raise Error('비어 있지 않은 5MB 이하 HTML이 필요합니다.')
    try:
        content.decode('utf-8')
    except UnicodeError:
        raise Error('UTF-8 HTML이 필요합니다.') from None
    return content


def keychain():
    if sys.platform != 'darwin':
        raise Error('인증은 macOS 키체인에서만 지원합니다.')
    from keyring.backends.macOS import Keyring
    return Keyring()


def authenticate(profile):
    if not sys.stdin.isatty():
        raise Error('본인의 터미널에서 auth를 실행하세요. 토큰을 채팅이나 명령 인자로 전달하지 마세요.')
    token = getpass.getpass('Notion 내부 연결 토큰 (화면에 표시되지 않음): ').strip()
    if not token or any(c.isspace() for c in token):
        raise Error('공백 없는 토큰이 필요합니다.')
    try:
        keychain().set_password(SERVICE, profile, token)
    except Error:
        raise
    except Exception:
        raise Error('키체인 저장에 실패했습니다.') from None


def read_token(profile):
    try:
        token = keychain().get_password(SERVICE, profile)
    except Error:
        raise
    except Exception:
        raise Error('키체인 접근 권한을 확인하세요.') from None
    if not token:
        raise Error('등록된 토큰이 없습니다. 본인의 터미널에서 auth를 실행하세요.')
    return token


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, token):
        self._token = token
        self._opener = build_opener(NoRedirect)

    def send(self, method, path, data=None, content_type='application/json'):
        request = Request('https://api.notion.com/v1/' + path, data=data, method=method, headers={
            'Authorization': 'Bearer ' + self._token, 'Notion-Version': VERSION, 'Content-Type': content_type,
        })
        try:
            with self._opener.open(request, timeout=60) as response:
                value = json.load(response)
            if not isinstance(value, dict) or value.get('object') == 'async_task':
                raise Error('예상하지 못한 API 응답입니다. inspect와 status로 상태를 확인하세요.')
            return value
        except HTTPError as error:
            raise Error(f'Notion HTTP {error.code}. 권한·요청·게시 상태를 확인하세요. 쓰기를 자동 재시도하지 않습니다.') from None
        except (URLError, OSError, ValueError):
            raise Error('Notion 응답을 확인하지 못했습니다. inspect와 status로 상태를 확인하세요. 자동 재시도하지 않습니다.') from None

    def request(self, method, path, payload=None):
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode()
        return self.send(method, path, data)


def upload_html(client, content, checkpoint):
    upload = client.request('POST', 'file_uploads', {'mode': 'single_part', 'filename': 'prototype.html', 'content_type': 'text/html'})
    upload_id = notion_id(upload['id'])
    checkpoint(upload_id)
    boundary = '----NotionPrototype' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="prototype.html"\r\nContent-Type: text/html\r\n\r\n'.encode() + content + f'\r\n--{boundary}--\r\n'.encode())
    result = client.send('POST', f'file_uploads/{upload_id}/send', body, 'multipart/form-data; boundary=' + boundary)
    if result.get('status') != 'uploaded':
        raise Error('HTML 업로드가 완료되지 않았습니다. status를 확인하세요.')
    return upload_id


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory or Path.home() / '.local/share/notion-prototype').expanduser()

    @contextlib.contextmanager
    def locked(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.directory / 'lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, 'w') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Error('다른 게시 작업이 진행 중입니다.') from None
            yield

    def load(self):
        path = self.directory / 'state.json'
        if not path.exists():
            return {'entries': {}}
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or not isinstance(value.get('entries'), dict):
            raise Error('게시 이력 형식을 확인하세요. 이력을 삭제하지 마세요.')
        return value

    def save(self, value):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, name = tempfile.mkstemp(dir=self.directory, prefix='.write-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.directory / 'state.json')
        finally:
            if os.path.exists(name):
                os.unlink(name)


def children(client, page):
    result = []
    cursor = None
    while True:
        path = f'blocks/{page}/children?page_size=100'
        if cursor:
            path += '&start_cursor=' + notion_id(cursor)
        response = client.request('GET', path)
        result.extend(response['results'])
        if not response.get('has_more'):
            return result
        cursor = response['next_cursor']


def inspect_page(client, page):
    page = notion_id(page)
    return {'page_id': page, 'embeds': [
        {'block_id': b['id'], 'last_edited_time': b['last_edited_time']}
        for b in children(client, page) if b['type'] == 'embed'
    ]}


def check_embed(client, block_id, page):
    block = client.request('GET', f'blocks/{notion_id(block_id)}')
    if block['type'] != 'embed' or block.get('in_trash') or block.get('archived'):
        raise Error('관리 중인 임베드가 삭제되었거나 종류가 변경됐습니다. recover로 연결을 확인하세요.')
    parent = block['parent']
    if parent.get('type') != 'page_id' or notion_id(parent.get('page_id', '')) != page:
        raise Error('이 페이지의 최상위 임베드만 관리할 수 있습니다.')
    return block


def check_profile(entry, profile):
    if entry and entry['profile'] != profile:
        raise Error('게시 이력의 프로필과 다릅니다. status에 표시된 --profile을 사용하세요.')


def publish(client, store, file, page, profile='default', position='end'):
    page = notion_id(page)
    content = read_html(file)
    digest = hashlib.sha256(content).hexdigest()
    state = store.load()
    old = state['entries'].get(page)
    check_profile(old, profile)
    if old and old['status'] == 'pending':
        raise Error('pending 상태입니다. inspect와 status를 확인한 뒤 recover를 실행하세요.')
    current_page = client.request('GET', f'pages/{page}')
    if current_page.get('in_trash') or current_page.get('archived'):
        raise Error('휴지통에 있는 페이지에는 게시할 수 없습니다.')
    if old:
        block = check_embed(client, old['block_id'], page)
        if block['last_edited_time'] != old['last_edited_time']:
            raise Error('Notion 임베드가 변경됐습니다. 원격 내용을 확인한 뒤 recover로 채택하세요.')
        if old.get('sha256') == digest:
            return {'status': 'unchanged', 'page_url': f'https://www.notion.so/{page.replace("-", "")}', 'block_id': old['block_id']}
    baseline = [b['block_id'] for b in inspect_page(client, page)['embeds']]
    if not old and baseline:
        raise Error('기존 임베드가 있습니다. inspect로 확인하고 관리할 HTML만 recover --adopt-block으로 연결하거나 별도 페이지를 사용하세요.')
    entry = {'status': 'pending', 'baseline_ids': baseline, 'page_id': page, 'profile': profile, 'file': str(Path(file).expanduser().resolve()), 'sha256': digest}
    if old:
        entry.update(block_id=old['block_id'], last_edited_time=old['last_edited_time'])
    state['entries'][page] = entry
    store.save(state)

    def checkpoint(upload_id):
        entry['upload_id'] = upload_id
        store.save(state)

    upload_id = upload_html(client, content, checkpoint)
    placement = {'type': position}
    if old:
        placement = {'type': 'after_block', 'after_block': {'id': old['block_id']}}
    payload = {'position': placement, 'children': [{'object': 'block', 'type': 'embed', 'embed': {'type': 'file_upload', 'file_upload': {'id': upload_id}}}]}
    response = client.request('PATCH', f'blocks/{page}/children', payload)
    entry['new_block_id'] = notion_id(response['results'][0]['id'])
    store.save(state)
    new = check_embed(client, entry['new_block_id'], page)
    if old:
        latest = check_embed(client, old['block_id'], page)
        if latest['last_edited_time'] != old['last_edited_time']:
            raise Error('게시 중 기존 임베드가 변경됐습니다. 두 블록을 확인한 뒤 recover를 실행하세요.')
        client.request('DELETE', f'blocks/{old["block_id"]}')
    entry.update(status='ready', block_id=new['id'], last_edited_time=new['last_edited_time'])
    entry.pop('new_block_id', None)
    entry.pop('upload_id', None)
    entry.pop('baseline_ids', None)
    store.save(state)
    status = 'created'
    if old:
        status = 'updated'
    return {'status': status, 'page_url': f'https://www.notion.so/{page.replace("-", "")}', 'block_id': new['id']}


def recover(client, store, page, profile, block_id=None, confirmed_absent=False):
    page = notion_id(page)
    state = store.load()
    previous = state['entries'].get(page)
    check_profile(previous, profile)
    visible = {b['block_id'] for b in inspect_page(client, page)['embeds']}
    if confirmed_absent:
        if visible:
            raise Error('임베드가 남아 있습니다. Notion에서 확인한 뒤 관리할 블록을 채택하세요.')
        state['entries'].pop(page, None)
        store.save(state)
        return {'status': 'cleared', 'page_id': page}
    block_id = notion_id(block_id)
    block = check_embed(client, block_id, page)
    if block_id not in visible:
        raise Error('페이지에서 해당 블록을 확인하지 못했습니다.')
    if previous and previous['status'] == 'pending':
        known = {previous.get('block_id'), previous.get('new_block_id')} - {None, block_id}
        unexpected = visible - set(previous.get('baseline_ids', [])) - {block_id}
        if known & visible or unexpected:
            raise Error('이전 또는 새 임베드가 함께 남아 있습니다. Notion에서 중복을 정리한 뒤 채택하세요.')
    state['entries'][page] = {'status': 'ready', 'page_id': page, 'profile': profile, 'block_id': block_id, 'last_edited_time': block['last_edited_time'], 'sha256': None}
    store.save(state)
    return {'status': 'adopted', 'block_id': block_id, 'next_publish': '현재 블록을 로컬 HTML로 교체'}
