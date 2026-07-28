# References

`korean-professional-editor`가 한국 채용·비즈니스 문서를 진단하고 재작성할 때 사용하는 기준 자료다.

| 파일 | 사용 시점 | 역할 |
|---|---|---|
| [`source-map.md`](./source-map.md) | 항상 | 국립국어원·원티드·토스·국내 포트폴리오·IR·한국어 LLM 연구의 출처와 적용 범위 |
| [`korean-naturalness-patterns.md`](./korean-naturalness-patterns.md) | 항상 | 번역투, 추상 동사, 명사화, 기계적 병렬, 문서 유형별 AI 문형 진단 |
| [`document-type-playbook.md`](./document-type-playbook.md) | 항상 | 이력서·경력기술서·포트폴리오·IR·회사·제품·브랜드별 구조와 문체 |
| [`voice-calibration.md`](./voice-calibration.md) | 작성자 샘플이나 브랜드 톤이 있을 때 | 사용자 고유 어휘·격식·단정 강도·문장 리듬 보존 |
| [`rewrite-examples.md`](./rewrite-examples.md) | 복합 편집 또는 교정 기준 확인 | 유형별 합성 원문–교정문과 과잉 교정 예시 |
| [`quality-rubric.md`](./quality-rubric.md) | 최종 검수 | 사실·문서 적합성·한국어 자연스러움·책임·근거·목소리 평가 |
| [`eval-cases.md`](./eval-cases.md) | 스킬 수정 후 유지보수 | 12개 수동 회귀 검사와 실패 조건 |

## 적재 원칙

- 일반 실행에서는 `source-map`, `korean-naturalness-patterns`, `document-type-playbook`, `quality-rubric`을 기준으로 사용한다.
- `voice-calibration`은 사용자가 직접 쓴 샘플이 있을 때만 상세 적용한다.
- `rewrite-examples`는 원문의 문장을 대체하는 템플릿이 아니다. 교정 방향을 판단할 때만 참고한다.
- `eval-cases`는 일반 출력 생성에 사용하지 않고 스킬 품질 검사에만 사용한다.

## 저작권·윤리

- 외부 레퍼런스의 문장·슬로건·디자인을 복제하지 않는다.
- 모든 예시는 합성 자료이며 실제 지원자·기업의 고유 문장을 재사용하지 않는다.
- 한국어 LLM 문체 연구는 진단 기준으로만 사용하며 AI 탐지 우회에는 사용하지 않는다.
