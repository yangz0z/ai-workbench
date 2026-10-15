# 핵심 설계를 탐색하는 HTML 만들기

`web-artifacts`는 프로젝트의 코드·스키마·테스트를 바탕으로 설계를 설명하는 인터랙티브 HTML을 만드는 AI 스킬입니다. 실제 결과물은 Claude Code·Codex 같은 AI 도구가 작성합니다. 고정된 프로젝트 화면이나 자동 게시 도구가 아니라, 무엇을 설명할지와 어떻게 표현하고 검증할지를 정한 제작 지침입니다.

## 설치

Node.js와 npm에 포함된 `npx`가 필요합니다. 아래 명령으로 실행 환경을 확인합니다.

```sh
node --version
npx skills --help
```

원하는 스킬만 사용자 전역에 설치합니다. 저장소를 직접 클론할 필요는 없습니다.

```sh
npx skills add yangz0z/ai-workbench --skill web-artifacts -g
```

설치 과정에서 Claude Code·Codex 등 사용할 AI 도구를 선택합니다. 도구까지 지정하려면 아래 중 하나를 실행합니다.

```sh
# Claude Code
npx skills add yangz0z/ai-workbench --skill web-artifacts -g --agent claude-code

# Codex
npx skills add yangz0z/ai-workbench --skill web-artifacts -g --agent codex
```

두 도구에 함께 설치하려면 `--agent claude-code codex`로 지정합니다. `-g`를 빼면 현재 프로젝트에만 설치합니다. 기존에 같은 이름의 개인 스킬이 있다면 덮어쓰기 전에 내용을 확인하세요. 설치 후 스킬이 보이지 않으면 새 세션을 시작합니다.

처음 실행할 때 Skills CLI 다운로드를 물을 수 있으며 인터넷 연결이 필요합니다. CLI가 저장소를 임시로 가져와 선택한 스킬 폴더를 설치합니다. 전체 저장소를 작업 폴더에 보관하거나 직접 심볼릭 링크를 만들 필요는 없습니다.

설치 확인과 업데이트:

```sh
npx skills list -g
npx skills update web-artifacts -g
```

이 가이드의 파일 경로 예시는 기본 전역 설치 위치인 `~/.agents/skills/web-artifacts`를 기준으로 합니다. 프로젝트 설치라면 프로젝트의 `.agents/skills/web-artifacts`로 바꾸고, 별도 경로를 사용했다면 설치 결과에 나온 경로를 따릅니다. [Skills CLI 사용법](https://github.com/vercel-labs/skills)

다른 스킬, Notion 계정, 개인 설정 저장소는 필요하지 않습니다. React 기반 제작에는 Node.js와 패키지 매니저가 필요하고, 검증에는 Playwright 같은 헤드리스 브라우저 도구가 필요합니다. 간단한 도식은 빌드 없이 HTML/CSS/JavaScript로 작성할 수 있습니다. 제작 시 패키지 설치에는 네트워크가 필요할 수 있지만, 완성 HTML은 오프라인에서 동작하도록 검증합니다.

## 사용

설명할 프로젝트를 AI 도구로 열고 요청합니다.

```text
$web-artifacts로 이 프로젝트의 핵심 설계를 설명하는 HTML을 만들어줘.
코드와 스키마를 확인해서 필요한 도식을 골라줘.
전체 아키텍처와 주요 요청의 정상·실패 흐름을 중심으로 보여줘.
결과 HTML과 재빌드 가능한 소스는 ./artifacts에 저장해줘.
```

현재 결과물을 수정할 때도 같은 스킬을 사용합니다.

```text
$web-artifacts로 artifacts/design.html을 수정해줘.
아키텍처에서 노드를 선택하면 직접 연결된 노드와 선만 강조해줘.
ERD에는 테이블명 오른쪽에 전체 스키마 상세보기 아이콘을 넣어줘.
```

## 제작 기준

| 항목 | 기본 규칙 |
| --- | --- |
| 내용 | 실제 코드·스키마·테스트에서 핵심 요구사항과 설계 이유를 확인 |
| 화면 | 큰 도식이 중심, 짧은 설명은 보조 패널 |
| 디자인 | 무채색 기본 UI, 상태·필터에 제한적으로 색 사용, 현재 단계는 연노랑 |
| 노드 선택 | 선택한 노드와 직접 연결된 노드·연결선만 강조 |
| 시나리오 | 전체 경로와 분기 라벨을 강조하고 다른 경로는 흐리게 표시 |
| 단계 이동 | 다음·이전·처음부터 버튼은 설명 길이와 무관하게 같은 위치 유지 |
| ERD | 테이블명·PK/FK·관계만 기본 표시, 나머지 컬럼·제약·인덱스는 테이블명 옆 아이콘의 전체 스키마 팝업에서 확인 |
| 팝업 | 바깥 클릭·Escape·닫기 버튼 지원, 내부 클릭 유지, 닫은 뒤 포커스 복귀 |
| 전달 | 오프라인 단일 HTML과 재빌드용 소스·설정·잠금 파일 보관 |

아키텍처, ERD, 시퀀스, 플로우차트, 상태 전이, 시간 계산, 동시 처리 도식 중 해당 프로젝트를 설명하는 데 필요한 것만 만듭니다. 사용자가 다른 디자인이나 구성을 지정하면 그 요청을 우선합니다.

기본 규칙과 토큰은 [SKILL.md](../skills/web-artifacts/SKILL.md)와 [theme.css](../skills/web-artifacts/assets/theme.css)에 있습니다. [내용 선정](../skills/web-artifacts/references/content.md), [도식별 기준](../skills/web-artifacts/references/diagrams.md), [조작 규칙](../skills/web-artifacts/references/interactions.md), [빌드·검증](../skills/web-artifacts/references/build.md)을 필요한 부분부터 확인하세요.

## 결과물 확인

AI는 브라우저 창을 자동으로 열지 않고 결과 경로와 여는 방법을 안내합니다. 파일 탐색기에서 생성된 HTML을 더블클릭해 브라우저로 열면 됩니다. 공유할 때는 HTML 파일만 전달할 수 있고, 수정하려면 함께 보관한 소스를 사용합니다.

주제·시나리오 전환, 단계 이동, 노드 선택과 팝업 조작을 직접 확인하세요. 도식은 실제 시스템을 설명하는 자료이며 실제 DB 조회나 API 실행 화면이 아닙니다. 검증하지 못한 내용은 결과에서 구분하도록 지시합니다.

공개 호스팅이나 외부 업로드는 자동으로 수행하지 않습니다. 외부에 전달할 때는 결과에 포함된 프로젝트 정보의 공유 범위를 확인하세요.
