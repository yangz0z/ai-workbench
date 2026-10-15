# 로컬 HTML 빌드

원칙은 React로 구성한 상호작용을 HTML 한 파일에 묶는 것. 공식 web-artifacts-builder의 외부 초기화 스크립트나 전체 shadcn 컴포넌트 묶음을 런타임에 내려받지 않음. 필요한 라이브러리만 일반 패키지 매니저로 설치.

## 작업 공간

기존 아티팩트 소스가 있으면 재사용. 새 작업은 프로젝트의 별도 산출물 폴더 또는 임시 폴더에 package.json을 만들고 React·React DOM·TypeScript 및 필요한 도식 라이브러리만 구성. 사용하지 않는 컴포넌트·스타터 로고를 생성하지 않음. 기존 백엔드 package.json은 건드리지 않음.

상태·선택·시나리오는 React로 관리. 화면 내 선택에 따라 제목·상세 패널·도식 강조가 동일 상태에서 파생되도록 구성. 단순한 결과물은 인라인 HTML/CSS/JS로 작성해 불필요한 빌드 생략 가능.

## 단일 HTML 출력

사용 가능한 기존 번들러가 단일 HTML 출력을 지원하면 우선 사용. 독립 프로젝트에서 확인된 경로는 다음과 같음:

```sh
npm install react react-dom
npm install --save-dev typescript @types/react @types/react-dom parcel html-inline
npx parcel build index.html --dist-dir dist --no-source-maps
npx html-inline dist/index.html > artifact.html
```

index.html은 root 요소와 TSX 진입 스크립트를 참조. 직접 CSS를 사용하면 Tailwind/PostCSS 설정 불필요. Parcel 기본 해석이 가능한 상대 import를 사용하고, 별칭을 사용하는 기존 소스에만 별칭 resolver 추가.

- package.json의 의도하지 않은 main 라이브러리 출력 대상이 HTML 앱 빌드와 충돌하지 않는지 확인
- pnpm의 빌드 스크립트 승인 정책은 현재 버전·환경을 확인. 필요한 네이티브 의존성만 검토해 설정하고 승인 정책을 일괄 해제하지 않음
- HTML 인라인 도구가 module script, 동적 import, worker, 폰트와 이미지를 모두 포함했는지 실제 출력으로 확인. 파일이 생성되었다는 이유만으로 단일 파일 성공을 선언하지 않음
- 외부 폰트/CDN이나 원격 API 없이는 동작하지 않는 부분을 남기지 않음. 자료에서 추린 텍스트를 외부 폰트 서비스에 전송하지 않음
- 외부 파일 의존을 제거하기 어려우면 단일 HTML이라고 부르지 말고 실제 구성과 실행 방법을 밝힘

## 검증과 보관

1. 작성한 소스의 타입 검사와 빌드
2. 네트워크를 차단한 헤드리스 브라우저에서 file URL로 최종 HTML 실행
3. 주제 전환, 도식 노드 선택, 정상·실패 경로, 되돌리기·초기화 등 핵심 조작 검사
4. 시나리오별 노드·연결선·분기 라벨 강조와 다른 경로 흐림 확인. 현재 단계의 연노랑 배경·기본 선 굵기, 단계 변경 시 조작부 위치 유지 확인
5. 화면 공유 해상도에서 스크린샷 확인. 연결선의 곡률·노드 경계 접점·화살표 방향과 라벨 겹침 확인. 작은 화면은 별도 확인하고 도식 확대·맞춤 검증
6. 최종 HTML과 재빌드 가능한 소스·패키지 설정·잠금 파일·빌드 명령을 함께 보관. node_modules와 캐시는 산출물에 포함하지 않음

브라우저 창을 직접 열지 않고 링크와 여는 방법 안내. 프로젝트 코드 동작을 바꾸지 않는 설명용 아티팩트에는 백엔드 전체 테스트를 불필요하게 실행하지 않음.
