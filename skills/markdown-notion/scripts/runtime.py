"""로컬 저장소, 키체인, Notion HTTP 통신"""

import contextlib
import fcntl
import getpass
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request

from core import Error

SERVICE = 'markdown-notion'
VERSION = '2026-03-11'


def keychain():
    if sys.platform != 'darwin':
        raise Error('인증정보 저장·조회는 macOS 키체인에서만 지원합니다.')
    from keyring.backends.macOS import Keyring
    return Keyring()


def authenticate(profile):
    if not sys.stdin.isatty():
        raise Error('본인의 터미널에서 auth 명령을 실행하세요. 토큰을 명령 인자나 채팅으로 전달하지 마세요.')
    token = getpass.getpass('Notion 내부 연결 토큰 (화면에 표시되지 않음): ').strip()
    if not token or any(c.isspace() for c in token):
        raise Error('공백 없는 토큰이 필요합니다.')
    try:
        keychain().set_password(SERVICE, profile, token)
    except Error:
        raise
    except Exception:
        raise Error('키체인 저장에 실패했습니다. macOS 키체인 접근 권한을 확인하세요.') from None


def read_token(profile):
    try:
        token = keychain().get_password(SERVICE, profile)
    except Error:
        raise
    except Exception:
        raise Error('키체인을 읽지 못했습니다. macOS 키체인 접근 권한을 확인하세요.') from None
    if not token:
        raise Error('토큰이 없습니다. 본인의 터미널에서 auth 명령을 먼저 실행하세요.')
    return token


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, token):
        self._token = token
        self._opener = urllib.request.build_opener(NoRedirect)

    def request(self, method, path, payload=None):
        request = urllib.request.Request(
            'https://api.notion.com/v1/' + path,
            data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode(),
            headers={'Authorization': 'Bearer ' + self._token, 'Notion-Version': VERSION, 'Content-Type': 'application/json'},
            method=method,
        )
        try:
            with self._opener.open(request, timeout=60) as response:
                result = json.load(response)
            if not isinstance(result, dict) or result.get('object') == 'async_task':
                raise Error('예상하지 못한 API 응답입니다. 게시 결과를 확인하세요.')
            return result
        except urllib.error.HTTPError as exc:
            messages = {
                400: '요청 형식·속성·본문 크기를 확인하세요.',
                401: '토큰을 확인하세요.',
                403: '연결의 읽기·삽입·수정 권한을 확인하세요.',
                404: '대상이 없거나 연결에 접근 권한이 없습니다.',
                429: '요청 한도에 도달했습니다. 잠시 뒤 결과를 확인하세요.',
            }
            raise Error(f'Notion HTTP {exc.code}: ' + messages.get(exc.code, '요청에 실패했습니다. 게시 결과를 확인하세요.')) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise Error('Notion 통신 또는 응답 해석에 실패했습니다. 쓰기 요청은 자동 재시도하지 않습니다.') from None


def load_json(path, default):
    if not path.exists():
        return default
    try:
        value = json.loads(path.read_text())
    except (ValueError, OSError):
        raise Error('로컬 설정 또는 게시 이력 파일을 읽지 못했습니다.') from None
    if not isinstance(value, dict):
        raise Error('로컬 설정 또는 게시 이력 파일 형식이 잘못되었습니다.')
    return value


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.write-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Store:
    def __init__(self, config_dir=None, state_dir=None):
        self.config_dir = Path(config_dir or Path.home() / '.config/markdown-notion').expanduser()
        self.state_dir = Path(state_dir or Path.home() / '.local/share/markdown-notion').expanduser()

    @contextlib.contextmanager
    def locked(self):
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.state_dir / 'lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, 'w') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Error('다른 게시 작업이 진행 중입니다.') from None
            yield

    def config(self):
        return load_json(self.config_dir / 'config.json', {'targets': {}})

    def save_config(self, value):
        save_json(self.config_dir / 'config.json', value)

    def state(self):
        return load_json(self.state_dir / 'state.json', {'entries': {}})

    def save_state(self, value):
        save_json(self.state_dir / 'state.json', value)
