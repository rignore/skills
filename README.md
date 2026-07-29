# skills

Claude Code 스킬(`SKILL.md`) 모음. 특정 회사·제품에 결합되지 않고 어떤 프로젝트에서든 동작하도록 일반화한 범용 스킬 세트다.

| 그룹 | 무엇을 하나 | 진입점 |
|---|---|---|
| [`prd-flow/`](prd-flow/) | 아이디어 → PRD → 와이어프레임 → 화면 설계서까지 잇는 제품 개발 파이프라인 | "prd-flow 시작" / "PRD 자동 진행" |
| [`ai-dlc/`](ai-dlc/) | PRD + 화면 사양을 자동 인테이크해 유저스토리 → 설계 → 코드 생성·빌드·테스트 (AWS AI-DLC 방법론) | `/ai-dlc` |
| [`loop-harness/`](loop-harness/) | 정답표 + 기계 판정이 있는 수치 지표를 라운드 단위로 반복 개선하는 하네스 | "loop 하네스" / "검증 루프" |
| [`ux-researcher/`](ux-researcher/) | 렌더된 화면·유저플로우를 관찰해 UX 개선점을 찾되, 발견과 판정을 분리해 LLM 오탐을 억제하는 리뷰 하네스 | "UX 검토" / "유저플로우 봐줘" |
| [`bizplan-builder/`](bizplan-builder/) | B2B SaaS·AI 에이전트·IIoT 신사업 사업계획서를 4개 Phase로 나누어 VC·컨설팅 펌 수준의 전문가 페르소나와 정량 가드레일로 검증하며 작성 | "사업계획서 작성" / "BP 만들어" |
| [`rnd-proposal-reviewer/`](rnd-proposal-reviewer/) | 정부 R&D 지원사업 제안서를 7인 전문가 페르소나로 검토해 고득점·Auto-fail 방지를 돕는 4단계 Fail-Safe 워크플로우 | "R&D 사업계획서 검토" / "IRIS 제안서" |
| [`editorial-reviewer/`](editorial-reviewer/) | 문서의 가독성·용어 일관성·논리 흐름·인용 사실을 검토(전략·기능 타당성이 아닌 "잘 쓰여졌는가") | "가독성 검토" / "문서 리뷰" |
| [`korean-professional-editor/`](korean-professional-editor/) | IR·제품·브랜드 소개 문구의 AI·번역투를 걷어내고 한국 비즈니스 문체에 맞는 최종 문장으로 재작성 | "AI 티 빼줘" / 자연스럽게 작성해줘" |
| [`meeting-minutes-writer/`](meeting-minutes-writer/) | STT 변환 텍스트에서 STT 오변환을 맥락으로 보정해 회의록을 작성 | "회의록 작성" / "STT 파일로 회의록" |
| [`paper-easy-reader/`](paper-easy-reader/) | 영어 학술 논문을 전문 용어는 보존하고 문장 구조만 쉬운 한국어로 변환 | "논문 번역해줘" / "쉽게 읽히게" |
| [`handoff-writer/`](handoff-writer/) | 진행 중인 작업을 다른 세션이 이어받도록 핸드오프 문서로 정리 | "핸드오프 문서 작성" / "세션 넘길 수 있게" |
| [`skill-improver/`](skill-improver/) | 세션 대화를 분석해 어떤 스킬이 쓰였는지 파악하고 트리거·품질 개선안을 제시 | "스킬 개선" / "이번 세션 스킬 어땠어" |
| [`codex-delegate/`](codex-delegate/) | 설계는 Claude가, 실행은 Codex CLI가 맡고 이중 교차검증을 거치는 로컬 위임 파이프라인 | "codex로 실행" / "코덱스한테 위임" |

## prd-flow — 아이디어에서 코드까지

```
아이디어
  │
  ▼
prd-builder-discovery ──── 거시 게이트(문제·페르소나 → 솔루션 범위 → 최종 리포트)로 PRD 완성
  │        │
  │        ├─ domain-research ─────── 도메인 지식을 웹 검색으로 조사해 리서치 캐시 구축
  │        └─ prd-builder-auto ────── 게이트 사이 자동 Phase(발산·상세화) + 페르소나 리뷰 + Hard-Stop
  ▼
prd-to-wireframe ────────── PRD → React JSX 와이어프레임
  │        │
  │        └─ design-system-builder ─ 페르소나·요구사항 기반 레퍼런스를 웹 리서치해
  │                                   프로젝트 전용 디자인 시스템 생성
  ▼
wireframe-description ───── 와이어프레임이 못 보여주는 정책·로직을 화면 설계서로 문서화
  │        └─ inspection-mode ─────── 프로토타입에 설계서 툴팁·검수 도구 주입
  ▼
ai-dlc ──────────────────── PRD + 화면 사양을 자동 인테이크 → 유저스토리 → 설계 → 유닛 분할
                            → 실제 코드 생성 → 빌드·테스트
```

횡단 스킬: `prd-sync`(산출물 간 앵커 동기화), `notion-organizer`(선택적 Notion 업로드), `general-ux-writing`(UX 문구 규칙), `shared/`(공용 페르소나 11종·가드레일·템플릿).

설계 원칙·작업 디렉토리 구조·개별 스킬 설치는 [`prd-flow/README.md`](prd-flow/README.md) 참조.

## loop-harness — 반복 개선 사이클

측정 가능한 지표 + 수정 가능한 해법이 있는 모든 시스템(LLM 프롬프트, 시뮬레이터 물리 모델, 검색 품질, 성능 튜닝 등)에 적용하는 반복 개선 방법론. Planner(계획)·Solver(해법)·Evaluator(판정) 3역할을 분리하고, 라운드마다 기계 집계로만 판정한다. 편향 통제(판정 모델을 생성 모델과 다른 계열로 고정), 통계 설계(동일 조건 N회 반복), 정체 시 학술 리서치 선행을 규약으로 둔다.

## 설치

리포를 클론한 뒤 필요한 스킬 디렉토리를 Claude Code 스킬 경로(`~/.claude/skills/`)에 심볼릭 링크로 연결한다. prd-flow 스킬은 [`prd-flow/README.md`](prd-flow/README.md)의 설치 섹션을, loop-harness는 아래를 참조한다:

```bash
git clone https://github.com/rignore/skills.git
ln -s "$(pwd)/skills/loop-harness" ~/.claude/skills/loop-harness
```

`prd-flow/shared/`는 스킬이 아니라 공용 자산(페르소나·가드레일·템플릿)으로, 다른 스킬들이 상대 경로로 참조한다.

## 요구 도구

- WebSearch (도메인 리서치·디자인 레퍼런스 조사)
- Notion MCP (선택 — prd-flow의 `notion_upload` 사용 시에만)
