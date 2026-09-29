# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML==6.0.3", "markdown-it-py==4.0.0", "keyring==25.7.0"]
# ///
"""Markdown 문서의 Notion 데이터베이스 게시 명령"""

import argparse
import json
from pathlib import Path
import sys

from core import Error, validate_mapping
from publishing import move, prepare, publish, recover, register, target_config
from runtime import Client, Store, authenticate, read_token


def parser():
    root = argparse.ArgumentParser(description='로컬 Markdown 문서를 Notion 데이터베이스에 게시')
    root.add_argument('--config-dir', type=Path)
    root.add_argument('--state-dir', type=Path)
    sub = root.add_subparsers(dest='command', required=True)
    auth = sub.add_parser('auth', help='본인의 터미널에서 토큰을 키체인에 저장')
    auth.add_argument('--profile', default='default')
    init = sub.add_parser('init', help='문서 폴더 경로 설정')
    init.add_argument('--root', required=True, type=Path)
    sub.add_parser('targets', help='등록된 데이터베이스와 매핑 조회')
    add = sub.add_parser('add-target', help='데이터베이스 등록 및 속성 확인')
    add.add_argument('alias')
    add.add_argument('database_url')
    add.add_argument('--profile', default='default')
    add.add_argument('--data-source')
    add.add_argument('--map', action='append', default=[], metavar='FIELD=PROPERTY')
    mapping = sub.add_parser('map-target', help='기존 대상의 속성 매핑 추가·변경')
    mapping.add_argument('--target', required=True)
    mapping.add_argument('--map', action='append', required=True, metavar='FIELD=PROPERTY')
    schema = sub.add_parser('schema', help='데이터베이스의 현재 속성·선택값 조회')
    schema.add_argument('--target', required=True)
    for name in ('preview', 'publish', 'recover'):
        command = sub.add_parser(name)
        command.add_argument('file')
        command.add_argument('--target', required=True)
        if name == 'preview':
            command.add_argument('--online', action='store_true', help='Notion 속성까지 검증')
            command.add_argument('--show-body', action='store_true', help='명시적으로 요청한 경우에만 본문 출력')
        elif name == 'publish':
            command.add_argument('--accept-warnings', action='store_true')
            command.add_argument('--new-version', action='store_true')
        else:
            choice = command.add_mutually_exclusive_group(required=True)
            choice.add_argument('--page', help='사용자가 확인한 기존 페이지 URL')
            choice.add_argument('--confirmed-absent', action='store_true')
            command.add_argument('--accept-remote', action='store_true', help='현재 원격 내용을 다음 갱신의 기준으로 채택')
    relocation = sub.add_parser('move', help='이동한 문서의 게시 이력 경로 변경')
    relocation.add_argument('old_file')
    relocation.add_argument('new_file')
    relocation.add_argument('--target', required=True)
    status = sub.add_parser('status', help='대상별 게시 상태 조회')
    status.add_argument('--target')
    return root


def api_for(target):
    return Client(read_token(target['profile']))


def parse_mapping(items):
    mapping = {}
    for item in items:
        field, separator, prop = item.partition('=')
        if not separator or not field or not prop or field in mapping:
            raise Error('--map은 중복 없는 FIELD=PROPERTY 형식이어야 합니다.')
        mapping[field] = prop
    return mapping


def dispatch(args, store):
    if args.command == 'auth':
        authenticate(args.profile)
        return {'status': 'credential_saved', 'profile': args.profile}
    if args.command == 'init':
        document_root = args.root.expanduser().resolve()
        if not document_root.is_dir():
            raise Error('존재하는 문서 폴더를 지정하세요.')
        store.save_config({**store.config(), 'root': str(document_root)})
        return {'root': str(document_root)}
    if args.command == 'targets':
        return store.config()['targets']
    if args.command == 'add-target':
        mapping = parse_mapping(args.map)
        return register(Client(read_token(args.profile)), store, args.alias, args.database_url, mapping, args.profile, args.data_source)
    if args.command == 'move':
        return move(store, args.target, args.old_file, args.new_file)
    config = store.config()
    if args.command == 'status':
        source = target_config(config, args.target)['data_source_id'] if args.target else None
        return [e for e in store.state()['entries'].values() if source is None or e['data_source_id'] == source]
    target = target_config(config, args.target)
    if args.command == 'preview':
        schema = api_for(target).request('GET', f"data_sources/{target['data_source_id']}")['properties'] if args.online else None
        path, meta, payload, warnings = prepare(config, store.state(), args.target, args.file, schema)
        result = {'target': args.target, 'file': str(path), 'title': meta['title'], 'warnings': warnings, 'bytes': len(payload['markdown'].encode()), 'properties_validated': schema is not None}
        if args.show_body:
            result['payload'] = payload
        return result
    client = api_for(target)
    if args.command == 'map-target':
        schema = client.request('GET', f"data_sources/{target['data_source_id']}")['properties']
        mapping = {**target['mapping'], **parse_mapping(args.map)}
        validate_mapping(mapping, schema)
        store.save_config({**config, 'targets': {**config['targets'], args.target: {**target, 'mapping': mapping}}})
        return {'target': args.target, 'mapping': mapping}
    if args.command == 'schema':
        return client.request('GET', f"data_sources/{target['data_source_id']}")['properties']
    if args.command == 'publish':
        return publish(client, store, args.target, args.file, args.accept_warnings, args.new_version)
    if args.command == 'recover':
        if args.page and not args.accept_remote:
            raise Error('현재 원격 내용을 기준으로 채택하려면 --accept-remote를 지정하세요. 다음 publish는 원격 본문을 교체합니다.')
        return recover(client, store, args.target, args.file, args.page, args.confirmed_absent)
    raise Error('지원하지 않는 명령입니다.')


def main():
    args = parser().parse_args()
    store = Store(args.config_dir, args.state_dir)
    try:
        with store.locked():
            result = dispatch(args, store)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except Error as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError):
        print('로컬 파일 또는 응답 형식을 확인하세요. 게시 중이었다면 status로 상태를 확인하세요.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('중단했습니다. 게시 중이었다면 status로 상태를 확인하세요.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
