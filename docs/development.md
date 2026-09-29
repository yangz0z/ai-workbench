# 개발과 검증

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
