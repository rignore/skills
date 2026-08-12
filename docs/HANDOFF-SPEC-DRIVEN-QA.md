# 핸드오프 — prd-flow 범용 Spec-driven QA Agent

작성일: 2026-08-01

대상 독자: 다음 구현을 맡을 Codex·Claude Code와 QA 인프라 엔지니어

기준 저장소: `/Users/igeun-won/skills` (`https://github.com/rignore/skills`)

현재 브랜치와 커밋: `main`, `29056e7 Merge pull request #3 from rignore/skills-upload-anonymized-20260722`

## 1. 지금 어디까지 왔나

범용 QA Agent의 배치 위치와 플랫폼 경계를 확정했다. 구현은 아직 시작하지 않았다. `/Users/igeun-won/skills` 작업 트리는 이 문서 작성 전까지 깨끗했다.

확정한 내용은 다음과 같다.

- 신규 스킬 이름은 `spec-driven-qa`다. 프로토타입뿐 아니라 개발자가 구현한 웹·네이티브 앱을 검증한다.
- 범용 코어는 개인 저장소 `rignore/skills`의 `prd-flow/spec-driven-qa`에 둔다.
- `idbrnd/prd-flow-copilot`은 필수 의존성이 아니다. Notion 입력, 검증 코멘트, Done 게이트를 제공하는 선택형 회사 adapter(외부 시스템 연결부)로만 남긴다.
- 실행 구조는 시나리오 생성, 결정론적 실행, 독립 판정의 세 층으로 나눈다.
- desktop web과 responsive mobile web은 Playwright provider가 실행한다.
- Android native app은 `/Users/igeun-won/Documents/video`의 Demo Video MCP가 구현한 Appium UiAutomator2 실행 방식을 adapter로 재사용한다.
- iOS native app은 스키마에 포함하지만 실행 가능하다고 표시하지 않는다. Demo Video MCP는 `.app.zip` 등록만 지원하고 XCUITest backend가 없다.
- 테스트 증거는 구조화된 로그, UI hierarchy(네이티브 화면 요소 트리), locator 결과, API·DB 상태, 테스트 명령, build·artifact hash를 우선한다.

기존 구현 중 재사용 가능한 자산은 회사 저장소에 이미 병합됐다.

| 자산 | 현재 위치 | 재사용 방식 |
| --- | --- | --- |
| `qa_package` | `/Users/igeun-won/prd-flow-copilot/internal/qa` | Notion과 inspection-mode 자료를 범용 `spec-bundle`로 변환하는 source adapter로 전환한다. |
| `record_verification` | `/Users/igeun-won/prd-flow-copilot/internal/tickets/verification.go` | 범용 결과를 Notion 코멘트에 쓰는 result sink로 남긴다. |
| Done 검증 게이트 | `/Users/igeun-won/prd-flow-copilot/internal/tickets/status.go` | 회사 티켓 운영에만 적용한다. 범용 코어는 상태 전환을 요구하지 않는다. |
| Android Appium runtime | `/Users/igeun-won/Documents/video/src/demo_video_mcp` | 선택형 `native-android` runner provider의 기준 구현으로 사용한다. |

범용 구현 작업 중인 파일은 없다. 이 문서와 `/Users/igeun-won/skills/status.md`만 신규 파일이며 아직 commit·push하지 않았다.

## 2. 최종 아키텍처와 지원 범위

`spec-driven-qa`는 네 종류의 provider contract(입력원·실행기·판정기·결과 저장소를 교체하는 규약)로 외부 시스템을 분리한다.

```text
Spec Source Provider
  PRD · Acceptance Criteria · 정책 · 디자인을 spec-bundle로 정규화

Scenario Planner
  spec-bundle에서 source reference가 있는 시나리오를 생성

Runner Provider
  web-playwright | native-android | native-ios | developer-test | manual

Judge
  expected와 observed evidence를 대조해 판정

Result Sink
  local file이 기본값이며 Notion · GitHub · Linear 등은 선택 adapter
```

플랫폼 지원 목표는 다음과 같다.

