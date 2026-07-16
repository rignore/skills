# skills

Claude Code 스킬(`SKILL.md`) 모음. 특정 회사·제품에 결합되지 않고 어떤 프로젝트에서든 동작하도록 일반화한 범용 스킬 세트다.

| 그룹 | 무엇을 하나 | 진입점 |
|---|---|---|
| [`prd-flow/`](prd-flow/) | 아이디어 → PRD → 와이어프레임 → 화면 설계서까지 잇는 제품 개발 파이프라인 | "prd-flow 시작" / "PRD 자동 진행" |
| [`ai-dlc/`](ai-dlc/) | PRD + 화면 사양을 자동 인테이크해 유저스토리 → 설계 → 코드 생성·빌드·테스트 (AWS AI-DLC 방법론) | `/ai-dlc` |
| [`loop-harness/`](loop-harness/) | 정답표 + 기계 판정이 있는 수치 지표를 라운드 단위로 반복 개선하는 하네스 | "loop 하네스" / "검증 루프" |

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
