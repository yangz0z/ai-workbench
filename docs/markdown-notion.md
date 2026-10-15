# 설치와 첫 게시

`markdown-notion`은 로컬 문서를 원본으로 두고 Notion 데이터베이스에 반복 게시하는 스킬입니다. AI에게 파일과 목적지를 알려주면 스크립트가 본문 변환·속성 검증·생성·갱신을 처리합니다.

## 설치

macOS, Python 3.11 이상, [uv](https://docs.astral.sh/uv/getting-started/installation/)가 필요합니다. 인증은 macOS 키체인을 사용하므로 Linux·Windows는 현재 지원하지 않습니다. Python 의존성은 스크립트에 고정되어 있으며 uv가 준비합니다.

Node.js와 npm에 포함된 `npx`가 필요합니다. 아래 명령으로 실행 환경을 확인합니다.

```sh
node --version
npx skills --help
```

원하는 스킬만 사용자 전역에 설치합니다. 저장소를 직접 클론할 필요는 없습니다.

```sh
npx skills add yangz0z/ai-workbench --skill markdown-notion -g
```

설치 과정에서 Claude Code·Codex 등 사용할 AI 도구를 선택합니다. 도구까지 지정하려면 아래 중 하나를 실행합니다.

```sh
# Claude Code
npx skills add yangz0z/ai-workbench --skill markdown-notion -g --agent claude-code

# Codex
npx skills add yangz0z/ai-workbench --skill markdown-notion -g --agent codex
```

두 도구에 함께 설치하려면 `--agent claude-code codex`로 지정합니다. `-g`를 빼면 현재 프로젝트에만 설치합니다. 기존에 같은 이름의 개인 스킬이 있다면 덮어쓰기 전에 내용을 확인하세요. 설치 후 스킬이 보이지 않으면 새 세션을 시작합니다.

처음 실행할 때 Skills CLI 다운로드를 물을 수 있으며 인터넷 연결이 필요합니다. CLI가 저장소를 임시로 가져와 선택한 스킬 폴더를 설치합니다. 전체 저장소를 작업 폴더에 보관하거나 직접 심볼릭 링크를 만들 필요는 없습니다.

설치 확인과 업데이트:

```sh
npx skills list -g
npx skills update markdown-notion -g
```

이 가이드의 파일 경로 예시는 기본 전역 설치 위치인 `~/.agents/skills/markdown-notion`를 기준으로 합니다. 프로젝트 설치라면 프로젝트의 `.agents/skills/markdown-notion`로 바꾸고, 별도 경로를 사용했다면 설치 결과에 나온 경로를 따릅니다. [Skills CLI 사용법](https://github.com/vercel-labs/skills)

## Notion 연결 준비

1. [Notion 개발자 포털](https://www.notion.so/profile/integrations)에서 내부 연결을 만듭니다. 워크스페이스 소유자 권한이 필요할 수 있습니다.
2. 콘텐츠 읽기·삽입·수정 권한을 설정합니다. 댓글·사용자 정보 권한은 필요하지 않습니다.
3. 게시할 데이터베이스에 내부 연결을 추가하고 데이터베이스 URL을 복사합니다. 링크된 보기만 있다면 원본 데이터베이스를 사용합니다.

접근 권한은 공유한 상위 페이지에서 하위 항목으로 상속됩니다. 연결에 허용할 범위를 확인하세요. [Notion 내부 연결 안내](https://developers.notion.com/guides/get-started/internal-connections)

**사용자 자신의 터미널**에서 다음 명령을 실행하고 토큰을 숨김 입력합니다. 토큰을 AI 채팅에 보내지 않습니다.

```sh
notion_publish_script="$HOME/.agents/skills/markdown-notion/scripts/notion_publish.py"
uv run --script "$notion_publish_script" auth
```

`credential_saved`가 나오면 준비된 것입니다. 토큰은 macOS 키체인에 저장됩니다. 이후 설정과 게시는 AI에게 요청할 수 있습니다.

## AI에게 요청하기

아래 경로와 URL은 자신의 값으로 바꿉니다.

```text
markdown-notion으로 ~/Documents/notes를 문서 폴더로 설정해줘.
이 Notion 데이터베이스 URL을 ‘팀 기록’이라는 별칭으로 등록해줘: DATABASE_URL
```

```text
회의록.md를 ‘팀 기록’에 게시해줘.
```

처음에는 데이터베이스 항목을 만들고, 같은 파일을 같은 대상에 다시 게시하면 기존 항목을 갱신합니다. 제목은 frontmatter의 `title`, 첫 번째 H1, 파일명 순서로 선택합니다. 제목 외의 속성은 추가로 매핑할 수 있습니다.

```text
‘팀 기록’의 속성을 확인하고, 문서의 tags를 태그 속성에 매핑해줘.
```

일반 Markdown 문서도 사용할 수 있습니다. [예제 문서](../skills/markdown-notion/assets/example.md)에는 선택적인 frontmatter가 포함되어 있습니다. 별칭 추가만으로 다른 데이터베이스도 연결할 수 있으며 데이터베이스마다 코드를 구현할 필요는 없습니다.

## 여러 연결 토큰 사용

업무용·개인용으로 서로 다른 내부 연결을 만들고 각각의 대상만 공유합니다. 자신의 터미널에서 프로필별로 토큰을 입력합니다.

```sh
uv run --script "$notion_publish_script" auth --profile work
uv run --script "$notion_publish_script" auth --profile personal
```

그다음 AI에게 등록을 요청합니다.

```text
WORK_DATABASE_URL을 ‘팀 기록’으로 등록하고 work 프로필을 사용해줘.
PERSONAL_DATABASE_URL을 ‘개인 메모’로 등록하고 personal 프로필을 사용해줘.
```

별칭별로 사용할 토큰을 고르는 구조입니다. 권한 자체는 Notion 내부 연결에서 제한합니다. 동일한 로컬 에이전트가 두 프로필을 모두 사용할 수 있으므로 에이전트 간 격리를 제공하는 기능은 아닙니다.

## 저장되는 정보

| 위치 | 내용 |
| --- | --- |
| macOS 키체인 `markdown-notion` 서비스 | 프로필별 연결 토큰 |
| `~/.config/markdown-notion/config.json` | 문서 폴더·대상 ID·속성 매핑·프로필 이름 |
| `~/.local/share/markdown-notion/state.json` | 로컬 파일과 페이지의 연결·해시·게시 상태 |

설정과 이력에 토큰·본문은 저장하지 않습니다. 로컬 경로와 Notion 주소는 포함되므로 공개 레포에 올리지 않습니다. 이력은 같은 페이지를 갱신하는 데 필요하므로 보존하세요. PC를 바꾸거나 이력을 잃었다면 [복구 절차](../skills/markdown-notion/references/usage.md)를 따릅니다.

스크립트는 Notion API에 본문을 보냅니다. AI가 원문을 읽거나 도구 출력에 본문이 포함되면 그 내용은 AI 컨텍스트에도 들어갈 수 있습니다. MCP 미사용이 문서의 AI 서버 전송 차단을 의미하지는 않습니다.

세부 명령·변환 제한·실패 복구는 [명령과 복구](../skills/markdown-notion/references/usage.md), 선택 기준은 [MCP와의 차이](mcp-comparison.md)를 참고하세요.
