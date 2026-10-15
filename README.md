# ai-workbench

개발 업무에 바로 가져다 쓸 수 있는 AI 스킬과 자동화 도구 모음입니다.

## 스킬 목록

| 스킬 | 용도 | 사용 가이드 |
| --- | --- | --- |
| [web-artifacts](#web-artifacts) | 코드에 근거한 설계·흐름을 인터랙티브 HTML로 제작 | [설치·사용법](docs/web-artifacts.md) |
| [notion-prototype](#notion-prototype) | 채팅 기획을 클릭형 HTML로 만들어 Notion에 공유 | [설치·사용법](docs/notion-prototype.md) |
| [markdown-notion](#markdown-notion) | 로컬 Markdown을 Notion 데이터베이스에 게시·갱신 | [설치·사용법](docs/markdown-notion.md) |

각 스킬은 독립 설치할 수 있습니다. `markdown-notion`은 페이지 본문 전체를 교체하므로 두 스킬은 별도 페이지에서 사용하고 링크로 연결하세요. Notion 연동 두 스킬의 게시에는 macOS·Python 3.11 이상·uv와 Notion 내부 연결이 필요합니다.

## 설치

Node.js와 npm에 포함된 `npx`가 필요합니다. `node --version`과 `npx skills --help`로 실행 환경을 확인하세요.

`{스킬명}`을 위 목록에 있는 이름으로 바꿔 실행합니다. 예를 들어 `web-artifacts`를 설치하려면 `{스킬명}` 부분을 중괄호 없이 `web-artifacts`로 바꿉니다.

```sh
npx skills add yangz0z/ai-workbench --skill {스킬명} -g
```

**Claude Code와 Codex 두 도구에 함께 설치하려면** 다음 명령을 사용합니다. 같은 스킬을 두 도구에서 사용할 수 있도록 한 번에 설치합니다.

```sh
npx skills add yangz0z/ai-workbench --skill {스킬명} -g --agent claude-code codex
```

- `--agent`를 생략하면 설치 과정에서 사용할 AI 도구를 선택합니다. 한 도구만 지정하려면 `--agent claude-code` 또는 `--agent codex`를 사용합니다.
- `-g`는 사용자 전역 설치이며, 빼면 현재 프로젝트에만 설치합니다.
- 저장소를 직접 클론할 필요는 없습니다. CLI가 저장소를 임시로 가져와 선택한 스킬을 설치합니다. 처음 실행할 때 CLI 다운로드를 물을 수 있으며 인터넷 연결이 필요합니다.
- 기존에 같은 이름의 스킬이 있으면 덮어쓰기 전에 내용을 확인하세요. 설치 후 스킬이 보이지 않으면 새 세션을 시작합니다.
- Notion 스킬의 실행 환경과 인증 준비는 각 사용 가이드를 따릅니다.

설치 확인과 업데이트에도 같은 스킬 이름을 사용합니다.

```sh
npx skills list -g
npx skills update {스킬명} -g
```

가이드의 실행 파일 경로는 기본 전역 설치 위치인 `~/.agents/skills/{스킬명}`을 기준으로 합니다. 프로젝트 설치라면 프로젝트의 `.agents/skills/{스킬명}`으로 바꾸고, 별도 경로를 사용했다면 설치 결과에 나온 경로를 따릅니다. [Skills CLI 사용법](https://github.com/vercel-labs/skills)

## 스킬 상세

### web-artifacts

프로젝트의 코드·스키마·테스트를 읽어 핵심 설계를 도식 중심의 인터랙티브 HTML로 만드는 스킬입니다. 큰 도식과 짧은 상세 패널로 구성하며, 선택한 노드의 연결 관계나 정상·실패 시나리오를 직접 따라갈 수 있습니다.

> “web-artifacts로 이 프로젝트의 핵심 설계를 HTML로 만들어줘. 코드와 일치하는 아키텍처와 주요 처리 흐름을 보여줘.”

- **코드에 근거한 설계 설명**: 아키텍처·ERD·시퀀스·상태 전이 중 설명에 필요한 도식을 선택합니다.
- **일관된 UI와 조작**: 무채색 UI, 연노랑 현재 단계, 연결 경로 강조, 고정 단계 버튼과 전체 스키마 팝업 규칙을 제공합니다.
- **로컬 파일로 전달**: 단일 HTML과 수정용 소스를 생성합니다. 게시·인증 없이 브라우저에서 열 수 있습니다.

[설치·사용법](docs/web-artifacts.md) · [제작 스킬](skills/web-artifacts/SKILL.md) · [UI 테마](skills/web-artifacts/assets/theme.css) · [샘플 보기](https://yangz0z.github.io/ai-workbench/)

---

### notion-prototype

채팅으로 설명한 화면을 클릭형 HTML 프로토타입으로 만들고 기존 Notion 페이지에 게시하는 스킬입니다. 개발 티켓에서 버튼 위치, 입력 기본값, 처리 전후 상태를 팀원과 직접 눌러보며 확인할 수 있습니다.

> “행사 신청 화면을 만들어줘. 확인 버튼을 눌렀을 때만 요약을 보여줘.”
> “이 HTML을 Notion 티켓 맨 위에 올리고, 수정하면 같은 위치에 반영해줘.”

- **기획을 동작하는 화면으로**: AI가 단일 HTML을 작성하고 브라우저에서 확인합니다. 예시 데이터와 테스트 전용 버튼을 구분합니다.
- **Notion 안에서 체험**: HTML 파일을 업로드하므로 별도 웹 호스팅이 필요하지 않습니다.
- **해당 HTML만 갱신**: 페이지별 연결 이력, 같은 파일 재게시 생략, 원격 변경 확인과 중간 실패 복구를 제공합니다.

[설치부터 첫 게시까지](docs/notion-prototype.md) · [명령과 복구](skills/notion-prototype/references/usage.md) · [체험하기](https://yangz0z.github.io/ai-workbench/notion-prototype/) · [HTML 원본](skills/notion-prototype/assets/example.html)

---

### markdown-notion

로컬 Markdown 문서를 정해진 Notion 데이터베이스에 게시하고, 수정할 때마다 같은 항목에 반영하는 스킬입니다.

> “회의록.md를 팀 기록에 올려줘.”
> “내용을 수정했으니 같은 항목에 반영해줘.”

- **반복 게시**: 문서와 Notion 페이지의 연결을 기억하고, 데이터베이스별 속성 매핑을 재사용합니다.
- **접근 범위 지정**: Notion 내부 연결에 허용한 페이지·데이터베이스에 접근하며, 대상별로 서로 다른 연결 토큰을 사용할 수 있습니다.
- **MCP 서버 설정 없이 연결**: AI가 로컬 스크립트를 실행하고, 스크립트가 Notion API를 직접 호출합니다.

현재 macOS, Python 3.11 이상, uv가 필요합니다. Claude Code·Codex의 로컬 스킬로 설치할 수 있습니다.

[설치와 첫 게시](docs/markdown-notion.md) · [명령과 복구](skills/markdown-notion/references/usage.md) · [MCP와의 차이](docs/mcp-comparison.md) · [개발·검증](docs/development.md)

---

## 라이선스

[MIT](LICENSE)
