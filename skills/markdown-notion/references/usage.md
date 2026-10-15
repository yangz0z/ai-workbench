# 명령과 복구

공통 도구가 Markdown 문서를 읽어 Notion 데이터베이스에 항목을 만든다. 본문은 페이지 안에, frontmatter는 설정된 데이터베이스 속성에 저장한다. Notion 데이터베이스 안에 데이터 소스가 여러 개면 어느 데이터 소스를 쓸지 명시한다.

경로 예시는 `npx skills add`의 기본 사용자 전역 설치 기준이다. 프로젝트 설치 또는 별도 경로를 사용했다면 실제 설치 위치로 바꾼다.

## 최초 설정

1. Notion에서 내부 연결을 생성하고 콘텐츠·속성의 조회·삽입·수정에 필요한 권한을 켠다. 사용자·댓글 권한은 필요하지 않다.
2. 게시할 데이터베이스의 연결 메뉴에서 해당 내부 연결에 접근을 허용한다. 링크된 보기만 있다면 원본 데이터베이스를 사용한다.
3. 자신의 터미널에서 토큰을 등록한다. 토큰은 명령어에 붙이지 않고 숨김 입력 프롬프트에 입력한다.

```sh
uv run --script ~/.agents/skills/markdown-notion/scripts/notion_publish.py auth
```

토큰은 macOS 키체인에 저장된다. 에이전트에게 입력을 대신 맡기거나 토큰을 채팅에 보내지 않는다. `--profile default`가 기본이며 워크스페이스별 토큰이 필요하면 다른 프로필로 `auth`를 실행한다.

아래 경로는 설치한 스킬 위치로 바꾼다. `scripts/notion_publish.py` 파일을 지정하며 디렉터리 자체를 실행하지 않는다. 문서 폴더는 미리 존재해야 한다. 값에 토큰은 포함하지 않는다.

```sh
notion_publish_script="$HOME/.agents/skills/markdown-notion/scripts/notion_publish.py"
uv run --script "$notion_publish_script" init --root "$HOME/Documents/notes"
uv run --script "$notion_publish_script" add-target 업무기록 'NOTION_DATABASE_URL'
uv run --script "$notion_publish_script" schema --target 업무기록
```

`NOTION_DATABASE_URL`은 실제 데이터베이스 URL로 바꾼다. 제목 속성은 자동 인식한다. 그 외 속성은 현재 이름과 타입을 확인한 뒤 매핑한다.

```sh
uv run --script "$notion_publish_script" map-target --target 업무기록 \
  --map 'project=프로젝트' --map 'tags=태그' --map 'created=작성일'
uv run --script "$notion_publish_script" add-target 개인글 'SECOND_DATABASE_URL'
uv run --script "$notion_publish_script" targets
```

속성이 없거나 타입이 맞지 않으면 등록·게시 전에 오류를 반환한다. 선택형 속성은 Notion에 이미 존재하는 옵션만 허용한다. 예를 들어 원문의 `type: note`를 연결하려면 선택값에도 `note`가 있어야 한다. 원문을 바꾸거나 해당 속성을 매핑에서 제외하는 방식으로 조정한다. 매핑 삭제는 `config.json`의 해당 키를 제거한다. 데이터베이스 속성 자체를 만들거나 변경하지 않는다.

지원 속성: 제목, 텍스트, 선택, 다중 선택, 상태, 날짜, 체크박스, 숫자, URL. 관계·롤업·수식·사용자·파일 속성은 매핑하지 않는다. 원문에 없는 필드는 전송하지 않아 기존 값을 유지하고, null은 텍스트·선택·다중 선택·상태·날짜·숫자·URL을 비울 때 사용한다. 체크박스는 true 또는 false가 필요하며 제목은 비울 수 없다.

## 게시와 확인

```sh
uv run --script "$notion_publish_script" preview 'notes/문서.md' --target 업무기록 --online
uv run --script "$notion_publish_script" publish 'notes/문서.md' --target 업무기록
uv run --script "$notion_publish_script" status --target 업무기록
```

미리보기는 Notion에 쓰지 않는다. `--online`을 빼면 인증 없이 문서 변환만 확인한다. 본문 출력은 `--show-body`로 명시한다. 변환 안내를 확인한 뒤 게시하려면 `publish`에 `--accept-warnings`를 추가한다. 같은 문서와 데이터 소스는 같은 항목의 본문 전체를 교체하고, 별도 항목 생성은 `--new-version`으로 명시한다.

표는 Notion의 HTML 표 형식으로 변환한다. 위키링크는 같은 게시 대상에 기록된 문서의 URL로 바꾸고, 매칭할 수 없거나 이름이 중복되면 텍스트로 바꿔 안내한다. 코드 블록의 내용은 보존한다. Dataview 블록은 제외하며 Mermaid는 코드로 보존한다. 로컬 이미지·첨부·상대 링크·Obsidian 임베드와 직접 작성한 HTML은 게시를 중단한다. 본문은 400 KB 이내로 제한하며 서버의 추가 블록·형식 제한에 걸리면 문서를 나눠야 한다.