| 대상 | 실행 provider | 상태 | 비고 |
| --- | --- | --- | --- |
| Desktop web | Playwright | 구현 예정 | 실제 서비스 URL에서 실행한다. |
| Responsive mobile web | Playwright device context | 구현 예정 | Chromium 반응형 화면이다. 네이티브 앱으로 분류하지 않는다. |
| Android native app | Appium UiAutomator2 + Emulator | 기준 구현 확인, QA adapter 미구현 | Demo Video MCP의 runtime·artifact·승인 구조를 재사용한다. |
| iOS native app | XCUITest + Simulator | contract only | provider가 없으므로 실행 요청은 `unsupported`로 종료한다. |
| Unit·integration | 개발자 테스트 runner | 기존 회사 adapter 있음 | 브라우저나 Appium으로 대체하지 않는다. |
| 물리 센서·장비 | Manual | 시나리오 라우팅만 | 사람이 수행한 로그와 결과를 수집한다. |

범용 스킬의 권장 구조는 다음과 같다.

```text
prd-flow/spec-driven-qa/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── validate-contracts.py
│   ├── compile-web-runbook.mjs
│   └── aggregate-results.py
└── references/
    ├── input-contract.md
    ├── scenario-schema.md
    ├── runner-provider-contract.md
    ├── native-mcp-adapter.md
    ├── judge-protocol.md
    └── result-schema.md
```

프로젝트별 QA 산출물은 해당 프로젝트의 `qa/`에 생성한다.

```text
qa/
├── qa.config.yaml
├── spec-bundle.json
├── scenarios.yaml
├── runbooks/
│   ├── web.json
│   └── native-android.json
└── results/
    └── <run-id>.json
```

## 3. 공통 시나리오와 판정 계약

공통 시나리오는 플랫폼에 종속되지 않는 필드와 runner 전용 필드를 분리한다.

필수 공통 필드:

- `id`, `title`, `source_refs`
- `method`: `web | native | unit | integration | manual`
- `preconditions`, `fixture`(테스트 상태를 만드는 고정 데이터)
- `steps`, `expected`, `oracle`(Pass/Fail 판정 기준)
- `severity`, `spec_version`, `review_status`
- `target.platform`: `web | mobile_web | android | ios`
- `runner_provider`

모든 시나리오는 Ticket AC, 정책 anchor, PRD 기능 anchor, 디자인 frame 중 하나 이상을 참조해야 한다. 참조가 없으면 실행하지 않는다.

판정 결과는 아래 여섯 값으로 고정한다.

| 판정 | 의미 |
| --- | --- |
| `pass` | 명세와 관측 결과가 일치한다. |
| `fail` | 관측 결과가 명세와 다르다. |
| `conflict` | PRD, AC, 정책, 디자인이 서로 다른 정답을 요구한다. |
| `insufficient_evidence` | 실행했지만 판정에 필요한 증거가 없다. |
| `blocked` | 환경, 인증, fixture, runtime 문제로 실행하지 못했다. |
| `unsupported` | 요청한 플랫폼 provider가 없다. 현재 iOS 실행이 여기에 해당한다. |

정확한 값, 존재 여부, 상태 코드는 deterministic oracle이 먼저 판정한다. 의미 동치처럼 규칙으로 확정할 수 없는 항목만 독립 LLM judge에 넘긴다. 실행 agent의 자기 보고는 증거로 인정하지 않는다.

공통 시나리오 예시는 다음과 같다.

- 근거: `AC-2(저장 완료 상태 반영)`는 저장 성공 뒤 상태가 `완료`여야 한다고 명시한다.
- Web runner: 테스트 fixture를 열고 저장 버튼을 누른 다음 API 응답과 DOM 상태를 수집한다.
- Android runner: 동일 fixture를 연다. `accessibility_id=Save` control을 누른 다음 `id=status-complete`가 나타나는지 확인한다.
- 판정: 두 플랫폼 모두 API 또는 integration test 로그가 저장 성공을 확인해야 한다. 화면만 `완료`이고 backend 상태가 `대기`라면 `fail`이다.
- 안전장치: 저장은 mutation이므로 격리된 테스트 fixture와 승인된 시나리오에서만 실행한다.

## 4. Android 네이티브 앱 연동 기준

참조 구현은 `/Users/igeun-won/Documents/video`의 Demo Video MCP다. 이 MCP는 제품과 분리된 로컬 `stdio` 서버이며 Android Emulator에서 Appium UiAutomator2를 실행한다.

현재 재사용 가능한 계약:

