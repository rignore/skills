# 리서치 근거 — UX 리서처 에이전트 설계 (2026-07-15 딥리서치)

이 파일은 정책(evidence-protocol·heuristics·severity-rubric)의 근거다. 정책이 왜 이렇게
설계됐는지는 여기 인용 수치를 따른다. 딥리서치 하네스(5각도 검색·23소스·110클레임 →
25검증 → 22확증·3기각)의 확증 findings만 옮긴다.

## 근거 1 — LLM UX 평가기는 단독 판정자로 부적합하다 (설계의 핵심 전제)

- GPT-4의 UI 휴리스틱 평가 precision 0.603 (인간 전문가 0.829). **플래그의 약 40%가
  false positive.** (100-violation ground truth, Nielsen 10 heuristics)
  - 출처: arxiv.org/html/2403.13139 (CHI 2024)
- GPT-4o는 3인 HCI 전문가가 찾은 66개 이슈 중 **21.2%(14개)만 재현**, 27개는 어느
  전문가도 못 찾은 배타 이슈(환각 다수 포함). 원저 결론: "GPT-4o should not be treated
  as a replacement for human experts."
  - 출처: arxiv.org/html/2506.16345v1 (INTERACT 2025)
- 51개 UI 등급 연구에서 GPT-4 제안의 52%만 'Accurate', 49%만 'helpful' 이상.

**설계 반영**: 에이전트는 **판정자가 아니라 pre-screener**다. 발견을 내되 확정은
독립 적대 게이트(evaluator)와 사람이 한다. 생성자와 판정자를 분리하는 검증 루프
(judge≠solver)와 동형이다.

## 근거 2 — 억제할 실패 모드는 3종으로 정형화된다 (evidence-protocol의 표적)

GPT-4o false positive 24.3%(27/111)의 분해:

1. **환각(problem disagreement, 15건)**: 스크린샷에 실존하지 않는 문제.
2. **정적 판별 불가(problem assumption, 9건)**: 정적 이미지로 판별 불가한 동적 인터랙션.
   예: "hover 시 피드백 없음" — 실제로 주행해봐야 안다.
3. **일반론(generalized, 3건)**: 구체성 없는 filler. 예: "high cognitive load".

추가로 **over-application**(의도된 디자인 컨벤션을 오탐)이 사용자 스터디에서 **12/12
참가자 전원이 지적한 최다 실패 모드**. 예(P7): 선택 상태를 나타내는 의도적 탭 두께 차이를
"비일관성"으로 오탐. 프롬프트 문구 변형이 검출 결과를 바꾸는 prompt-sensitivity도 보고됨.

- 출처: arxiv.org/html/2506.16345v1, arxiv.org/html/2403.13139,
  arxiv.org/pdf/2604.25420, doi.org/10.3390/electronics13234633

**설계 반영**: evidence-protocol이 이 3종+over-application을 정확한 표적으로 방어한다
(증거 강제, 정적 스크린샷만으로 동적 주장 금지, 구체성 검사, 의도된 컨벤션 확인).

## 근거 3 — 증거 그라운딩 + heuristic 개별 평가가 filler를 실사용 품질로 끌어올린다

- 스크린 레코딩+인터랙션 로그로 그라운딩한 MLLM 권고안 285건을 95명 SW 엔지니어가 리뷰:
  **73.7% 'complete'**, 22.8% 'partially complete', 3.5%만 'incomplete'. clarity 4.21~4.28,
  plausibility 4.04~4.10 (5점 Likert).
- 단, 이슈 존재 검출의 inter-run 신뢰도 Cohen's κ 0.50 (moderate). **단일 run 재현성이
  완전하지 않아 병렬 실행·병합·사람 검증이 필요하다.**
- 출처: arxiv.org/pdf/2604.25420 (FSE 2026), arxiv.org/html/2512.04262v1 (VL/HCC 2025)

**설계 반영**: SKILL.md가 화면 캡처+유저플로우 주행으로 그라운딩하고, heuristic을 1개씩
개별 평가하며, 차원별 finder를 병렬로 돌려 병합한다.

## 근거 4 — 판정 프레임워크 (heuristics.md 근거)