## 수정 충돌·실패 복구

Notion의 원격 본문과 속성이 마지막 게시 이후 바뀌었으면 갱신을 중단한다. 양방향 자동 병합은 수행하지 않는다. 원격 확인과 쓰기 사이의 동시 편집까지 원자적으로 막지는 못하므로 게시 중 Notion 직접 편집은 피한다.

쓰기 전에 `pending`을 저장한다. 네트워크 오류·HTTP 오류·부분 갱신 후에는 자동 재시도하지 않는다. 우선 Notion 화면과 `status`에서 결과를 확인한다.

기존 페이지를 확인했고 다음 게시에서 로컬 내용으로 교체하기로 결정한 경우:

```sh
uv run --script "$notion_publish_script" recover 'notes/문서.md' --target 업무기록 \
  --page 'EXISTING_PAGE_URL' --accept-remote
```

이 명령은 현재 원격 내용을 충돌 검사의 기준으로 저장한다. 원격 본문을 로컬에 가져오지 않으며 다음 `publish`는 로컬 본문으로 교체한다. 새 PC에서 기존 항목에 연결할 때도 같은 명령을 사용한다.

페이지 ID조차 받지 못한 생성 요청이 실제로 실패했고, Notion에서 항목이 없음을 확인한 경우에만:

```sh
uv run --script "$notion_publish_script" recover 'notes/문서.md' --target 업무기록 --confirmed-absent
```

이후 다시 게시할 수 있다. 기존 페이지가 있는데 이 옵션을 쓰면 중복 생성될 수 있다. 파일을 이동한 경우에는 대상마다 이력을 이전한다.

```sh
uv run --script "$notion_publish_script" move 'drafts/문서.md' 'notes/문서.md' --target 업무기록
```

## 로컬 저장과 검증

설정은 `~/.config/markdown-notion/config.json`, 게시 이력은 `~/.local/share/markdown-notion/state.json`에 저장한다. 파일은 소유자만 읽고 쓸 수 있게 생성하며 토큰·본문은 저장하지 않는다. 이력에는 로컬 경로와 개인 Notion URL이 포함된다. 다른 PC에서 이어 쓰려면 이력을 안전하게 옮기거나 `recover`로 연결한다.

토큰 저장 서비스 이름은 `markdown-notion`이며 기본 프로필은 `default`다. 같은 토큰을 여러 대상에 쓰거나 `auth --profile work`와 `add-target ... --profile work`처럼 프로필을 나눌 수 있다. 프로필 분리는 대상 선택 기능이며 같은 로컬 에이전트의 접근을 서로 격리하지 않는다.

CLI의 `--config-dir`, `--state-dir` 전역 옵션은 명령 이름 앞에 둔다. 테스트·미리보기를 격리할 때 사용할 수 있다. 두 옵션은 설정과 이력의 위치만 바꾸며 키체인 프로필은 공유한다. 기존 게시 폴더를 이동하거나 PC를 바꿀 때는 파일 경로가 달라지므로 이력을 이전하거나 기존 페이지를 recover로 연결해야 중복 생성을 피할 수 있다.

```sh
cd ~/.agents/skills/markdown-notion
uv run --with 'PyYAML==6.0.3' --with 'markdown-it-py==4.0.0' --with 'keyring==25.7.0' \
  python -m unittest discover -s tests -v
```

실제 Notion 인증·API 쓰기를 하지 않는 모의 테스트다. 실계정 연결 후 별도의 테스트 문서로 생성·수정·화면 표시를 검증한다. 토큰 갱신은 같은 프로필로 `auth`를 다시 실행한다. 폐기는 Notion 연결 관리와 macOS 키체인에서 직접 처리한다.

사용 API 버전은 `2026-03-11`이다. [Markdown API](https://developers.notion.com/guides/data-apis/working-with-markdown-content), [데이터 소스](https://developers.notion.com/reference/retrieve-a-data-source), [인증](https://developers.notion.com/guides/get-started/authorization)을 기준으로 구현했다.

## 대표 입력과 결과

등록된 문서 폴더가 `~/Documents/notes`라면 `notes/문서.md`는 그 폴더 안의 상대 경로다. 작업 터미널의 현재 폴더와 무관하다. `init --root` 전에는 문서 게시를 거부한다.

```yaml
---
title: 회의록
tags: [meeting]
created: 2026-09-29
---
```

제목은 자동으로 Notion 제목 속성에 연결한다. `tags=태그`, `created=작성일` 매핑이 있으면 각각 다중 선택과 날짜로 전송한다. `meeting` 선택지가 Notion에 없으면 쓰기 전에 중단한다. 매핑하지 않은 frontmatter 필드는 전송하지 않는다. 본문은 별도 페이지 콘텐츠로 저장한다.

정상 응답의 `status`는 첫 게시 `created`, 수정 반영 `updated`, 내용 동일 `unchanged`다. 실패 시 종료 코드 1과 간결한 오류를 반환한다. 권한 오류는 Notion 연결에 원본 데이터베이스가 공유되어 있는지 확인한다. 다른 토큰으로 자동 전환하지 않는다.
