# 프로토타입 배포 + desc 편집 인프라

`desc 직접 편집`([desc-editing.md](desc-editing.md))이 동작하려면 프로토타입이 **GitHub에 있고 Vercel로 자동 배포**되어야 한다. 이 문서는 새 프로토타입에 그 인프라를 붙이는 절차다.

## 구성 개요

> 아래에서 `{owner}/{repo}`는 프로토타입 모음용 GitHub 저장소(사용자 소유, private 권장, monorepo)를 뜻한다. 실제 값으로 치환해 사용한다.

```
GitHub: {owner}/{repo} (private, monorepo)
  └─ {project}/wireframe/         ← 프로토타입 소스
        └─ api/save-desc.js        ← desc 커밋 함수
  └─ .github/workflows/deploy-{project}.yml   ← 자동 배포

Vercel: {project} 프로젝트 (Root Directory 미설정 — Actions가 working-directory에서 빌드)
  └─ 환경변수 GITHUB_TOKEN          ← desc 커밋용 PAT

편집 흐름: 브라우저 편집 → /api/save-desc → GitHub 커밋 → Actions → Vercel 재배포
```

## 한 번만 (전체 공유)

- **GitHub repo**: `{owner}/{repo}` 하나에 모든 프로토타입을 하위 디렉토리로.
- **fine-grained PAT** (`GITHUB_TOKEN`): owner `{owner}`, repo `{repo}`, **Contents: Read and write**. **모든 프로토타입이 재사용**(같은 repo). 재발급 불필요.
  - 발급: github.com/settings/personal-access-tokens/new
  - 만료일을 길게(90일+) — 만료되면 편집 저장이 막힌다.
- **GitHub Actions Secret** (repo 레벨, 공유): `VERCEL_TOKEN`, `VERCEL_ORG_ID`
  - `gh secret set VERCEL_TOKEN --repo {owner}/{repo} --body "$TOKEN"`
  - Vercel 토큰: `~/Library/Application Support/com.vercel.cli/auth.json`의 `token` (macOS 기준)

## 프로토타입마다 (1회)

### 1. 소스를 repo에
`{owner}/{repo}`에 클론/커밋되어 있어야 한다. 외부에서 만든 프로토타입이면 전체를 `{project}/` 하위로 커밋한다.

### 2. Vercel 프로젝트 생성 (⚠️ Root Directory 설정 금지)
```bash
# wireframe 디렉토리에서 프로젝트 링크, 또는 대시보드에서 New Project
cd {project}/wireframe
npx vercel link --yes --token=$TOKEN
```
**Root Directory는 설정하지 않는다.** monorepo라 `{project}/wireframe`로 지정하고 싶어지지만, 설정하면 (1) 빌드 캐시가 구버전을 재사용하고 (2) 로컬 배포 시 경로가 중복되며 (3) production alias가 자동 갱신되지 않는다(함정 표 참조). 대신 Actions가 `working-directory`에서 직접 빌드한다. 확보한 projectId를 워크플로우 `VERCEL_PROJECT_ID`에 넣는다.

### 3. GITHUB_TOKEN 환경변수 (Vercel)
Vercel 대시보드 → 프로젝트 → Settings → Environment Variables → `GITHUB_TOKEN` = (공유 PAT), Production.
- 값은 **위에서 한 번 발급한 PAT 재사용**.

> **챗봇 환경변수는 별개다.** 챗봇을 켰다면 `CHAT_API_BASE_URL`·`CHAT_API_KEY`도 같은 화면에서 추가한다([chatbot-architecture.md](chatbot-architecture.md) §5).
> 🔴 단, **자체 호스팅 LLM 서버가 사설 IP에 있으면 Vercel 배포본에서 도달하지 못한다** — Vercel 런타임에서 사설망으로 라우팅되지 않는다. Vercel로 배포할 프로토타입의 챗봇은 상용 API 프로바이더(`https://api.openai.com/v1`)로 두거나, 자체 호스팅 LLM을 쓸 경우 `npm run dev`(Vite dev proxy) 또는 내부망 호스팅으로 실행한다. 판단 기준은 chatbot-architecture.md §0의 표.

### 4. Actions 워크플로우
`.github/workflows/deploy-{project}.yml` 생성. **`VERCEL_PROJECT_ID`는 Secret이 아니라 직접 명시**(프로토타입별 다름, ID 자체는 민감정보 아님). `VERCEL_TOKEN`·`VERCEL_ORG_ID`만 공유 Secret.

```yaml
name: Deploy · {project} wireframe
on:
  push:
    branches: [main]
    paths:
      - '{project}/wireframe/**'
      - '.github/workflows/deploy-{project}.yml'
  workflow_dispatch:

# 동시 실행 방지 — 배포가 겹치면 alias가 역전될 수 있다
concurrency:
  group: deploy-{project}
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: {project}/wireframe   # Root Directory 미설정 → 여기서 직접 빌드
    env:
      VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
      VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
      VERCEL_PROJECT_ID: prj_xxxxx          # ← 직접 명시 필수 (.vercel은 gitignore라 미추적)
      VERCEL_FORCE_NO_BUILD_CACHE: '1'      # 빌드 캐시 무력화 (deploy 단계엔 안 먹으므로 --force도 병행)
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm install -g vercel@latest
      - run: vercel pull --yes --environment=production --token=$VERCEL_TOKEN
      # prebuilt(vercel build) 금지 — 함수에 런타임 env(GITHUB_TOKEN)를 못 주입해 편집 API가 깨진다.
      # deploy --prod(Vercel 빌드)는 env 자동 주입. 단 빌드 캐시가 구버전을 재사용하므로 --force 필수.
      # production alias 자동 갱신이 불안정하므로 deploy URL을 추출해 명시적으로 연결한다.
      - name: Deploy + alias
        run: |
          URL=$(vercel deploy --prod --force --token=$VERCEL_TOKEN | grep -o 'https://[a-z0-9-]*\.vercel\.app' | tail -1)
          vercel alias set "$URL" {production-domain} --token=$VERCEL_TOKEN
```

