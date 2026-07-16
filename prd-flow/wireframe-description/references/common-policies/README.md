# 공통 정책 인덱스

시스템 전체에 적용되는 공통 정책 문서 목록.
디스크립션 작성 전에 이 인덱스를 읽고, 해당 화면에 적용되는 정책을 확인한다.

---

## 정책 목록 및 적용 빈도

| 파일 | 정책명 | 적용 빈도 | 주요 적용 화면 |
|------|------|---------|-------------|
| [data-table-policy.md](data-table-policy.md) | 데이터 테이블 키워드 검색 / 정렬 기준 정책 | 높음 | 테이블·리스트가 있는 모든 화면 |
| [text-input-policy.md](text-input-policy.md) | 텍스트 입력폼 유효성 검증 정책 | 매우 높음 | 폼 입력이 있는 모든 화면 |
| [chart-axis-policy.md](chart-axis-policy.md) | 라인/바 차트 Y축·X축 정책 | 매우 높음 | 차트 화면 전체 |
| [number-display-policy.md](number-display-policy.md) | 숫자 표기 정책 (지수/천단위/소수점) | 매우 높음 | 숫자 데이터가 표시되는 모든 화면 |
| [tooltip-policy.md](tooltip-policy.md) | 툴팁 인터랙션 정책 (A/B/C 3타입) | 높음 | 툴팁이 있는 화면 |
| [selectbox-policy.md](selectbox-policy.md) | 셀렉박스 선택 영역·전체 항목 정책 | 높음 | 셀렉박스가 있는 화면 |
| [notice-popup-policy.md](notice-popup-policy.md) | 안내 팝업 정책 (배경 클릭 비차단) | 높음 | 확인 팝업·요청 대기 팝업 |
| [snackbar-policy.md](snackbar-policy.md) | 스낵바 정책 (오류 10초 / 완료 3초) | 높음 | 오류 및 완료 피드백 전체 |
| [data-preprocessing-policy.md](data-preprocessing-policy.md) | 평균값·표준편차·변화율 계산 (IQR, 백분위) | 중간 | 통계·차트 화면 |
| [system-common-policy.md](system-common-policy.md) | 시스템 공통 정책 (테이블 검색·정렬 + 입력폼 검증 통합본) | 중간 | 전체 화면 |
| [text-button-hover-policy.md](text-button-hover-policy.md) | 텍스트 버튼 마우스 오버 인터랙션 | 낮음 | 텍스트 버튼이 있는 화면 |

---

## 디스크립션에서의 참조 방법

정책과 **정확히 일치**하면 정책명으로 참조:
```markdown
유효성 검증: 텍스트 입력폼 유효성 검증 정책 A 적용
```

정책과 **차이가 있으면** 참조 + 차이점 명시:
```markdown
정렬: 데이터 정렬 기준 정책 A 적용. 단, 이 화면에서는 최근 접속일 기준 내림차순을 우선 적용.
```

공통 정책에 **해당하지 않는** 화면 고유 정책은 직접 기술.

---

## 정책 SoT(Source of Truth)

**이 디렉토리의 파일들이 SoT다.** 정책 변경 시 이 파일들을 직접 수정하고, 정책을 참조하는 디스크립션은 정책명 참조를 유지하므로 별도 수정이 필요 없다.
프로젝트 고유 정책이 생기면 같은 형식으로 이 디렉토리에 파일을 추가하고 위 인덱스에 등록한다.
