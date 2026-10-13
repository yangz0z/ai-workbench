# 명령과 복구

게시 환경은 macOS, Python 3.11 이상, uv다. `scripts/notion_prototype.py`는 이 스킬 폴더 기준으로 찾는다. 최초 사용 안내는 저장소의 `docs/notion-prototype.md`에 있다.

```sh
prototype_cli="$HOME/ai-workbench/skills/notion-prototype/scripts/notion_prototype.py"
uv run --script "$prototype_cli" --help
```

| 명령 | 역할 | 원격 쓰기 |
| --- | --- | --- |
| `auth --profile NAME` | 사용자 터미널에서 키체인 토큰 등록. 기본 `default` | 없음 |
| `preview FILE` | 확장자·UTF-8·5MB 제한 검사, 크기와 해시 출력 | 없음 |
| `publish FILE --page URL --profile NAME --position start` | 첫 게시 또는 연결된 HTML 교체 | 있음 |
| `status --page URL` | 로컬 연결·처리 상태 조회. 페이지 생략 시 전체 조회 | 없음 |
| `inspect --page URL --profile NAME` | 최상위 임베드 ID·수정 시각 조회 | 없음 |
| `recover --page URL --profile NAME --adopt-block ID` | 원격에서 확인한 기존 HTML을 관리 대상으로 채택 | 없음 |
| `recover --page URL --profile NAME --confirmed-absent` | 임베드 부재 확인 후 로컬 연결 해제 | 없음 |

`--position`은 `start` 또는 `end`이며 기본은 `end`다. 첫 게시에만 적용하며 갱신은 기존 위치를 유지한다. `--state-dir DIRECTORY`는 명령 앞에 쓰는 전역 옵션이며 기본은 `~/.local/share/notion-prototype`다. 다른 디렉터리를 쓰면 별개 이력이 되므로 오류를 우회하려고 바꾸지 않는다.

업무용·개인용 연결을 나누려면 자신의 터미널에서 각각 인증한다.

```sh
uv run --script "$prototype_cli" auth --profile work
uv run --script "$prototype_cli" publish ./prototype.html --page 'PAGE_URL' --profile work
uv run --script "$prototype_cli" inspect --page 'PAGE_URL' --profile work
```

프로필은 게시 이력에 저장되며 다른 프로필로 같은 페이지를 게시하면 중단한다. 프로필 이름이 권한 경계는 아니다. 접근 범위는 Notion 내부 연결에 공유한 페이지와 그 하위 항목으로 결정된다.

## 게시 상태와 복구

쓰기 전에 `pending`을 기록하고, 업로드 ID·새 블록 ID를 알게 될 때마다 저장한다. 새 블록을 재조회한 뒤 기존 블록을 제거하고 `ready`로 전환한다. 응답 유실·중간 실패 시 자동으로 쓰기를 재시도하지 않는다.

1. `status`에서 기존·새 블록 ID와 프로필을 확인한다.
2. `inspect`로 현재 임베드 ID를 조회한다. HTML 본문이나 서명된 임시 URL은 출력하지 않는다.
3. Notion 화면에서 각각의 내용을 확인한다. API의 embed 종류만으로는 HTML인지 일반 웹 임베드인지 구별할 수 없다.
4. 중복이 있다면 사용자가 지목한 불필요한 프로토타입만 Notion에서 제거한다. 본문 전체를 교체하지 않는다.
5. 남길 HTML을 `recover --adopt-block ID`로 채택한다. 다음 `publish`는 그 블록을 로컬 파일로 교체한다. 임베드가 전혀 없다면 `--confirmed-absent`로 연결을 해제한다.

초기 업로드만 성공한 뒤 실패했다면 연결되지 않은 파일이 남을 수 있다. 새 게시 전에 임베드가 생성됐는지 먼저 확인한다. 업로드 ID를 알고 있어도 이 CLI는 업로드 재개를 제공하지 않는다.

## 충돌과 보존 범위

게시 이력이 있는 블록의 `last_edited_time`이 달라지면 갱신을 멈춘다. 로컬 파일이 같아도 원격 변경 여부를 먼저 확인한다. 동시 편집을 원자적으로 차단하지는 못하므로 게시 중에는 같은 임베드를 편집하지 않는다.

한 PC의 기본 이력 디렉터리에서는 파일 잠금으로 동시 게시를 막는다. PC 사이의 이력은 자동 동기화되지 않는다. 한 PC에서 게시를 맡거나, 다른 PC에서 갱신하기 전에 이력을 옮기고 원격 상태를 확인한다.

교체는 새 블록 생성 후 이전 블록 제거다. 블록 ID·댓글·크기는 유지되지 않는다. 일반 본문·속성·다른 블록은 편집하지 않는다. 위치 이동은 Notion UI에서 수행한다. 첫 게시 시 기존 임베드가 있으면 중복 방지를 위해 중단하며, 원하는 HTML의 명시적 채택 또는 별도 페이지가 필요하다.

## 구현 계약

- API 버전: `2026-03-11`
- 업로드: `file_uploads` 생성 → multipart `file` 전송 → `embed.file_upload` 연결
- 삽입: 첫 게시는 `position.type=start|end`, 교체는 `after_block`
- 업로드 파일명: `prototype.html`, 콘텐츠 유형: `text/html`
- 인증정보를 다른 호스트로 보내지 않도록 HTTP 리디렉션 차단
- 성공 출력: `created`, `updated`, `unchanged`와 Notion 페이지 URL·블록 ID
- 실패 출력: 정리된 오류 메시지와 종료 코드 1, 사용자 중단은 130
- 상태 파일은 개인 경로·페이지 식별자를 포함하므로 공개 저장소에서 제외

[HTML 블록](https://developers.notion.com/reference/block#html-blocks), [업로드 생성](https://developers.notion.com/reference/create-file), [파일 전송](https://developers.notion.com/reference/upload-file), [블록 삽입 위치](https://developers.notion.com/reference/patch-block-children)를 사용한다. 이 패키지는 파일 기반 임베드의 직접 갱신 대신 생성 후 제거 방식을 사용한다.
