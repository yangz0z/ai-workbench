"""게시 대상 등록과 문서별 생성·갱신 상태 관리"""

from pathlib import Path

from core import Error, convert, digest, notion_id, properties, validate_mapping


def target_config(config, alias):
    target = config['targets'].get(alias)
    if not target:
        raise Error(f'등록되지 않은 대상입니다: {alias}')
    return target


def register(client, store, alias, database, mapping, profile='default', source=None):
    config = store.config()
    if alias in config['targets']:
        raise Error('이미 등록된 별칭입니다. 다른 별칭을 사용하거나 config.json에서 매핑을 수정하세요.')
    database_id = notion_id(database)
    response = client.request('GET', f'databases/{database_id}')
    sources = response.get('data_sources', [])
    if source:
        source_id = notion_id(source)
        if source_id not in {notion_id(s['id']) for s in sources}:
            raise Error('지정한 데이터 소스가 이 데이터베이스에 없습니다.')
    elif len(sources) == 1:
        source_id = notion_id(sources[0]['id'])
    else:
        choices = ', '.join(f"{s.get('name', '')}: {s['id']}" for s in sources)
        raise Error('데이터 소스를 명시하세요 (--data-source). 후보: ' + choices)
    schema = client.request('GET', f'data_sources/{source_id}')['properties']
    titles = [name for name, prop in schema.items() if prop['type'] == 'title']
    if len(titles) != 1:
        raise Error('제목 속성을 식별하지 못했습니다.')
    mapping = {'title': titles[0], **mapping}
    validate_mapping(mapping, schema)
    target = {'database_id': database_id, 'data_source_id': source_id, 'profile': profile, 'mapping': mapping}
    store.save_config({**config, 'targets': {**config['targets'], alias: target}})
    return {'target': alias, 'properties': {k: v['type'] for k, v in schema.items()}, 'mapping': mapping}


def document_root(config):
    if not config.get('root'):
        raise Error('먼저 init --root로 문서 폴더를 설정하세요.')
    return Path(config['root']).expanduser().resolve()


def source_path(config, filename):
    root = document_root(config)
    path = Path(filename).expanduser()
    path = (path if path.is_absolute() else root / path).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() != '.md':
        raise Error('설정한 문서 폴더 안의 Markdown 파일을 지정하세요. 폴더 밖으로 향하는 심볼릭 링크도 사용할 수 없습니다.')
    return path


def entry_key(path, target):
    return digest([str(path), target['data_source_id']])


def link_map(state, target, root):
    candidates = {}
    for entry in state['entries'].values():
        if entry.get('status') != 'ready' or entry['data_source_id'] != target['data_source_id']:
            continue
        path = Path(entry['file'])
        if not path.is_relative_to(root):
            continue
        for name in {str(path.relative_to(root).with_suffix('')), path.stem}:
            candidates.setdefault(name, set()).add(entry['url'])
    return {name: next(iter(urls)) for name, urls in candidates.items() if len(urls) == 1}


def prepare(config, state, alias, filename, schema=None):
    target = target_config(config, alias)
    path = source_path(config, filename)
    root = document_root(config)
    meta, body, warnings = convert(path.read_text(), link_map(state, target, root))
    if meta.get('title') in (None, ''):
        meta = {**meta, 'title': path.stem}
    payload = {'markdown': body}
    if schema is not None:
        payload['properties'] = properties(meta, target['mapping'], schema)
    return path, meta, payload, warnings


def remote_snapshot(client, page_id, target):
    page = client.request('GET', f'pages/{page_id}')
    parent = page.get('parent', {})
    if parent.get('type') != 'data_source_id' or notion_id(parent.get('data_source_id', '')) != target['data_source_id']:
        raise Error('페이지가 지정한 데이터베이스의 데이터 소스에 속하지 않습니다.')
    if page.get('archived') or page.get('in_trash'):
        raise Error('페이지가 휴지통에 있습니다. 복원 여부를 먼저 확인하세요.')
    content = client.request('GET', f'pages/{page_id}/markdown')
    if content.get('truncated') or content.get('unknown_block_ids'):
        raise Error('페이지 전체 내용을 확인할 수 없어 갱신을 중단했습니다.')
    if not isinstance(content.get('markdown'), str):
        raise Error('Notion 본문 응답을 확인할 수 없습니다.')
    return digest({'markdown': content['markdown'], 'properties': page['properties']}), page


