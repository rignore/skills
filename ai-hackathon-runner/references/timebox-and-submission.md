# 해커톤 Timebox와 제출 안전장치

## 비율 기반 운영

| 구간 | 권장 비율 | 종료 조건 |
|---|---:|---|
| Competition + Context | 15% | 규칙과 트랙별 Context Pack |
| Problem discovery + Human Gate | 15% | Problem Lock |
| Scaffold + first slice | 10% | Build Contract와 task map |
| Core build | 30% | P0 end-to-end 동작 |
| Verification + field evidence | 15% | 실행 증거와 한계 |
| Taste + Mock Judge | 7% | top gaps 교정 |
| Submission + buffer | 8% | receipt와 handoff |

대회 길이에 맞게 환산하되 마지막 30%를 검증·심사·제출에 보존한다. 밤샘/다일 대회는 각 작업 블록 종료 시 같은 비율로 checkpoint를 둔다.

## Hard cut-off

- **T+30%**: Problem Lock. 이후 문제 교체는 치명적 근거 또는 실현 불가능성이 확인될 때만 한다.
- **T+40%**: P0/API/schema lock. 병렬 구현 contract를 바꾸려면 영향 범위를 먼저 확인한다.
- **T+70%**: Feature Freeze. P1 중단, field evidence와 engineering verification으로 전환한다.
- **T+85%**: Submission Freeze. rubric gap, blocker, 실격 위험만 수정한다.
- **T+92%**: Code Freeze. demo rehearsal, 링크·권한·업로드·receipt만 처리한다.

늦게 시작했으면 경과 시간이 아니라 남은 시간에서 역산한다. 제출 buffer를 구현 시간으로 쓰지 않는다.

## Rescue 순서

1. 다른 트랙/후보 탐색 종료
2. P1과 cosmetic polish 제거
3. P0에서 핵심 가설과 무관한 edge path 제거
4. 불안정한 외부 연동을 replay/sample data fallback으로 전환하고 명확히 고지
5. 가장 짧은 재현 가능한 demo path 고정
6. 검증·제출 buffer 유지

금지: framework 교체, 검증 삭제, mock을 real result로 표현, 제출 직전 대규모 refactor.

## 실격·제출 체크리스트

### Eligibility

- 팀 규모, 참가자 자격, 중복 참가, 트랙 선택 조건
- 사전 제작물·기존 IP·오픈소스 사용 허용 범위
- 필수 현장 참여, 발표, 체크인 조건

### Artifact

- repository/deploy URL 접근 권한과 심사 계정
- 파일 형식, 크기, 길이, 언어, naming
- demo video 재생·음성·자막·공개 범위
- README 실행법, 환경 변수 예시, sample data
- 필수 form 필드, 팀원·기업·트랙 정보

### Compliance

- dependency·asset·dataset license와 출처
- AI 사용 고지 의무
- 개인정보·기업 기밀·민감 데이터 제거
- 외부 API terms, quota, 비용, 지역 제한
- 의료·안전·금융 등 고위험 주장에 한계 표시

### Reliability

- clean environment 실행 확인
- production build/test 재실행
- 핵심 demo 2회 연속 rehearsal
- 네트워크/API 장애 fallback
- backup 영상·스크린샷·local sample

### Receipt

- deadline과 timezone 재확인
- 제출 후 수정 가능 여부 확인
- 성공 화면, confirmation email, submission ID 보존
- 제출된 URL/파일 버전 기록

하나라도 `UNKNOWN`이면 owner와 해결 시각을 지정한다. 실격 가능 항목은 기능보다 우선한다.