`working-directory`에서 pull/deploy가 실행되므로 Root Directory 설정이 불필요하다. **`vercel build` + `--prebuilt`는 쓰지 않는다**(아래 함정 참조).

### 5. 첫 배포
새 워크플로우는 **그것을 추가하는 push에서는 paths 필터로 트리거되지 않는다**(GitHub 동작). 수동 실행:
```bash
gh workflow run "deploy-{project}.yml" --repo {owner}/{repo}
```

### 6. 검증
```bash
# 함수 인식 확인 — 토큰 적용 전이면 500, 후면 404(존재하지 않는 num)
curl -s -X POST https://{project-domain}/api/save-desc \
  -H 'Content-Type: application/json' -d '{"scope":"screen","num":"__diag__","body":"x"}'
```

---

## 함정 (실제로 겪은 것)

| 함정 | 원인 | 해결 |
|------|------|------|
| **🔴 워크플로우가 엉뚱한 Vercel 프로젝트로 배포 (최우선 의심)** | monorepo 다중 프로젝트에서 `secrets.VERCEL_PROJECT_ID` 같은 **공용 secret이 한 프로젝트 ID만 담고 있어**, 다른 프로토타입 워크플로우도 그 값을 읽으면 남의 프로젝트로 배포됨 → 내 도메인은 안 갱신되고 남의 URL이 덮어써진다. "구버전 배포·alias 미갱신"으로 보이는 증상의 실제 주범인 경우가 많다 | **프로토타입별 워크플로우에 PROJECT_ID를 직접 하드코드.** 공용 secret 금지. 배포 후 실제 어느 프로젝트/URL에 갔는지 반드시 확인. |
| **🔴 Root Directory 설정이 로컬 배포를 망가뜨림** | monorepo라 Root Directory를 `{project}/wireframe`로 설정하면 로컬 `vercel deploy` 시 경로 중복 에러 | **Root Directory를 설정하지 않고** `working-directory`에서 빌드. |
| **⚠️ (미확정) deploy 구버전 배포 / alias 미갱신** | 빌드 캐시·alias 자동 갱신 문제로 보였으나, **실제 원인은 위 PROJECT_ID 오배포였을 가능성이 크다**(같은 시점에 함께 수정돼 효과가 구분되지 않음) | 먼저 PROJECT_ID부터 확인. 그래도 재현되면 `deploy --prod --force` + deploy URL 추출 후 명시적 `vercel alias set`(현재 워크플로우에 안전장치로 포함). |
| **org private repo git 연동 실패** | Vercel Hobby plan은 org 소유 private repo의 git 자동 연동 미지원 (Pro 필요) | git 연동 대신 **GitHub Actions가 Vercel CLI로 배포**(이 문서 방식). plan 무관, 무료. |
| **🔴 편집 API가 GITHUB_TOKEN 500 (배포는 됐는데)** | `vercel build` + `deploy --prebuilt` 방식은 런타임 환경변수(GITHUB_TOKEN)를 서버리스 함수에 주입하지 못함. 프로젝트에 env가 있어도 함수에서 못 읽음 | **`vercel deploy --prod`(Vercel 빌드) 사용.** prebuilt 금지. Vercel 빌드는 런타임 env를 자동 주입한다. |
| **환경변수 추가했는데 반영 안 됨** | 대시보드 Redeploy는 prebuilt 배포의 env를 갱신 못 함 | Actions 재실행(`vercel pull`이 최신 env 반영). deploy --prod 방식이면 매 배포가 자동 반영. |
| **첫 워크플로우가 push로 안 돌음** | 새 워크플로우는 등록 전이라 그 push 이벤트를 평가 못 함 | `gh workflow run`으로 수동 트리거(`workflow_dispatch`). |
| **push 거부 (fetch first)** | Vercel GitHub App이 `routes.json`을 자동 커밋(Figma Sync 매핑) → remote 선행 | `git fetch && git rebase origin/main` 후 push. |
| **Node 20 deprecation 경고** | actions/checkout·setup-node가 Node 20 타겟 | 무해(자동 24 실행). 거슬리면 액션 버전 상향. |

## 배포 방식 비교

| | GitHub Actions (이 문서) | Vercel git 연동 |
|---|---|---|
| Hobby plan org private | ✅ | ❌ (Pro 필요) |
| 환경변수 갱신 | Actions 재실행 | 자동 |
| PR preview | 추가 설정 | 기본 제공 |

Pro 플랜이면 git 연동이 더 매끄럽다. 무료로 org private repo를 쓰려면 Actions 방식이 정답.