def publish(client, store, alias, filename, accept_warnings=False, new_version=False):
    config, state = store.config(), store.state()
    target = target_config(config, alias)
    schema = client.request('GET', f"data_sources/{target['data_source_id']}")['properties']
    path, meta, payload, warnings = prepare(config, state, alias, filename, schema)
    if warnings and not accept_warnings:
        raise Error('변환 안내를 확인한 뒤 --accept-warnings를 사용하세요: ' + ', '.join(warnings))
    key = entry_key(path, target)
    old = state['entries'].get(key)
    if old and old.get('status') != 'ready':
        raise Error('이전 게시 결과가 미확정입니다. Notion에서 확인 후 recover 명령으로 연결하세요.')
    content_hash = digest(payload)
    if old and not new_version:
        remote_hash, _ = remote_snapshot(client, old['page_id'], target)
        if remote_hash != old['remote_hash']:
            raise Error('Notion에서 수정된 내용이 있습니다. 미리보기와 원격 페이지를 비교한 뒤 처리하세요.')
        if content_hash == old['content_hash']:
            return {'target': alias, 'status': 'unchanged', 'url': old['url'], 'warnings': warnings}
    history = list(old.get('history', [])) if old else []
    if old and new_version:
        history.append({'page_id': old['page_id'], 'url': old['url']})
    entry = {
        'file': str(path), 'data_source_id': target['data_source_id'],
        'status': 'pending', 'content_hash': content_hash, 'history': history,
    }
    updating = old is not None and not new_version
    if updating:
        entry.update(page_id=old['page_id'], url=old['url'])
    state['entries'][key] = entry
    store.save_state(state)
    # 쓰기 전에 pending을 영속화해 응답 유실·중간 실패 후 중복 생성 방지
    if updating:
        page_id = entry['page_id']
        client.request('PATCH', f'pages/{page_id}', {'properties': payload['properties']})
        client.request('PATCH', f'pages/{page_id}/markdown', {'type': 'replace_content', 'replace_content': {'new_str': payload['markdown']}})
    else:
        created = client.request('POST', 'pages', {'parent': {'type': 'data_source_id', 'data_source_id': target['data_source_id']}, **payload})
        entry['page_id'] = notion_id(created['id'])
        entry['url'] = created['url']
        store.save_state(state)
    remote_hash, page = remote_snapshot(client, entry['page_id'], target)
    entry.update(status='ready', remote_hash=remote_hash, url=page['url'])
    store.save_state(state)
    return {'target': alias, 'status': 'updated' if updating else 'created', 'url': entry['url'], 'warnings': warnings}


def recover(client, store, alias, filename, page_url=None, confirmed_absent=False):
    config, state = store.config(), store.state()
    target = target_config(config, alias)
    path = source_path(config, filename)
    key = entry_key(path, target)
    old = state['entries'].get(key, {})
    if confirmed_absent:
        if old.get('status') != 'pending' or old.get('page_id'):
            raise Error('페이지 ID가 없는 미확정 생성 요청만 해제할 수 있습니다.')
        state['entries'].pop(key)
        store.save_state(state)
        return {'status': 'pending_cleared'}
    if not page_url:
        raise Error('연결할 페이지 URL이 필요합니다.')
    page_id = notion_id(page_url)
    if any(k != key and e.get('page_id') == page_id for k, e in state['entries'].items()):
        raise Error('다른 파일에 연결된 페이지입니다. 이동한 파일이면 move 명령을 사용하세요.')
    remote_hash, page = remote_snapshot(client, page_id, target)
    state['entries'][key] = {
        'file': str(path), 'data_source_id': target['data_source_id'], 'status': 'ready',
        'page_id': page_id, 'url': page['url'], 'remote_hash': remote_hash,
        'content_hash': None, 'history': old.get('history', []),
    }
    store.save_state(state)
    return {'status': 'linked', 'url': page['url']}


def move(store, alias, old_filename, new_filename):
    config, state = store.config(), store.state()
    target = target_config(config, alias)
    root = document_root(config)
    old_path = Path(old_filename).expanduser()
    old_path = (old_path if old_path.is_absolute() else root / old_path).resolve()
    new_path = source_path(config, new_filename)
    old_key, new_key = entry_key(old_path, target), entry_key(new_path, target)
    if old_key not in state['entries'] or new_key in state['entries']:
        raise Error('이전 게시 이력이 없거나 새 경로에 이미 게시 이력이 있습니다.')
    entry = state['entries'].pop(old_key)
    state['entries'][new_key] = {**entry, 'file': str(new_path)}
    store.save_state(state)
    return {'status': 'moved', 'url': entry.get('url')}
