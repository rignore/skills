# Status

업데이트: 2026-08-12

## Completed

- [x] `ax-assessment-runner`를 시험/70분 PRD 구현용에서 AX 인재전쟁·기업 과제형 해커톤용 실행 프로토콜로 재설계
- [x] Context, Problem Definition, Human Judgment, Scaffolding, Verification, Evidence, Taste, Mock Judge, submission safety, handoff 반영
- [x] 트랙/기업별 병렬 탐색과 문제 후보 비교 규약 추가
- [x] 영상 인사이트 기반 목표 역산, interactive context interview, AI Judge + Persona Judge 이중 심사, milestone별 검증 루프 반영
- [x] 대회별 competition profile·team model·judge pack·submission ledger 템플릿 구조 추가
- [x] 1~4인 팀 workstream·artifact ownership·Integration DRI 운영 모델 추가
- [x] `prd-flow`, `ai-dlc`, `loop-harness` 배제 정책을 phase별 SoT 조합 정책으로 전환
- [x] 2026 금융 AI Challenge preset 추가
- [x] `ai-dlc`, `loop-harness`, `ux-researcher`, `codex-delegate` 경계 및 root README 갱신
- [x] 범용 Spec-driven QA Agent의 P0~P5와 P6 회사 adapter code path 구현
- [x] Desktop web·responsive mobile web Playwright runner와 Android Emulator·APK Appium adapter 구현
- [x] `spec-bundle-v1`, `scenario-v1`, `runbook-v1`, `result-v1`, Android MCP adapter, independent judge 계약과 표준 라이브러리 validator 구현
- [x] 공개 web·Android 샘플로 회사 adapter와 분리된 contract-valid `result-v1` `pass` 검증
- [x] 회사 Done 게이트가 최신 QA 결과의 context·result·receipt SHA-256, validator SHA-256, Notion projection, ticket·AC source binding을 재검증하도록 연결
- [x] Spec-driven QA Agent 전체 변경을 `rignore/skills` 원격 `main`에 배포

## Pending

- [ ] 실제 해커톤 입력으로 forward test 후 시간 배분·Mock Judge rubric 보정
- [ ] Spec-driven QA P4의 실제 독립 label 30건 이상으로 Cohen's κ 0.6 이상과 자동 Pass precision 기준 확인
- [ ] Spec-driven QA P6의 staging 환경에서 read-only artifact root와 validator hash를 설정하고 실제 Notion Done 전이 smoke test 실행
- [ ] iOS XCUITest provider 구현
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
