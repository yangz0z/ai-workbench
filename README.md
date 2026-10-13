# ai-workbench

개발 업무에 바로 가져다 쓸 수 있는 AI 스킬과 자동화 도구 모음입니다.

## 스킬 목록

| 스킬 | 용도 | 사용 가이드 |
| --- | --- | --- |
| [notion-prototype](#notion-prototype) | 채팅 기획을 클릭형 HTML로 만들어 Notion에 공유 | [설치·사용법](docs/notion-prototype.md) |
| [markdown-notion](#markdown-notion) | 로컬 Markdown을 Notion 데이터베이스에 게시·갱신 | [설치·사용법](docs/markdown-notion.md) |

각 스킬은 독립 설치할 수 있습니다. `markdown-notion`은 페이지 본문 전체를 교체하므로 두 스킬은 별도 페이지에서 사용하고 링크로 연결하세요. 두 스킬 모두 게시에는 macOS·Python 3.11 이상·uv와 Notion 내부 연결이 필요합니다.

## 스킬 상세

### notion-prototype

채팅으로 설명한 화면을 클릭형 HTML 프로토타입으로 만들고 기존 Notion 페이지에 게시하는 스킬입니다. 개발 티켓에서 버튼 위치, 입력 기본값, 처리 전후 상태를 팀원과 직접 눌러보며 확인할 수 있습니다.

> “행사 신청 화면을 만들어줘. 확인 버튼을 눌렀을 때만 요약을 보여줘.”
> “이 HTML을 Notion 티켓 맨 위에 올리고, 수정하면 같은 위치에 반영해줘.”

- **기획을 동작하는 화면으로**: AI가 단일 HTML을 작성하고 브라우저에서 확인합니다. 예시 데이터와 테스트 전용 버튼을 구분합니다.
- **Notion 안에서 체험**: HTML 파일을 업로드하므로 별도 웹 호스팅이 필요하지 않습니다.
- **해당 HTML만 갱신**: 페이지별 연결 이력, 같은 파일 재게시 생략, 원격 변경 확인과 중간 실패 복구를 제공합니다.

[설치부터 첫 게시까지](docs/notion-prototype.md) · [명령과 복구](skills/notion-prototype/references/usage.md) · [체험용 HTML](skills/notion-prototype/assets/example.html)

### markdown-notion

로컬 Markdown 문서를 정해진 Notion 데이터베이스에 게시하고, 수정할 때마다 같은 항목에 반영하는 스킬입니다.

> “회의록.md를 팀 기록에 올려줘.”
> “내용을 수정했으니 같은 항목에 반영해줘.”

- **반복 게시**: 문서와 Notion 페이지의 연결을 기억하고, 데이터베이스별 속성 매핑을 재사용합니다.
- **접근 범위 지정**: Notion 내부 연결에 허용한 페이지·데이터베이스에 접근하며, 대상별로 서로 다른 연결 토큰을 사용할 수 있습니다.
- **MCP 서버 설정 없이 연결**: AI가 로컬 스크립트를 실행하고, 스크립트가 Notion API를 직접 호출합니다.

현재 macOS, Python 3.11 이상, uv가 필요합니다. Claude Code·Codex의 로컬 스킬로 설치할 수 있습니다.

[설치와 첫 게시](docs/markdown-notion.md) · [명령과 복구](skills/markdown-notion/references/usage.md) · [MCP와의 차이](docs/mcp-comparison.md) · [개발·검증](docs/development.md)

## 라이선스

[MIT](LICENSE)
