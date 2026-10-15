# 채팅 기획을 Notion에서 눌러보는 화면으로 만들기

`notion-prototype`은 개발자·기획자가 채팅으로 논의한 화면을 **버튼과 입력이 동작하는 HTML 초안**으로 만들어 Notion에 공유하는 AI 스킬입니다. 글만으로 전달하기 어려운 버튼 위치, 입력 기본값, 계산 전후 화면, 오류 안내를 직접 눌러보며 확인할 때 사용합니다.

예를 들어 “지출 목록은 계속 보여주고 계산 버튼을 누르면 결과를 위에 표시해 줘. 내역이 추가되면 재계산 안내만 해 줘”라고 요청하면, AI가 그 흐름을 HTML로 작성합니다. 화면을 확인한 뒤 게시를 요청하면 Notion 페이지 안에서 팀원이 눌러볼 수 있습니다.

HTML 작성은 Claude Code·Codex 같은 AI가 담당합니다. 함께 제공하는 CLI는 완성된 HTML의 검사, Notion 업로드, 같은 페이지의 HTML 교체를 담당합니다. CLI 자체가 자연어를 해석해 화면을 생성하지는 않습니다.

## 어떤 결과가 만들어지나요?

```text
채팅으로 요구사항 설명
  → 단일 HTML 파일 생성
  → 로컬 브라우저에서 화면·클릭 확인
  → 기존 Notion 페이지에 HTML 업로드
  → 같은 페이지의 HTML을 반복 갱신
```