- `register_native_app`: APK를 절대 경로로 등록하고 SHA-256으로 고정한다. MCP는 복사본을 권한 `0600`의 비공개 저장소에 둔다.
- `get_native_runtime_status`: `adb`, Emulator·AVD, Appium, UiAutomator2, FFmpeg를 점검한다.
- `inspect_native_app`: 사용자가 앱 실행의 network effect(외부 API 호출처럼 앱 밖의 상태에 주는 영향)를 승인한 뒤 resource ID, accessibility label, class, locator 후보를 수집한다.
- `get_native_video_scenario_schema`: Android action과 locator schema를 제공한다.
- `create_native_video_job`: 동결된 시나리오와 app artifact를 job에 결합한다.
- `preflight_video_job`: runtime, artifact hash, frozen plan, mutation step(외부 상태를 바꿀 수 있는 실행 단계)을 검사한다.
- `approve_video_job`: 사용자가 승인한 mutation step을 고정한다.
- `start_video_job`, `get_video_job`: worker를 비동기로 실행하고 상태와 manifest를 반환한다.

QA adapter가 Demo Video MCP에서 재사용할 Android action은 다음과 같다.

- 앱 실행: `launch`
- 상태 대기: `wait_for`
- 사용자 조작: `tap`, `fill`, `press_key`, `back`, `swipe`
- 실행 제어: `pause`

locator 우선순위는 `accessibility_id`, `id`, `text`, `class_name`, `xpath` 순으로 둔다. 좌표 기반 tap은 공통 계약에 넣지 않는다.

QA adapter는 영상 제작 기능 전체를 가져오지 않는다.

- 자막과 영상 편집 계약은 사용하지 않는다.
- MP4는 QA 완료 증거의 필수 항목이 아니다.
- Native Scenario의 `wait_for present|absent`와 step result는 기본 deterministic evidence로 쓴다.
- 앱 artifact ID, SHA-256, package ID, Emulator·OS, orientation, reset policy를 결과에 기록한다.
- UI hierarchy의 필요한 항목만 수집하고 비밀번호·token·입력값은 제거한다.
- backend 상태 판정에는 앱 화면이 아니라 API, DB, integration test 로그를 사용한다.

현재 MCP만으로 부족한 항목도 있다.

- Native Scenario에는 QA의 `expected`, `oracle`, `source_refs`가 없다. 범용 시나리오가 이 필드를 소유해야 한다.
- 실행 중 UI hierarchy snapshot을 결과 manifest에 남기는 공통 evidence contract가 없다.
- Android `logcat` 수집이 없다. native runner provider에 별도 로그 수집을 추가해야 한다.
- 현재 worker는 녹화를 항상 수행한다. QA 전용 실행에서는 recording을 선택 항목으로 분리해야 한다.
- Emulator 로그인 재현은 `reset_policy: preserve`에 의존한다. 암호화된 native profile은 아직 없다.

MVP에서는 Demo Video MCP를 외부 runner provider로 호출한다. runtime 코드를 `spec-driven-qa`에 복사하지 않는다. 기본 존재·부재 판정을 파일럿한 뒤, QA 전용 job API가 필요한지 또는 공통 device runtime package를 분리할지 결정한다.

## 5. 다음에 할 일

### P0. 스킬 scaffold 생성

`/Users/igeun-won/skills`에서 `spec-driven-qa`를 초기화한다. 회사 저장소에서 시작하지 않는다.

완료 기준:

- `SKILL.md` description이 웹·Android·iOS contract, 실제 서비스 검증, 명세 기반 QA 요청을 trigger로 포함한다.
- `agents/openai.yaml`이 스킬의 현재 역할과 일치한다.
- `quick_validate.py`가 통과한다.

### P1. schema와 validator 구현

`references/input-contract.md`, `scenario-schema.md`, `result-schema.md`를 먼저 확정한다. `scripts/validate-contracts.py`는 Python 표준 라이브러리만 사용해 다음 오류를 차단한다.

- source reference 없는 시나리오
- 지원하지 않는 platform·method 조합
- iOS 시나리오를 실행 가능으로 표시한 경우
- mutation action에 승인 정책이 없는 경우
- credential, APK bytes, Base64 artifact를 입력에 포함한 경우
- fixture가 필요한 destructive case에 격리 환경이 없는 경우

### P2. web runner provider 구현

Playwright로 desktop web과 responsive mobile web을 실행한다. 저장한 runbook을 반복 재생하며 CI 실행 중에는 LLM을 호출하지 않는다.

수집 항목:

- DOM과 accessibility state
- network·console 오류
- URL과 route state
- API 응답과 테스트가 허용한 storage state
- 실행 명령, build reference, 재시도 횟수

### P3. Android runner adapter 구현

`references/native-mcp-adapter.md`에 Demo Video MCP tool mapping을 작성한다. 첫 파일럿은 다음 범위로 제한한다.

