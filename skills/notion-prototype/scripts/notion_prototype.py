# /// script
# requires-python = ">=3.11"
# dependencies = ["keyring==25.7.0"]
# ///
"""클릭형 HTML 프로토타입의 Notion 게시 명령"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from prototype import Client, Error, Store, authenticate, inspect_page, notion_id, publish, read_html, read_token, recover


def parser():
    root = argparse.ArgumentParser(description='HTML 프로토타입을 기존 Notion 페이지에 게시·갱신')
    root.add_argument('--state-dir', type=Path)
    commands = root.add_subparsers(dest='command', required=True)
    auth = commands.add_parser('auth', help='본인의 터미널에서 키체인에 토큰 등록')
    auth.add_argument('--profile', default='default')
    preview = commands.add_parser('preview', help='로컬 파일 검사, Notion에 전송하지 않음')
    preview.add_argument('file', type=Path)
    status = commands.add_parser('status', help='로컬 게시 이력 조회')
    status.add_argument('--page')
    for name in ('publish', 'inspect', 'recover'):
        command = commands.add_parser(name)
        command.add_argument('--page', required=True)
        command.add_argument('--profile', default='default')
        if name == 'publish':
            command.add_argument('file', type=Path)
            command.add_argument('--position', choices=['start', 'end'], default='end', help='첫 게시 위치; 갱신은 기존 위치 유지')
        if name == 'recover':
            choice = command.add_mutually_exclusive_group(required=True)
            choice.add_argument('--adopt-block', help='확인한 기존 HTML 블록을 다음 갱신 대상으로 채택')
            choice.add_argument('--confirmed-absent', action='store_true', help='임베드 부재 확인 후 로컬 연결 해제')
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    store = Store(args.state_dir)
    try:
        if args.command == 'auth':
            authenticate(args.profile)
            result = {'status': 'credential_saved', 'profile': args.profile}
        elif args.command == 'preview':
            content = read_html(args.file)
            result = {'status': 'valid_file', 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(), 'note': '파일 검사만 완료. 브라우저에서 화면·클릭 동작을 별도로 확인하세요.'}
        else:
            with store.locked():
                if args.command == 'status':
                    entries = store.load()['entries']
                    result = entries
                    if args.page:
                        result = entries.get(notion_id(args.page), {'status': 'untracked'})
                else:
                    if args.command == 'publish':
                        read_html(args.file)
                    page = notion_id(args.page)
                    client = Client(read_token(args.profile))
                    if args.command == 'inspect':
                        result = inspect_page(client, page)
                    elif args.command == 'publish':
                        result = publish(client, store, args.file, page, args.profile, args.position)
                    else:
                        result = recover(client, store, page, args.profile, args.adopt_block, args.confirmed_absent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Error as error:
        print(str(error), file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError):
        print('파일·이력·API 응답 형식을 확인하세요. 게시 중이었다면 status와 inspect로 상태를 확인하세요.', file=sys.stderr)
    except KeyboardInterrupt:
        print('중단했습니다. 게시 중이었다면 status와 inspect로 상태를 확인하세요.', file=sys.stderr)
        return 130
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