- **Cognitive Walkthrough**: 태스크 각 스텝마다 4문항 고정 게이트 —
  (1) 올바른 결과를 시도하는가 (2) 올바른 액션이 있음을 알아채는가 (3) 액션과 결과를
  연결하는가 (4) 액션 후 진행 피드백을 보는가. learnability 발견에 강함. persona당 1회 주행.
  - 출처: nngroup.com/articles/cognitive-walkthroughs/
- **Interaction Cost**: 목표 도달까지의 정신적·물리적 노력 총합 = usability의 직접 척도.
  9종 계량 단위 — reading, scrolling, looking around, comprehending, clicking/touching,
  typing, page loads/waiting, attention switches, memory load.
  - 출처: nngroup.com/articles/interaction-cost-definition/
- **JTBD Universal Job Map**(Ulwick, HBR 2008): 8단계 solution-agnostic —
  define, locate, prepare, confirm, execute, monitor, modify, conclude. job map은
  "needs view"(무엇을 해내려는가)이지 "solution view"(무엇을 하고 있는가)가 아니다.
  - 출처: jobs-to-be-done.com/mapping-the-job-to-be-done-45336427b3bc
- **context divergence**: evaluator가 실사용자와 다른 맥락을 방문해 false alarm 발생.
  맥락(persona·job) 그라운딩이 over-application을 직접 상쇄.
  - 출처: arxiv.org/pdf/1204.2138

## 근거 5 — Severity는 relative ranking으로 강제한다 (severity-rubric.md 근거)

- Nielsen severity = frequency(빈발/희소) + impact(극복 난이도) + persistence(1회성인가
  반복적으로 괴롭히는가) 3요소 결합. 0-4 척도(0=문제 아님, 1=cosmetic, 2=minor, 3=major,
  4=catastrophe).
  - 출처: nngroup.com/articles/how-to-rate-the-severity-of-usability-problems/
- **LLM에 명시적 절대 척도(3점·5점)를 요구하면 동일 등급이 다발해 strict order가 붕괴**.
  relative ordering으로 전환해야 함. relative 기준: impact on task success·user
  frustration·likelihood of occurrence·effort for recovery.
  - 출처: arxiv.org/pdf/2604.25420 (FSE 2026 실험)

## 근거 6 — 증거 기반 리뷰 프로토콜 (evidence-protocol.md 근거)

- 모든 finding을 관찰된 태스크 주행 + 명시적 persona에 고정한다.
- Nielsen heuristic을 1개씩 개별 평가한다(더 다양·상세한 이슈 산출).
- heuristic 간 중복 이슈는 임베딩 cosine similarity 0.7 임계로 병합한 뒤 severity를 매긴다.
- 입력은 스크린 레코딩+인터랙션 로그 결합이 시각-only보다 precision/recall/F1 우위.
  - 출처: arxiv.org/pdf/2604.25420, doi.org/10.3390/electronics13234633

## 한계·경고 (반드시 인지)

1. **근거 공백**: 주의력 관리·오케스트레이션 대시보드 UX 패턴과 local-first 알림·집중 보호
   패턴은 이 리서치 배치에서 확증 근거 0건이었다. **이 두 영역은 학술 근거로 게이트에 못
   박지 않는다.** 대신 대상의 불변 설계 원칙과 persona 실측을 도메인 기준으로 쓴다.
2. **외삽 리스크**: 확증 근거 대부분이 mobile/web UI·정적 스크린샷·짧은 태스크를 다룬 학술
   연구다. 데스크탑 앱·파워유저 도구·장기 반복 사용 맥락으로 옮길 때 수치가 그대로 성립하는지는
   보장되지 않는다. 대상 도메인에서 자체 holdout으로 재검증해야 한다.
3. **precision 임계의 시간 민감성**: 문헌 baseline 0.60은 참고치일 뿐. 게이트 임계값은
   대상 도메인에서 재측정해 고정한다.
4. **기각된 주장(서술 금지)**: "LLM이 인간 평가보다 정확하다"(0-3 기각), "모든 usability
   heuristic은 interaction cost로 환원된다"(0-3 기각). 정책에 이 두 서술을 넣지 않는다.
