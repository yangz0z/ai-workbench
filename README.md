# ai-workbench

개발 업무에 바로 가져다 쓸 수 있는 AI 스킬과 자동화 도구 모음입니다.

## markdown-notion

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
