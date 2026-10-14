# Status

업데이트: 2026-10-13

## Completed

- [x] Full PRD 형식·KPI 3개와 측정 방법·의미 중심 Epic 소제목 정책을 반영하고 활성 1-Pager 경로를 제거했다. [변경 기록](prd-flow/shared/references/revision-log.md)을 따른다. 공통 경로의 승인된 정책만 최신 원격 기준으로 배포한다.

- [x] `ai-hackathon-runner`를 특정 대회에 종속되지 않는 AI 해커톤·프로토타입 대회 실행 프로토콜로 일반화하고 `rignore/skills` 원격 `main`에 배포
- [x] 스킬명·폴더명·등록 링크·README 자기참조를 `ai-hackathon-runner`로 통일
- [x] Context, Problem Definition, Human Judgment, Scaffolding, Verification, Evidence, Taste, Mock Judge, submission safety, handoff 반영
- [x] 트랙/기업별 병렬 탐색과 문제 후보 비교 규약 추가
- [x] 영상 인사이트 기반 목표 역산, interactive context interview, AI Judge + Persona Judge 이중 심사, milestone별 검증 루프 반영
- [x] 대회별 competition profile·team model·judge pack·submission ledger 템플릿 구조 추가
- [x] 공식 규정이 허용하는 팀 규모에 맞춰 workstream·artifact ownership·Integration DRI를 조정하는 운영 모델 추가
- [x] `prd-flow`, `ai-dlc`, `loop-harness` 배제 정책을 phase별 SoT 조합 정책으로 전환
- [x] 특정 대회 preset을 제거하고 실행 시 공식 원문을 competition profile에 주입하도록 변경
- [x] `ai-dlc`, `loop-harness`, `ux-researcher`, `codex-delegate` 경계 및 root README 갱신
- [x] 범용 Spec-driven QA Agent의 P0~P5와 P6 회사 adapter code path 구현
- [x] Desktop web·responsive mobile web Playwright runner와 Android Emulator·APK Appium adapter 구현
- [x] `spec-bundle-v1`, `scenario-v1`, `runbook-v1`, `result-v1`, Android MCP adapter, independent judge 계약과 표준 라이브러리 validator 구현
- [x] 공개 web·Android 샘플로 회사 adapter와 분리된 contract-valid `result-v1` `pass` 검증
- [x] 회사 Done 게이트가 최신 QA 결과의 context·result·receipt SHA-256, validator SHA-256, Notion projection, ticket·AC source binding을 재검증하도록 연결
- [x] Spec-driven QA Agent 전체 변경을 `rignore/skills` 원격 `main`에 배포
- [x] `prd-flow/data-scientist` evidence-pack·explore·hypothesis 분석 스킬을 `rignore/skills` 원격 `main`에 배포
- [x] `prd-builder-discovery`에 `data-scientist` evidence-pack 선행 분석·Gate 1 근거 연계 규칙 동기화
- [x] Full PRD 기능 요구사항을 `EP-` Epic 단위로 통일하고 Epic 분리 기준·PRD와 티켓의 경계·이름 원칙·권장 작성 수준 반영
- [x] `prd-flow`의 PRD 생성·Notion 투영·동기화·티켓화·wireframe 연계가 Epic 정본을 사용하도록 갱신하고 검증

- [x] Spec-driven QA 스킬을 Claude Code·Codex·Gemini에 등록(2026-10-13). 공통 경로 `~/.agents/skills/prd-flow/spec-driven-qa`가 이 저장소의 `prd-flow/spec-driven-qa`를 가리키는 링크이고, 세 도구의 등록 위치가 그 공통 경로를 가리킨다. 그전에는 어느 도구에서도 스킬이 보이지 않아 2026-09-06 QA를 손으로 했다. 팀 배포용 저장소 반영은 하지 않았다.
- [x] Spec-driven QA `SKILL.md`에 요소의 부재와 숨김을 구분해 증명하는 규칙을 올림(2026-10-13, 커밋 전). 부재는 `locator_result`의 `/count equals 0`으로, 숨김은 `count` 1 이상과 `visible: false`를 함께 확인한다. `absent` 연산자는 JSON 경로가 없는지를 보므로 `/count`에는 쓰지 않는다.
## Pending