- Emulator only
- APK only
- `wait_for present|absent` deterministic oracle
- `accessibility_id`와 resource ID 우선 locator
- app launch와 사용자 조작 전 mutation preflight
- manual login 후 `reset_policy: preserve`

Native action 이후 상태를 검증할 evidence가 부족하면 `pass`가 아니라 `insufficient_evidence`로 종료한다.

### P4. 독립 judge와 사람 calibration 추가

generator와 judge가 대화 상태를 공유하지 않게 한다. judge는 source reference, expected, observed evidence, rubric만 받는다.

최소 30개 gold case를 두 명이 독립 라벨링한다. Cohen's κ가 0.6 미만이면 자동 판정을 배포하지 않는다. 자동 Pass의 precision을 별도로 측정한다.

### P5. 범용성 파일럿 수행

회사 시스템이 아닌 샘플 두 개로 먼저 검증한다.

1. 로컬 Markdown 명세와 공개 sample web app
2. test APK와 Android Emulator

두 파일럿 모두 `prd-flow-copilot`, Notion, Protect Go plugin 없이 실행돼야 한다.

### P6. 회사 adapter 연결

범용 contract가 고정된 뒤에만 `prd-flow-copilot`을 연결한다.

- `qa_package`가 `spec-bundle-v1`을 반환하도록 변환한다.
- `record_verification`이 `result-v1`의 unit·integration 결과를 저장한다.
- Done 게이트는 회사 운영 정책으로 유지한다.

## 6. 반드시 지킬 것

- core 파일에 회사명, 제품 URL, Notion database ID, 프로젝트명, selector를 넣지 않는다. 해당 값은 project config 또는 optional adapter가 소유한다.
- Android APK는 로컬 절대 경로로만 등록한다. 파일 bytes, Base64, signing key를 MCP argument에 넣지 않는다.
- 비밀번호와 token을 시나리오, 결과, 로그, manifest에 기록하지 않는다.
- responsive mobile web을 native app으로 판정하지 않는다.
- 앱 설치와 실행만으로 API 호출이 발생할 수 있다. `inspect_native_app`도 사용자 확인 없이 호출하지 않는다.
- `launch`, `tap`, `fill`, `press_key`, `back`은 초기 단계에서 potential mutation으로 처리한다.
- mutation action은 자동 재시도하지 않는다. 현재 Demo Video MCP의 `retry_policy: never`를 유지한다.
- 오류·경계 상태는 운영 데이터가 아니라 fixture, mock, seed script, test endpoint로 만든다.
- 영상 파일을 Pass 근거로 사용하지 않는다. 판정은 구조화된 실행 결과와 시스템 상태를 근거로 한다.
- unit·integration 검증을 web·native E2E로 대체하지 않는다.
- iOS provider가 구현되기 전에는 Android 결과를 iOS에 일반화하지 않는다.

## 7. 함정

- `/Users/igeun-won/prd-flow`는 `idbrnd/prd-flow` 회사 저장소다. 범용 스킬 SoT로 사용하지 않는다.
- 기존 `/Users/igeun-won/prd-flow/docs/AUTO-QA-DESIGN.md`는 prototype QA, `SIM_ACTION`, 회사 프로젝트 구조를 전제로 한 초안이다. 아이디어만 참고하고 구현 기준으로 복사하지 않는다.
- 기존 명칭 `prototype-qa`를 사용하면 실제 서비스와 네이티브 앱이 범위 밖으로 오해된다. 신규 명칭은 `spec-driven-qa`로 고정한다.
- Demo Video MCP의 Native Scenario를 그대로 QA scenario로 쓰지 않는다. 해당 schema에는 명세 출처와 oracle이 없다.
- `inspect_native_app`은 control을 누르지 않지만 앱을 설치하고 실행한다. read-only라고 표시하면 안 된다.
- `reset_policy: preserve`는 로그인 상태를 유지하지만 초기 상태 재현성을 보장하지 않는다. 실행 결과에 reset policy와 device 식별자를 남긴다.
- Android physical device는 현재 Native Scenario validator가 거부한다. Emulator 지원과 혼동하지 않는다.
- 원격 Appium URL은 현재 구현이 거부한다. 로컬 `127.0.0.1` server만 지원한다.
- iOS `.app.zip` 등록 성공은 실행 지원을 뜻하지 않는다. XCUITest backend가 없다.
- Android App Bundle(AAB)은 설치용 실행 artifact가 아니므로 현재 provider 입력으로 받지 않는다.
- 현재 Demo Video MCP 작업 트리는 사용자 변경과 생성 artifact가 남아 있다. QA 작업 중 해당 파일을 정리하거나 덮어쓰지 않는다.
- Demo Video MCP의 네이티브 관련 테스트 18건 중 17건은 통과했다. 가짜 Appium W3C 서버를 사용하는 녹화 통합 테스트는 worker가 종료 코드 1을 반환해 실패했으며 원인은 아직 진단하지 않았다.
- `init_skill.py` 직후 `quick_validate.py`를 실행하면 template의 TODO description이 YAML list라서 실패한다. `SKILL.md`의 frontmatter와 본문을 작성한 뒤 검증한다.