CSS·JavaScript를 한 파일에 넣으므로 별도 웹 서버를 배포할 필요가 없습니다. Notion은 업로드한 HTML을 페이지 안의 격리된 프레임에서 표시합니다. [Notion HTML 블록 문서](https://developers.notion.com/reference/block#html-blocks)

이 결과물은 기획 검토용입니다. 실제 로그인·데이터 저장·송금·서버 처리를 구현한 서비스가 아닙니다. 기본적으로 예시 데이터를 사용하고 새로고침하면 초기화합니다. 초기화·데이터 주입 같은 테스트 버튼은 점선 영역에 모아 실제 제품 버튼과 구분합니다.

## 1. 실행 환경

게시에는 **macOS, Python 3.11 이상, uv**가 필요합니다. 인증을 macOS 키체인에 저장하므로 현재 Linux·Windows에서의 게시를 지원하지 않습니다. HTML 파일 자체는 일반 브라우저에서 열 수 있습니다.

설치는 [README의 공통 설치 안내](../README.md#설치)에서 `notion-prototype`을 선택합니다.


이 스킬만 설치해도 동작하며 `markdown-notion` 설치는 필요하지 않습니다.

아래 파일 경로는 사용자 전역 설치 기준입니다. 프로젝트 설치라면 실제 설치 경로로 바꿉니다.

## 2. 게시 전에 화면부터 체험

[브라우저에서 체험하기](https://yangz0z.github.io/ai-workbench/notion-prototype/)에서 설치·Notion 인증 없이 예제를 눌러볼 수 있습니다. 실제 신청이나 저장은 하지 않습니다.

로컬 파일로 열 수도 있습니다.

파일 탐색기에서 `~/.agents/skills/notion-prototype/assets/example.html`을 찾아 더블클릭합니다.

예제는 신청 내용을 입력하고 확인 버튼을 누르면 요약을 표시합니다. 입력을 바꾸면 이전 결과와 재확인 안내를 유지하고, 버튼을 다시 눌러야 결과가 바뀝니다. 점선 영역의 초기화 버튼은 테스트용입니다.

나만의 화면은 AI에게 다음처럼 요청하세요.

```text
notion-prototype으로 행사 신청 화면을 만들어줘.
이름과 참석 인원을 입력하고, ‘신청 내용 확인’을 누르면 위에 요약을 보여줘.
입력만 바꿨을 때는 이전 요약을 유지하고 다시 확인하라고 안내해줘.
테스트용 초기화 버튼은 점선 영역으로 구분해줘.
원본은 ./prototypes/event.html에 저장하고 우선 로컬에서 확인해줘.
```

입력 항목, 기본값, 버튼을 누른 뒤의 변화, 자동으로 처리하면 안 되는 동작을 알려주면 논의하기 쉽습니다. 디자인·업무 규칙이 미정이면 미정이라고 적어 주세요. 이 요청만으로 Notion에 게시하지는 않습니다.

## 3. Notion 연결 준비

1. [Notion 개발자 포털](https://www.notion.so/profile/integrations)에서 내부 연결을 만듭니다. 워크스페이스 소유자 권한이 필요할 수 있습니다.
2. 콘텐츠 읽기·삽입·수정 권한을 켭니다.
3. 프로토타입을 올릴 **기존 페이지**의 연결 메뉴에서 해당 내부 연결을 추가합니다.
4. 페이지 링크를 복사합니다. 처음에는 다른 임베드가 없는 테스트 페이지를 권합니다.

이 스킬은 페이지를 새로 만들거나 검색하지 않습니다. 연결에 허용한 페이지와 그 하위 항목에 접근할 수 있습니다. 데이터베이스 안의 개별 티켓 페이지도 대상으로 사용할 수 있습니다. [내부 연결 안내](https://developers.notion.com/guides/get-started/internal-connections)

**본인의 터미널**에서 다음 명령을 실행합니다. AI가 실행한 터미널이나 채팅으로 토큰을 보내지 마세요.

```sh
prototype_cli="$HOME/.agents/skills/notion-prototype/scripts/notion_prototype.py"
uv run --script "$prototype_cli" auth
```

프롬프트에 내부 연결 토큰을 입력하면 화면에는 표시되지 않습니다. `credential_saved`가 나오면 준비됐습니다. 토큰은 macOS 키체인의 `notion-prototype` 서비스에 저장됩니다. 다른 Notion 스킬의 토큰은 자동으로 가져오지 않습니다.

## 4. AI에게 게시 요청

화면을 확인한 뒤 AI에게 파일과 페이지 링크를 알려 주세요.

```text
./prototypes/event.html을 이 Notion 페이지 맨 위에 게시해줘: PAGE_URL
```

AI는 파일을 검사하고, HTML을 업로드해 기존 페이지에 임베드 하나를 추가합니다. 결과로 Notion 페이지 링크를 받습니다. 로컬 브라우저 검증과 실제 Notion 화면 표시는 별도이므로, 게시한 페이지에서 입력·버튼이 동작하는지도 확인하세요.

CLI로 직접 실행하려면 `PAGE_URL`을 실제 페이지 링크로 바꿉니다.

```sh
uv run --script "$prototype_cli" preview ./prototypes/event.html
uv run --script "$prototype_cli" publish ./prototypes/event.html --page 'PAGE_URL' --position start
```

`preview`는 파일 확장자·인코딩·크기만 검사하며 Notion으로 전송하지 않습니다. HTML 보안 검사나 화면·동작 검증 도구는 아닙니다. 게시 가능한 입력은 비어 있지 않은 UTF-8 `.html`·`.htm` 파일이며 최대 5MB입니다. 5MB는 이 CLI의 제한입니다.

## 5. 수정한 화면 다시 반영

```text
행사 신청 화면의 참석 인원 기본값을 2명으로 바꾸고,
버튼 이름은 ‘신청 내용 확인’으로 유지해줘.
브라우저에서 확인하고 같은 Notion 페이지에 반영해줘.
```

```sh
uv run --script "$prototype_cli" publish ./prototypes/event.html --page 'PAGE_URL'
```

페이지별 연결 이력으로 기존 HTML 하나를 찾아 교체합니다. 파일이 같으면 `unchanged`로 끝납니다. 파일을 다른 폴더로 옮겨도 같은 페이지를 지정하면 같은 HTML을 갱신합니다.

첫 게시는 `--position start`로 맨 위, `--position end`로 맨 아래에 넣습니다. 생략하면 맨 아래입니다. **갱신은 기존 위치를 유지**하므로 `--position start`를 다시 붙여도 이동하지 않습니다. 위치 이동이 필요하면 Notion 화면에서 옮긴 뒤, 변경 충돌이 발생할 경우 아래 복구 안내를 따르세요.

교체는 새 블록을 만든 뒤 기존 블록을 제거하는 방식입니다. 블록 ID가 바뀌고 기존 블록의 댓글·크기 같은 부가 정보는 이관되지 않습니다. 리뷰 의견은 임베드 자체의 댓글보다 페이지 본문이나 페이지 댓글에 남겨두는 편이 좋습니다.

## 6. 실패하거나 기존 HTML을 이어서 관리할 때

게시 중 오류가 났다면 같은 명령을 반복하기 전에 상태를 확인하세요.

```sh
uv run --script "$prototype_cli" status --page 'PAGE_URL'
uv run --script "$prototype_cli" inspect --page 'PAGE_URL'
```

- `ready`: 관리 중인 블록 연결이 저장돼 있습니다.
- `pending`: 업로드·삽입·기존 블록 제거 중 결과가 불명확합니다. 재게시가 차단됩니다.
- `untracked`: 이 PC에 해당 페이지의 게시 이력이 없습니다.

`inspect`는 페이지 최상위 임베드의 ID와 수정 시각을 보여줍니다. 서명된 다운로드 주소나 HTML 본문은 출력하지 않습니다. 일반 웹 임베드도 함께 표시되므로 Notion 화면에서 원하는 HTML인지 확인해야 합니다.

Notion에 HTML이 하나 남아 있고 그것을 계속 관리하려면:

```sh
uv run --script "$prototype_cli" recover --page 'PAGE_URL' --adopt-block BLOCK_ID
```

이 명령은 원격 내용을 바꾸지 않고 로컬 연결만 채택합니다. **다음 `publish`가 그 블록을 로컬 HTML로 교체합니다.** 두 버전이 남았다면 Notion 화면에서 내용을 비교하고 필요 없는 프로토타입만 제거한 뒤 남긴 블록을 채택하세요. 이력이 있는 기존·새 블록이 함께 남아 있으면 채택이 차단됩니다.

첫 게시가 실패했고 페이지에 임베드가 전혀 없음을 확인했다면:

```sh
uv run --script "$prototype_cli" recover --page 'PAGE_URL' --confirmed-absent
```

이 명령은 임베드가 없는지 API로 확인한 뒤 로컬 연결을 해제합니다. 업로드만 된 파일이 있더라도 중복 블록을 만들지는 않습니다. 이후 다시 게시할 수 있습니다. 이력 파일을 삭제해 오류를 우회하지 마세요.

PC를 바꾸거나 이력을 잃었을 때도 `inspect` → Notion 화면 확인 → `recover --adopt-block` 순서로 기존 HTML을 연결합니다. 상세 명령은 [명령과 복구](../skills/notion-prototype/references/usage.md)에 있습니다.

## 어디에 무엇이 저장되나요?

| 위치 | 내용 |
| --- | --- |
| 직접 정한 HTML 경로 | 다시 수정할 원본. 임시 경로라면 나중에 없어질 수 있음 |
| Notion | 업로드한 HTML 사본과 임베드 블록 |
| macOS 키체인 `notion-prototype` | 프로필별 내부 연결 토큰 |
| `~/.local/share/notion-prototype/state.json` | 페이지·블록 ID, 원본 경로, 프로필 이름, 해시와 게시 상태 |

로컬 HTML을 지워도 Notion에 업로드한 사본은 유지되지만, 계속 수정하려면 로컬 원본을 보관하세요. 상태 파일에는 토큰과 HTML 본문을 넣지 않습니다. 개인 경로와 페이지 ID가 포함되므로 공개 저장소에 올리지 마세요.

HTML에는 인증정보·실제 개인정보·운영 API 호출을 넣지 않습니다. 업로드한 HTML은 Notion으로 전송되며 페이지의 공유 범위에 따라 다른 사람이 볼 수 있습니다. AI가 원본을 읽으면 그 내용도 AI 컨텍스트에 들어갑니다. 외부에서 받은 HTML은 실행 전에 내용을 확인하세요.

## markdown-notion과 함께 사용하려면

| 목적 | 스킬 |
| --- | --- |
| 로컬 Markdown 문서를 데이터베이스 항목으로 반복 게시 | `markdown-notion` |
| 화면을 HTML로 만들고 기존 페이지에 클릭형 프로토타입 게시 | `notion-prototype` |

`markdown-notion`은 본문 전체를 교체하므로 같은 페이지에 두 스킬을 번갈아 게시하지 마세요. 원격 변경 충돌이 발생할 수 있고, 원격을 채택한 뒤 Markdown을 다시 게시하면 HTML이 제거될 수 있습니다. **문서 페이지와 프로토타입 페이지를 나누고 링크로 연결**하면 각 원본을 따로 갱신할 수 있습니다.

이 스킬은 페이지당 최상위 임베드 하나를 관리합니다. 여러 화면은 하나의 HTML 안에서 탭·상태로 표현하거나 별도 페이지를 사용하세요. 실제 서비스 개발이나 디자인 원본 관리가 필요하면 해당 작업 도구를 함께 사용합니다.
