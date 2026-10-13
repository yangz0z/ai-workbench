# 개발과 검증

## markdown-notion

`skills/markdown-notion`은 `SKILL.md`, 실행 스크립트, 사용 가이드, 예제와 테스트로 구성됩니다. 특정 문서 폴더나 개인 설정 저장소에 의존하지 않습니다.

| 파일 | 역할 |
| --- | --- |
| `scripts/notion_publish.py` | 명령 처리와 출력 |
| `scripts/core.py` | Markdown 변환·속성 검증 |
| `scripts/runtime.py` | 키체인·HTTP·로컬 저장과 잠금 |
| `scripts/publishing.py` | 대상 등록·게시·충돌 확인·복구 |

레포 루트에서 실행합니다.

```sh
uv run --with 'PyYAML==6.0.3' --with 'markdown-it-py==4.0.0' --with 'keyring==25.7.0' \
  python -m unittest discover -s skills/markdown-notion/tests -v
```

테스트는 임시 문서·설정·이력과 모의 API를 사용합니다. 문서 변환, 여러 대상 게시, 같은 페이지 갱신, 원격 수정 충돌, 응답 유실·부분 성공 복구, 경로 제한, 토큰 비노출, CLI 미리보기를 확인합니다. 실제 키체인 토큰이나 Notion 계정은 필요하지 않습니다.

모의 테스트 통과가 실계정의 생성·갱신·화면 표시를 보증하지는 않습니다. 실제 연결을 검증할 때는 연결 권한을 부여한 테스트용 데이터베이스에서 예제 문서로 생성 → 원문 수정 → 같은 페이지 갱신을 확인합니다. 이 공개 패키지의 실계정 게시 검증은 아직 수행하지 않았습니다.

사용 API 버전은 `2026-03-11`입니다. [Markdown 콘텐츠](https://developers.notion.com/guides/data-apis/working-with-markdown-content)와 [본문 교체](https://developers.notion.com/reference/update-page-markdown)의 계약을 따릅니다. 속성 갱신과 본문 교체는 별도 요청이며, 두 요청 중 하나만 성공할 수 있어 `pending` 상태로 복구를 요구합니다. 원격 확인과 쓰기 사이의 동시 편집을 원자적으로 차단하지는 않습니다.

변경을 공개할 때는 토큰, 개인 Notion 주소, 실제 설정·이력 파일을 포함하지 않습니다. 테스트에는 임의 식별자만 사용합니다.


## notion-prototype

`skills/notion-prototype`은 다른 스킬이나 개인 설정 저장소에 의존하지 않는다.

| 파일 | 역할 |
| --- | --- |
| `scripts/notion_prototype.py` | 인증·미리보기·게시·조회·복구 CLI |
| `scripts/prototype.py` | HTML 검사·HTTP·키체인·게시 이력·충돌 처리 |
| `assets/example.html` | 입력 변경과 명시적 확인 흐름을 체험하는 단일 HTML |
| `references/usage.md` | 명령 계약과 실패 복구 |

레포 루트에서 표준 라이브러리만으로 모의 테스트를 실행한다. 실제 토큰이나 네트워크는 필요 없다.

```sh
python3 -m unittest discover -s skills/notion-prototype/tests -v
python3 skills/notion-prototype/scripts/notion_prototype.py preview skills/notion-prototype/assets/example.html
```

테스트는 새 게시·같은 파일 재게시·교체 순서·원격 변경·응답 유실·부분 실패·복구·인증정보 비노출·이력 잠금을 검증한다. 두 스킬의 테스트는 위 명령과 기존 명령으로 각각 실행한다.

브라우저에서 `assets/example.html`을 열고 입력 → 확인 → 입력 변경 → 이전 결과 유지와 안내 → 재확인 → 초기화를 검증한다. 좁은 화면에서 잘림도 확인한다.

공개 패키지의 실계정 게시 검증은 아직 수행하지 않았다. 기반이 된 로컬 구현에서 HTML 업로드·블록 생성·교체·맨 위 배치를 확인했지만, 그것이 이 패키지의 인증·게시 이력·복구 흐름까지 검증한 것은 아니다. 실계정 검증은 내부 연결이 허용된 테스트 페이지에서 생성 → 같은 파일 재게시 → 변경 게시 → 원격 조회 순서로 수행한다.

Notion HTML 등록은 API 버전 `2026-03-11`의 `file_uploads`와 `embed.file_upload`를 사용한다. 업로드·삽입·기존 블록 제거는 별도 요청이다. 쓰기 전 `pending`을 저장하고 중간 식별자를 기록하며, 불명확한 실패는 자동 재시도하지 않는다. 수정 시각 비교가 동시 편집을 원자적으로 막지는 못한다.
