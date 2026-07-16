# prd-builder-discovery

PRD-Flow 파이프라인의 진입점. "prd-flow 시작해줘" 또는 "PRD 빠르게 만들어줘"로 트리거.

---

## 사전 조건: prd-flow 폴더 위치

이 스킬은 피처별 작업 디렉토리를 `./prd-flow/{feature-slug}/` 경로에 생성한다.  
`./`는 **Claude Code를 실행하는 디렉토리** 기준이다.

### 권장 설정

```
~/                          ← 여기서 Claude Code 실행
└── prd-flow/
    ├── habit-tracker-reminders/
    ├── commerce-refund-flow/
    └── ...
```

`~/`(홈 디렉토리)에서 Claude Code를 실행하면 `~/prd-flow/`가 자동으로 SoT 디렉토리가 된다.

### 주의

- 다른 프로젝트 폴더(`~/my-project/`)에서 실행하면 `~/my-project/prd-flow/`를 새로 만들고, 기존 `~/prd-flow/` 데이터는 접근하지 않는다.
- 기존 작업을 이어서 하려면 반드시 `~/`에서 Claude Code를 실행하거나, 세션 시작 시 작업 디렉토리 절대 경로를 명시한다.

### 기존 작업 재개 시 진입 방법

```
~/prd-flow/habit-tracker-reminders/ 작업 이어서 진행해줘
```

작업 디렉토리 경로를 명시하면 어느 디렉토리에서 실행하든 동일하게 동작한다.

---

## 전체 워크플로우

리포 루트의 `README.md` 참고. Gate 2 통과(Full PRD 완성) 후에는 `/ai-dlc`로 설계·코드 생성 단계로 이어진다.