- [ ] 실제 해커톤 입력으로 forward test 후 시간 배분·Mock Judge rubric 보정
- [ ] Spec-driven QA P4의 실제 독립 label 30건 이상으로 Cohen's κ 0.6 이상과 자동 Pass precision 기준 확인
- [ ] Spec-driven QA P6의 staging 환경에서 read-only artifact root와 validator hash를 설정하고 실제 Notion Done 전이 smoke test 실행
- [ ] iOS XCUITest provider 구현
- [ ] Spec-driven QA 보완 검토 4건(2026-10-13 검토, 반영 여부는 사람이 정한다). 2026-09-06에 이 스킬 없이 손으로 한 QA의 경험을 계약 문서와 대조해 나온 항목이다.
  - 사람이 정한 사양 충돌 결정을 적는 자리: 판정 규약은 "우선순위가 따로 명시되지 않았다면 Judge가 고르지 않는다"고 쓰지만 명시할 입력이 없어, 사람이 한 번 정한 충돌도 매번 `conflict`로 다시 올라온다. 검토 결론은 결정을 판정 단계가 아니라 시나리오 승인 전에 반영하는 것이다. 판정 단계에서 진 쪽 검사를 빼면 완료된 결과가 모든 oracle 규칙을 정확히 한 번씩 덮어야 한다는 검증 규칙(`E_ORACLE_RESULT_COVERAGE_INVALID`)에 걸리고, 이긴 쪽 사양을 검사하는 규칙도 생기지 않는다. 결정을 적는 형태는 미정이다. 후보는 결정 문서를 별도 source로 bundle에 넣는 방식과 anchor에 선택 관계 필드를 두는 방식 2가지다.
  - 나중 결정이 앞 사양을 덮어쓴 관계: 위 항목과 묶어 다룬다. 날짜 순서로 추론하지 않고 명시된 결정만 따른다.
  - `shared_test` 환경의 판정 규칙: 격리 환경에만 규칙이 있다. 검토 결론은 연산자 종류로 가르지 않고, 검사 대상 데이터의 범위를 시나리오에 적은 뒤 Judge가 식별자를 결정론적으로 대조하는 방향이다. 지금 Judge는 실행 식별자를 보지 않는다.
  - 충돌 후보를 찾는 보조 도구: `source-conflicts-v1`을 받는 쪽만 있고 만드는 쪽이 없다. 같은 expectation이 함께 인용한 anchor 쌍을 열거하는 작은 도구와 시나리오 초안 단계의 사람 검토 중 어느 쪽이 나은지 근거가 없어 보류한다.
- [ ] Direct Notion Done 변경을 찾는 reconcile 정책 구현

## Spec-driven QA 현재 상태

| 단계 | 상태 | 남은 완료 조건 |
| --- | --- | --- |
| P0(스킬 구조) | 완료 | 없음 |
| P1(계약과 validator) | 완료 | 계약 변경 시 회귀 테스트를 유지한다. |
| P2(Playwright web runner) | 완료 | 실제 통합 환경은 version-pinned Playwright와 Chromium을 제공한다. |
| P3(Android MCP adapter) | 승인 실행·runtime·readiness hardening 완료 | UI hierarchy와 Android `logcat` 수집은 후속 vertical slice로 남았다. |
| P4(독립 judge와 calibration) | Judge 구현 완료, 사람 calibration 대기 | 두 사람의 독립 label 30건 이상을 확보한다. |
| P5(회사 독립 파일럿) | 완료 | 없음 |
| P6(회사 adapter 연결) | Code 구현 완료, 운영 smoke test 대기 | Fresh current-contract artifact로 실제 Notion Done 전이를 확인한다. |

## Spec-driven QA 의존성과 리스크

- iOS는 `.app.zip` 등록 contract만 있으며 실행 backend가 없다.
- Android physical device와 AAB는 현재 지원하지 않는다.
- 범용 core는 Playwright production dependency를 포함하지 않으므로 host project가 version-pinned runtime을 제공해야 한다.
- P4의 30건 calibration fixture는 계산 검증용 synthetic data다. 실제 사람 label을 넣기 전에는 semantic 자동 release gate를 활성화할 수 없다.
- 기존 P5 Android 결과는 `runbook_state` 필수화 전 artifact이므로 P6 Done 게이트 증거로 재사용하지 않는다.
- 현재 범용 validator SHA-256은 `sha256:2704231a455a6cc58cfe40dac37ba50ce75c1fe7fce347768b12fb9f9a04fc4d`다. Validator 파일을 바꾸면 회사 adapter의 allowlist도 갱신해야 한다.

## Spec-driven QA 다음 액션

Staging 환경에 `QA_ARTIFACT_ROOT`를 read-only로 mount하고 `QA_VALIDATOR_SHA256`를 pin한다. 새 bundle·scenario·runbook·result·validation receipt를 만든 뒤 QA role로 결과를 기록하고 실제 Notion Done 전이를 확인한다.