## 8. 알려진 미해결

| 항목 | 현재 상태 | 다음 판단 |
| --- | --- | --- |
| Android QA evidence contract | `wait_for`와 step result만 즉시 재사용 가능 | UI hierarchy snapshot과 `logcat`을 result에 추가할 방식을 정한다. |
| Native QA 실행 위치 | Demo Video MCP 호출과 공통 runtime package 분리 두 선택지가 있음 | MVP는 MCP adapter로 시작하고 중복·성능을 측정한다. |
| 녹화 없는 Android 실행 | 현재 native worker는 MP4를 생성함 | QA 전용 job 또는 `recording: optional` 확장을 결정한다. |
| iOS 실행 | `.app.zip` 등록만 가능 | XCUITest provider를 별도 Phase로 구현한다. |
| native 로그인 profile | Emulator `preserve` 상태에 의존 | encrypted profile 또는 deterministic seed login을 설계한다. |
| 실제 기기 | Android Emulator만 지원 | device farm과 physical device는 별도 provider로 분리한다. |
| 디자인 검증 | Figma 참조는 입력할 수 있지만 플랫폼별 component mapping이 없음 | web·Android·iOS frame과 scenario의 source reference 규칙을 정한다. |
| result sink | local file만 기본값으로 확정 | GitHub·Linear·Notion adapter는 core 안정화 후 추가한다. |

한계로 남기는 것도 정당하다. 특히 iOS와 physical device는 지원하지 않으면서 지원한다고 표시하는 것보다 `unsupported`로 명확히 종료해야 한다.

## 9. 환경 복구와 시작 명령

### 범용 스킬 구현 시작

```bash
cd /Users/igeun-won/skills
git status --short --branch
git pull --ff-only
git switch -c feat/spec-driven-qa

python3 /Users/igeun-won/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  spec-driven-qa \
  --path /Users/igeun-won/skills/prd-flow \
  --resources scripts,references \
  --interface display_name="Spec-driven QA" \
  --interface short_description="PRD·정책·디자인 기반 웹·Android 네이티브 앱 QA" \
  --interface default_prompt="PRD, 인수조건, 정책, 디자인을 기준으로 실제 웹 또는 네이티브 앱을 검증해줘."

# SKILL.md의 TODO와 frontmatter description을 실제 내용으로 교체한 뒤 실행한다.
python3 /Users/igeun-won/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/igeun-won/skills/prd-flow/spec-driven-qa
```

이 핸드오프와 `status.md`는 현재 untracked 상태다. 브랜치를 만들면 두 파일이 그대로 새 브랜치에 따라간다.

### Android 참조 구현 확인

```bash
cd /Users/igeun-won/Documents/video
git status --short --branch
git log -1 --oneline

PYTHONPATH=src python3 -m unittest \
  tests.test_native_models \
  tests.test_native_service \
  tests.test_native_runtime \
  tests.test_native_recording_integration \
  -v
```

현재 참조 저장소 상태:

- 브랜치: `codex/publish-demo-video-mcp`
- 커밋: `4cd45e3 Update project status`
- 사용자 변경: `native_runtime.py`, `tests/test_native_runtime.py`, `status.md`와 영상 산출물·시나리오 문서
- 검증: native model·service·runtime 테스트 17건 통과, 가짜 Appium 녹화 통합 테스트 1건 실패

Android 실제 실행 host에는 `adb`, Android Emulator·AVD, Node.js, Appium, UiAutomator2 driver, FFmpeg가 필요하다. MCP package가 이 의존성을 자동 설치하지 않는다.

### 회사 adapter 확인

```bash
cd /Users/igeun-won/prd-flow-copilot
git status --short --branch
go test ./internal/qa ./internal/mcpserver ./internal/tickets -count=1
```

회사 adapter는 범용 `spec-bundle-v1`과 `result-v1`이 확정되기 전에는 수정하지 않는다.
