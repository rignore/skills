# 인스펙션 챗봇 아키텍처 (Chat Completions 기반)

설명 모드 프로토타입에 주입하는 컨텍스트 기반 챗봇의 **전체 구현 코드**. SKILL.md Phase 6~9의 설계 결정을 코드로 구현한다.

> 설계 원칙·정책·체크포인트는 SKILL.md Phase 6~9에 있다. 이 문서는 **코드**만 다룬다.

**LLM 프로바이더는 두 가지 중에서 고른다** — 자체 호스팅 LLM 서버(`local`)와 상용 LLM API(`api`). 둘 다 OpenAI Chat Completions 스키마를 쓰므로 **코드는 하나고, base URL·키·모델명만 갈린다**(§0·§1).

## 아키텍처 한눈에

```
사용자 입력
  → 컨텍스트 조립 (전부 주입 + 섹션 앵커 [DOC §ID] + descs/data.json)
  → /api/chat 프록시 (키 서버측 보관, 스트리밍 패스스루)
  → OpenAI 호환 Chat Completions (stream + tools=[propose_edit])
     · local : 자체 호스팅 LLM 서버   ${CHAT_API_BASE_URL}
     · api   : 상용 LLM API           https://api.openai.com/v1
  → tool_call?
      ├─ 없음(질문) → 마크다운 스트리밍 렌더 + citation 칩 → 클릭 시 정책 패널 이동
      └─ 있음(편집) → InlineDiff 카드 → Apply → 기존 saveBody() 재사용 → 재배포
```

핵심 설계 결정 5가지:
1. **프로바이더 교체 가능** — OpenAI 호환 엔드포인트를 제공하는 자체 호스팅 서버(vLLM·Ollama·LM Studio 등)와 상용 API를 같은 코드로 지원한다. 자체 호스팅을 고르면 PRD·정책·desc 전문이 외부로 나가지 않고 호출 비용도 없다. 대신 서버가 있는 네트워크 안에서만 동작한다(§0).
2. **컨텍스트 라우팅 폐기** — regex `intentClassifier` 제거. 컨텍스트 예산 이하 코퍼스는 전부 주입이 라우팅보다 안전(잘못 분기 시 정보 누락이 순손실).
3. **grounding + citation** — "컨텍스트에서만 답·없으면 미정의 응답·섹션 id 인용"을 system prompt와 structured output으로 강제.
4. **텍스트 수정 = saveBody 재사용** — 챗봇은 `propose_edit` 도구로 수정안만 제안. Apply 시 기존 `InspectionContext.saveBody(scope, num, body)`를 호출 → 새 백엔드 불필요. ([desc-editing.md](desc-editing.md) §2·§7)
5. **키 프록시** — 프로바이더와 무관하게 키를 서버측에 둔다. 클라이언트는 `/api/chat`만 호출한다.

---

## 0. 프로바이더·실행 환경 선택 (가장 먼저 결정)

두 축을 함께 정한다. **누가 어디서 이 프로토타입을 여는가**가 프로바이더를 결정한다.

| 프로토타입 실행 위치 | `local`(자체 호스팅) | `api`(상용) | 비고 |
|---|---|---|---|
| **로컬 dev 서버**(`npm run dev`) — LLM 서버와 같은 네트워크 | ✅ Vite dev proxy 경유 | ✅ | 작성자 본인이 보며 검토할 때. 추가 인프라 0 |
| **사내(내부망) 호스팅** — 정적 배포 + 프록시 동봉 | ✅ 내부 프록시 경유 | ✅ | 팀원 여러 명이 링크로 볼 때 |
| **외부 클라우드 배포**(Vercel 등) | ❌ **불가**(사설 IP 미도달) | ✅ | 사외 공유. 프롬프트가 외부 API로 나간다 |

자체 호스팅 서버가 **사설 IP + HTTP**로 떠 있는 경우(대부분의 사내 GPU 서버) 두 가지 제약이 따라온다.

- **브라우저에서 LLM 서버를 직접 호출하지 않는다.** HTTPS로 서빙되는 페이지에서 `http://<사설 IP>`를 부르면 브라우저가 mixed content로 차단하고, 사설망 대상 요청은 Private Network Access 정책에도 걸린다. `local` 경로는 **항상 서버측 프록시 경유**다.
- **외부 클라우드에 배포한 페이지에서는 도달 자체가 불가능하다.** 클라우드 런타임에서 사내 사설 IP로 라우팅되지 않는다. 그 조합이 필요하면 LLM 서버를 공인 도메인 + TLS로 노출하는 인프라 작업이 선행돼야 하고, 이는 내부 LLM을 인터넷에 여는 일이므로 **인프라·보안 담당자 승인 없이 진행하지 않는다.**

> **조직 내부 서버의 실제 주소·모델 목록·운영 절차는 이 문서에 적지 않는다.** `references/local-llm.local.md`에 분리해 두고 스킬 본문은 프로바이더 중립으로 유지한다 — 파일명 접미사 `.local.md`가 git 배포 제외 규약이라 사내·공개 레포 어디로도 동기화되지 않는다. 그 파일이 없으면 자체 호스팅 서버 정보를 사용자에게 확인하거나 `api` 프로바이더로 진행한다.

---

## 1. 모델·환경 설정

```ts
// src/lib/chatConfig.ts

// Phase 0에서 고른 프로바이더를 여기에 고정한다.
//   'local' = 자체 호스팅 LLM 서버(OpenAI 호환) | 'api' = 상용 LLM API
export const CHAT_PROVIDER: 'local' | 'api' = 'api';

// 🔴 모델명 하드코딩 금지 — 이 상수 하나만 갱신한다.
// local : 서버에 실제 적재된 모델명과 정확히 일치해야 한다(불일치 시 §5의 503/404).
// api   : 배포 시점에 공급자 문서에서 최신 모델을 확인하고 교체. 모델 회전 주기가 빠르다.
export const CHAT_MODEL = 'gpt-4o';

export const MAX_OUTPUT_TOKENS = 1024;
export const HISTORY_TURNS = 10;          // 최근 N턴(2N 메시지)만 API에 전달

// 컨텍스트 예산 = 모델 컨텍스트 상한 − 답변 출력분 − 대화 히스토리 여유.
// 자체 호스팅 모델은 상한이 좁은 경우가 많다(예: 상한 65k → 예산 48k).
export const CONTEXT_TOKEN_BUDGET = 75_000;

// 자체 호스팅 서버에 관리 콘솔이 있으면 그 주소. 모델 미적재(503) 안내에서 열어준다.
// 비밀이 아니므로 VITE_ 접두어 허용. 없으면 빈 문자열.
export const CHAT_DASHBOARD_URL = import.meta.env.VITE_CHAT_DASHBOARD_URL ?? '';
```

### 프로바이더별 설정 값

| 항목 | `local`(자체 호스팅) | `api`(상용) |
|---|---|---|
| `CHAT_API_BASE_URL` | 서버의 OpenAI 호환 엔드포인트 (예: `http://<host>:<port>/v1`) | `https://api.openai.com/v1` |
| `CHAT_API_KEY` | 서버에 설정된 API 키 | 공급자 발급 키 |
| `CHAT_MODEL` | 서버에 적재된 모델명 | 공급자 모델 id |
| `CONTEXT_TOKEN_BUDGET` | 모델 상한에 맞춰 축소 | 75k |

### 자체 호스팅 서버를 고를 때 확인할 것

**필수 1건 — tool calling 파싱 활성 여부.** 텍스트 수정 기능(`propose_edit`, §4)은 서버가 도구 호출을 파싱해야 동작한다. vLLM 기준으로 기동 명령에 `--enable-auto-tool-choice`와 모델에 맞는 `--tool-call-parser <이름>`이 함께 붙어 있어야 한다.

- `--enable-auto-tool-choice`는 도구를 서버에 등록하는 옵션이 아니라, 요청의 `tool_choice: "auto"`를 받아들여 **모델이 스스로 도구를 부를지 판단하도록 허용**하는 스위치다. 도구 정의는 클라이언트가 요청마다 `tools` 배열로 보내므로 서버가 사전에 알 필요는 없다.
- `--tool-call-parser`는 모델이 자기 형식으로 뱉은 도구 호출 텍스트를 OpenAI 규격의 `tool_calls` 구조로 번역한다. 파서 이름이 모델과 맞지 않으면 도구 호출이 일반 텍스트로 새어 나온다.
- 꺼져 있으면 **질문·답변은 정상 동작하고 텍스트 수정 제안만 동작하지 않는다.** 그 경우 §4 대신 JSON 응답 파싱으로 우회하거나, 수정 기능을 끄고 질의응답 전용으로 운영한다.

**선택 1건 — prefix caching 활성 여부.** 매 요청마다 같은 컨텍스트를 프롬프트 앞에 붙이는 구조라, 켜져 있으면 두 번째 질문부터 응답이 빨라진다(§11). **기능 조건이 아니라 속도 최적화 항목**이므로 확인하지 못했어도 도입을 진행한다.

**모델 선택 기준**: 컨텍스트 상한이 조립 결과(통상 15~48k)를 담을 수 있어야 한다. 추론 특화 모델(reasoning model)은 사고 과정 텍스트가 응답 앞에 붙어 스트리밍 렌더와 `[§id]` 인용 형식을 흐트러뜨리므로 이 용도에는 쓰지 않는다.

### 키 보관

키는 클라이언트에 두지 않는다. 프록시(§5)가 `process.env.CHAT_API_KEY`로 보관한다.

> `VITE_` 접두어가 붙은 변수는 빌드 시 번들에 **평문 인라인**되어 브라우저에 노출된다(Vite 공식 동작). 비밀이 아닌 값(`VITE_CHAT_DASHBOARD_URL`)만 이 접두어를 쓴다. **API 키에는 절대 `VITE_`를 붙이지 않는다.**

---

## 2. 컨텍스트 레이어 + 섹션 앵커

PRD 컨텍스트를 레이어 파일로 분리 관리하되, **라우팅 없이 전부 조립**한다. 각 섹션을 `[DOC §ID]` 앵커로 래핑해 citation·사람 검증의 기준점으로 삼는다.

| 레이어 | 파일 | 내용 |
|--------|------|------|
| Layer 0 | `base-context.md` | 챗봇 역할·grounding 규칙·답변 형식 |
| Layer 1 | `prd-context.md` | 기능 정의·처리 흐름·주요 정책 |
| Layer 2 | `discovery-context.md` | 배경·페르소나·가치가설·KPI |
| Layer 3 | `policies-context.md` | 공통 정책·도메인 지식 |
| Layer 4 | `changelog.md` | 설계 이력·결정 사유 |
| Layer 5 | `descs/data.json` | **실제 desc·정책 본문** (런타임 직렬화) |

레이어 파일 작성 출처는 SKILL.md Phase 6 표 참조.

```ts
// src/lib/contextAssembler.ts
import baseContext from '../data/base-context.md?raw';
import prdContext from '../data/prd-context.md?raw';
import discoveryContext from '../data/discovery-context.md?raw';
import policiesContext from '../data/policies-context.md?raw';
import changelogContext from '../data/changelog.md?raw';
import descData from '../../descs/data.json';

// data.json의 정책을 섹션 앵커가 달린 텍스트로 직렬화 (Layer 5)
function serializeDescData(): string {
  const screen = (descData.screenPolicies ?? [])
    .map((p: any) => `[DESC §${p.num}] ${p.title ?? ''} (${p.componentId ?? ''})\n${p.body ?? ''}`)
    .join('\n\n');
  const logic = (descData.logicPolicies ?? [])
    .map((p: any) => `[LOGIC §${p.num}] ${p.title ?? ''}\n${p.body ?? ''}`)
    .join('\n\n');
  return `# 현재 프로토타입 desc·로직 정책\n\n${screen}\n\n${logic}`;
}

// 라우팅 없음 — 전부 주입. 각 레이어를 구분자로 결합.
export function assembleContext(): string {
  return [
    baseContext,
    `# PRD\n\n${prdContext}`,
    `# Discovery\n\n${discoveryContext}`,
    `# 공통 정책\n\n${policiesContext}`,
    `# 변경 이력\n\n${changelogContext}`,
    serializeDescData(),
  ].join('\n\n---\n\n');
}

// 거친 토큰 추정(한국어 ≈ 1.5자/토큰). CONTEXT_TOKEN_BUDGET 초과 감지용.
export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 1.5);
}
```

> **컨텍스트 예산 가드레일**: 조립 결과가 `CONTEXT_TOKEN_BUDGET`을 넘으면 빌드 시 콘솔 경고를 남기고, 레이어 파일을 핵심 섹션만 남겨 축약한다.
> 예산은 **선택한 모델의 컨텍스트 상한에서 답변 출력분과 대화 히스토리 여유를 뺀 값**으로 잡는다(예: 상한 65k → 48k). 상용 API 모델은 통상 75k로 충분하다.
> 예산을 넘겼는데 축약할 여지가 없으면 client-side RAG(precompute embeddings + cosine)로 전환한다 — 통상 규모(15~48k)에서는 불필요한 over-engineering이므로 먼저 축약을 시도한다.

---

## 3. grounding system prompt + structured output

### base-context.md (Layer 0) 골격

```markdown
당신은 이 프로토타입의 사양(아래 컨텍스트)에 대해 답하는 인스펙션 어시스턴트다.

## 답변 규칙
- 답변은 **아래 컨텍스트에서만** 근거를 찾는다. 외부 지식·추측을 쓰지 않는다.
- 컨텍스트에 없으면 정확히 이렇게 답한다: "사양에 정의되어 있지 않습니다."
- 모든 사실 주장 끝에 근거 섹션 id를 `[§id]` 형식으로 붙인다 (예: `[§2-1]`, `[§L-3]`).
- 개발 구현 방법·기술 스택·API는 답하지 않는다(이 프로토타입의 사양 범위 밖).
- 답변은 개조식(bullet) 우선. 표가 적합하면 마크다운 표를 쓴다.

## 텍스트 수정
- 사용자가 **명시적으로 desc 변경을 요청**할 때만 `propose_edit` 도구를 호출한다.
- 설명을 묻는 질문, 의견을 구하는 질문에는 도구를 호출하지 말고 평문으로 답한다.
- 요청받지 않은 num은 절대 건드리지 않는다.
```

### structured output (질문 경로)

답변에 citation을 구조적으로 강제하려면 `response_format`의 `json_schema`를 쓴다. 단 **스트리밍과 동시 사용 시 UX가 복잡**해지므로, 프로토타입에서는 다음 둘 중 하나를 고른다.

- **간이(권장)**: 스트리밍 + 본문 내 `[§id]` 인라인 토큰. 렌더 시 정규식으로 칩 변환(§8). 구현 단순, 스트리밍 자연스러움.
- **엄격**: 스트리밍 끄고 `json_schema`로 `{answer, citations[], grounded}` 강제. citation enum = 실제 num 목록. hallucinated id를 구조적으로 차단하나 스트리밍 포기.

```ts
// 엄격 모드용 스키마 (스트리밍 미사용 시)
const ANSWER_SCHEMA = {
  type: 'json_schema',
  json_schema: {
    name: 'grounded_answer',
    strict: true,
    schema: {
      type: 'object',
      additionalProperties: false,
      required: ['answer', 'citations', 'grounded'],
      properties: {
        answer: { type: 'string' },
        citations: { type: 'array', items: { type: 'string' } }, // 실제 num
        grounded: { type: 'boolean' }, // 컨텍스트로 답 가능 여부
      },
    },
  },
};
```

기본은 **간이 모드**(스트리밍 + 인라인 `[§id]`)로 구현한다. 아래 §6 코드는 간이 모드 기준이다.

---

## 4. propose_edit 도구 (텍스트 수정)

```ts
// src/lib/chatTools.ts
import descData from '../../descs/data.json';

// data.json의 모든 num을 enum으로 → 모델이 존재하지 않는 num을 생성 불가
const ALL_NUMS: string[] = [
  ...(descData.screenPolicies ?? []).map((p: any) => p.num),
  ...(descData.logicPolicies ?? []).map((p: any) => p.num),
];

export const PROPOSE_EDIT_TOOL = {
  type: 'function' as const,
  function: {
    name: 'propose_edit',
    description:
      '프로토타입 컴포넌트의 desc 텍스트 수정안을 제안한다. 사용자가 명시적으로 텍스트 변경을 요청할 때만 호출. 설명/의견 질문에는 호출하지 말 것. 요청받지 않은 num은 건드리지 말 것.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: ['scope', 'target_num', 'old_body', 'new_body', 'rationale'],
      properties: {
        scope: { type: 'string', enum: ['screen', 'logic'] },
        target_num: { type: 'string', enum: ALL_NUMS, description: '수정 대상 num' },
        old_body: { type: 'string', description: '모델이 읽은 현재 body 전문. stale 검증용.' },
        new_body: { type: 'string', description: '교체할 body 전문(전체 치환).' },
        rationale: { type: 'string', description: '한 줄: 무엇을 왜 바꿨는지.' },
      },
    },
  },
};
```

- `old_body`는 **적용용이 아니라 stale 검증용**(낙관적 동시성 토큰). 전체 치환이므로 적용은 `new_body`만 쓴다.
- `target_num`을 enum으로 제약 → 1차 가드(생성 단계 차단). 서버 재검증이 2차 가드(§5·§9).

---

## 5. api/chat.js — 프록시 (스트리밍 패스스루)

`api/save-desc.js`와 같은 디렉토리에 둔다. Vercel이 서버리스 함수로 인식한다([deployment.md](deployment.md)). 로컬·OpenAI 어느 쪽이든 **엔드포인트 스키마가 같으므로 base URL과 키만 환경변수로 바꾼다.**

```js
// api/chat.js
const BASE_URL = process.env.CHAT_API_BASE_URL ?? 'https://api.openai.com/v1';
const DASHBOARD_URL = process.env.CHAT_DASHBOARD_URL ?? '';

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  const apiKey = process.env.CHAT_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'CHAT_API_KEY 미설정' });

  // 🔴 사외 공유 시 필수: Origin 검증 + per-IP rate limit + 모델/max_tokens 서버측 고정 + (선택) x-app-secret 헤더.
  try {
    const upstream = await fetch(`${BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ ...req.body, stream: true }),
    });

    // 자체 호스팅 서버는 요청 모델이 메모리에 적재돼 있지 않으면 503을 반환하는 경우가 많다
    // (GPU 메모리 한계로 모델을 자동 교체하지 않는 구성). 사용자가 조치할 수 있게 구조화해 내려준다.
    if (upstream.status === 503) {
      return res.status(503).json({
        error: 'MODEL_NOT_LOADED',
        message: '요청한 모델이 LLM 서버에 적재되어 있지 않습니다.',
        dashboard: DASHBOARD_URL,
      });
    }
    if (upstream.status === 401) {
      return res.status(401).json({ error: 'UNAUTHORIZED', message: 'API 키가 서버 설정과 일치하지 않습니다.' });
    }
    if (!upstream.ok) {
      const t = await upstream.text();
      return res.status(upstream.status).json({ error: t });
    }

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    // SSE 청크를 그대로 클라이언트로 흘려보낸다
    const reader = upstream.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(decoder.decode(value, { stream: true }));
    }
    res.end();
  } catch (e) {
    // 자체 호스팅 서버가 사설망에 있는데 이 함수가 외부 클라우드에서 돌면 도달하지 못해 여기로 떨어진다.
    res.status(502).json({ error: 'UPSTREAM_UNREACHABLE', message: String(e) });
  }
}
```

**환경변수** — 프로바이더별로 값이 다르다.

| 변수 | `local`(자체 호스팅) | `api`(상용) |
|---|---|---|
| `CHAT_API_BASE_URL` | 서버의 OpenAI 호환 엔드포인트 (`http://<host>:<port>/v1`) | `https://api.openai.com/v1` |
| `CHAT_API_KEY` | 서버에 설정된 API 키 | 공급자 발급 키 |
| `CHAT_DASHBOARD_URL` | 관리 콘솔 주소(있으면). 503 안내에 노출 | 미사용 |

로컬 dev에서는 프로젝트 루트 `.env.local`에 넣는다. **`.env.local`이 `.gitignore`에 있는지 반드시 확인한다** — 키가 커밋되면 LLM 서버가 열린다. 배포 시에는 Vercel 대시보드 → Settings → Environment Variables에 `GITHUB_TOKEN`(save-desc용)과 별개로 추가하고, 빌드는 deployment.md의 `vercel deploy --prod`(런타임 env 자동 주입) 방식을 따른다.

> 🔴 **open proxy 남용 주의**: 프록시는 키 문자열만 숨긴다. `/api/chat`이 무인증 공개면 URL을 아는 누구나 호출할 수 있다.
> - **`local`**: 과금은 없지만 호출이 GPU를 점유해 **같은 서버를 쓰는 다른 사람의 작업을 지연**시킨다. 내부망 밖으로 노출되는 경로에는 `local`을 걸지 않는다.
> - **`api`**: 남용이 곧 비용이다. OpenAI는 하드 예산 컷오프를 제공하지 않으므로 선충전 잔액 + auto-recharge OFF 전용 키를 쓴다.
> - 공통: ① Origin/Referer 검증, ② per-IP rate limit, ③ 모델·max_tokens 서버측 고정, ④ (선택) `x-app-secret` 헤더.

---

## 5-b. 로컬 dev 서버에서 챗봇 쓰기 (Vite proxy)

`api/chat.js`는 Vercel 런타임 함수라 `npm run dev`에서는 실행되지 않는다. 자체 호스팅 LLM 서버를 쓰는 경우 로컬 dev가 주 사용 경로가 되므로, **Vite dev proxy로 같은 `/api/chat` 경로를 LLM 서버에 연결**한다. 클라이언트 코드는 그대로 둔다.

```ts
// vite.config.ts
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), ''); // VITE_ 접두어 없는 값도 읽는다
  const base = env.CHAT_API_BASE_URL ?? '';     // 예: http://<host>:<port>/v1
  return {
    server: {
      proxy: base ? {
        '/api/chat': {
          target: base.replace(/\/v1\/?$/, ''),
          changeOrigin: true,
          rewrite: () => '/v1/chat/completions',
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              proxyReq.setHeader('Authorization', `Bearer ${env.CHAT_API_KEY}`);
            });
          },
        },
      } : {},
    },
  };
});
```

- 페이지가 `http://localhost:5173`(HTTP)이고 요청도 서버측 프록시를 타므로 mixed content 차단이 발생하지 않는다.
- 프록시가 SSE를 그대로 흘려보내므로 스트리밍이 유지된다. 응답이 한꺼번에 몰려 오면 dev 미들웨어의 압축·버퍼링을 끈다.
- **desc 편집(`/api/save-desc`)은 이 방식으로 살아나지 않는다.** GitHub 커밋 함수라 배포 환경에서만 동작한다 — 로컬 dev는 질문·답변까지, 편집 반영은 배포본에서 한다.

---

## 6. InspectionChatContext (스트리밍 + tool 분기)

```tsx
// src/contexts/InspectionChatContext.tsx
import { createContext, useContext, useState, useRef, useCallback, type ReactNode } from 'react';
import { assembleContext } from '../lib/contextAssembler';
import { PROPOSE_EDIT_TOOL } from '../lib/chatTools';
import { CHAT_MODEL, MAX_OUTPUT_TOKENS, HISTORY_TURNS, CHAT_DASHBOARD_URL } from '../lib/chatConfig';

export interface EditProposal {
  scope: 'screen' | 'logic';
  target_num: string;
  old_body: string;
  new_body: string;
  rationale: string;
}
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  error?: boolean;
  proposal?: EditProposal; // 편집 제안 카드(있으면 InlineDiff 렌더)
  applied?: boolean;
}

interface InspectionChatCtx {
  open: boolean; toggle: () => void;
  messages: ChatMessage[];
  sending: boolean;
  focusedNum: string | undefined;
  setFocusedNum: (n: string | undefined) => void;
  sendMessage: (text: string) => Promise<void>;
  stop: () => void;
  clearMessages: () => void;
  applyProposal: (msgId: string) => Promise<void>;
  discardProposal: (msgId: string) => void;
}
const Ctx = createContext<InspectionChatCtx | null>(null);

const STORAGE_KEY = 'inspection-chat-history';
function loadHistory(): ChatMessage[] {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]'); } catch { return []; }
}

export function InspectionChatProvider({ children, saveBody, getBody }: {
  children: ReactNode;
  saveBody: (scope: 'screen' | 'logic', num: string, body: string) => Promise<{ ok: boolean; error?: string }>;
  getBody: (scope: 'screen' | 'logic', num: string) => string; // 현재 body 조회 (stale 재검증용)
}) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(loadHistory);
  const [sending, setSending] = useState(false);
  const [focusedNum, setFocusedNum] = useState<string | undefined>();
  const abortRef = useRef<AbortController | null>(null);

  const persist = (next: ChatMessage[]) => {
    setMessages(next);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next.slice(-40))); } catch { /* quota */ }
  };

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text, timestamp: Date.now() };
    const asstId = crypto.randomUUID();
    let working = [...messages, userMsg, { id: asstId, role: 'assistant' as const, content: '', timestamp: Date.now() }];
    persist(working);
    setSending(true);

    // 컨텍스트 조립 + 포커스 컴포넌트 본문 직접 주입
    let system = assembleContext();
    if (focusedNum) {
      system += `\n\n---\n\n# 현재 포커스 컴포넌트\n사용자가 [§${focusedNum}]을(를) 보고 질문 중. 우선 이 항목 기준으로 답하라.\n현재 본문:\n${getBody('screen', focusedNum) || getBody('logic', focusedNum)}`;
    }
    const history = [...messages, userMsg].slice(-HISTORY_TURNS * 2)
      .map(m => ({ role: m.role, content: m.content }));

    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const resp = await fetch('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: ac.signal,
        body: JSON.stringify({
          model: CHAT_MODEL, max_tokens: MAX_OUTPUT_TOKENS, stream: true,
          tools: [PROPOSE_EDIT_TOOL], tool_choice: 'auto',
          messages: [{ role: 'system', content: system }, ...history],
        }),
      });
      // 자체 호스팅 서버 특유의 실패를 사용자가 조치 가능한 문구로 바꾼다.
      // 🔴 오류 코드(§5의 api/chat.js가 붙임)와 상태코드를 함께 본다 —
      //    Vite dev proxy(§5-b)는 LLM 서버의 원본 응답을 그대로 흘려보내므로 코드가 오지 않는다.
      if (!resp.ok) {
        const info = await resp.json().catch(() => ({}));
        if (info.error === 'MODEL_NOT_LOADED' || resp.status === 503) {
          throw new Error(
            `모델 "${CHAT_MODEL}"이(가) LLM 서버에 적재되어 있지 않습니다.` +
            (CHAT_DASHBOARD_URL ? ` 관리 콘솔(${CHAT_DASHBOARD_URL})에서 모델을 기동한 뒤 다시 질문해 주세요.` : ' 서버 관리자에게 모델 기동을 요청해 주세요.')
          );
        }
        if (info.error === 'UNAUTHORIZED' || resp.status === 401)
          throw new Error('인증 실패 — 서버 키 설정(CHAT_API_KEY)을 확인해 주세요.');
        if (info.error === 'UPSTREAM_UNREACHABLE' || resp.status === 502 || resp.status === 504)
          throw new Error('LLM 서버에 연결할 수 없습니다. 네트워크 접속 상태를 확인해 주세요.');
        throw new Error(`HTTP ${resp.status}`);
      }
      if (!resp.body) throw new Error('응답 본문 없음');

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '', acc = '', toolArgs = '', isTool = false;

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? ''; // 마지막 미완성 라인 보존
        for (const line of lines) {
          const t = line.trim();
          if (!t.startsWith('data:')) continue;
          const payload = t.slice(5).trim();
          if (payload === '[DONE]') continue;
          const delta = JSON.parse(payload).choices?.[0]?.delta;
          if (delta?.tool_calls) {
            isTool = true;
            toolArgs += delta.tool_calls[0]?.function?.arguments ?? '';
          } else if (delta?.content) {
            acc += delta.content;
            working = working.map(m => m.id === asstId ? { ...m, content: acc } : m);
            persist(working); // throttle은 §8 ChatPanel에서 처리
          }
        }
      }

      if (isTool && toolArgs) {
        const p = JSON.parse(toolArgs) as EditProposal;
        working = working.map(m => m.id === asstId
          ? { ...m, content: `수정 제안: ${p.rationale}`, proposal: p } : m);
        persist(working);
      }
    } catch (e) {
      const msg = (e as Error).name === 'AbortError' ? '응답 중단됨' : `오류: ${(e as Error).message}`;
      working = working.map(m => m.id === asstId ? { ...m, content: msg, error: true } : m);
      persist(working);
    } finally {
      setSending(false); abortRef.current = null;
    }
  }, [messages, focusedNum, getBody]);

  const applyProposal = useCallback(async (msgId: string) => {
    const msg = messages.find(m => m.id === msgId);
    if (!msg?.proposal) return;
    const { scope, target_num, old_body, new_body } = msg.proposal;
    // 클라 측 stale 검증 (서버도 재검증)
    const current = getBody(scope, target_num);
    if (current !== old_body) {
      persist(messages.map(m => m.id === msgId
        ? { ...m, content: `${m.content}\n\n⚠️ 현재 본문이 제안 시점과 달라 적용 보류. 다시 질문해 주세요.`, error: true } : m));
      return;
    }
    const r = await saveBody(scope, target_num, new_body);
    persist(messages.map(m => m.id === msgId
      ? { ...m, applied: r.ok, content: r.ok ? `${m.content}\n\n✓ 적용됨 · 재배포 약 1분 후 반영` : `${m.content}\n\n저장 실패: ${r.error}` } : m));
  }, [messages, saveBody, getBody]);

  const discardProposal = (msgId: string) =>
    persist(messages.map(m => m.id === msgId ? { ...m, proposal: undefined, content: `${m.content}\n\n(제안 취소됨)` } : m));

  const stop = () => abortRef.current?.abort();
  const clearMessages = () => persist([]);

  return (
    <Ctx.Provider value={{ open, toggle: () => setOpen(p => !p), messages, sending, focusedNum, setFocusedNum, sendMessage, stop, clearMessages, applyProposal, discardProposal }}>
      {children}
    </Ctx.Provider>
  );
}
export const useInspectionChat = () => useContext(Ctx);
```

AppShell에서 Provider 중첩 — `saveBody`·`getBody`를 `useInspection()`에서 주입:

```tsx
function ChatProviderBridge({ children }) {
  const { saveBody, getScreenPolicy, getLogicPolicy } = useInspection();
  const getBody = (scope, num) => {
    const p = scope === 'logic' ? getLogicPolicy(num) : getScreenPolicy(num);
    return p?.body ?? '';
  };
  return <InspectionChatProvider saveBody={saveBody} getBody={getBody}>{children}</InspectionChatProvider>;
}
// <InspectionProvider> → <ChatProviderBridge> → 화면 + ChatToggle + ChatPanel
```

---

## 7. InlineDiff 컴포넌트 (jsdiff)

```bash
npm i diff   # jsdiff v9 (TS 타입 내장)
```

```tsx
// src/components/InlineDiff.tsx
import { diffWords, type Change } from 'diff';

export function InlineDiff({ oldText, newText }: { oldText: string; newText: string }) {
  return (
    <div className="chat-diff">
      {diffWords(oldText, newText).map((p: Change, i) =>
        p.added   ? <span key={i} className="chat-diff--add">{p.value}</span> :
        p.removed ? <span key={i} className="chat-diff--del">{p.value}</span> :
                    <span key={i}>{p.value}</span>
      )}
    </div>
  );
}
```

---

## 8. ChatPanel UI (스트리밍·마크다운·scope chip·추천질문·diff 카드)

```bash
npm i react-markdown remark-gfm rehype-highlight   # 마크다운 안전 렌더
```

```tsx
// AppShell 내부 함수 컴포넌트
import { createPortal } from 'react-dom';
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { InlineDiff } from '../components/InlineDiff';
import { useInspectionChat } from '../contexts/InspectionChatContext';
import { useInspection } from '../components/InspectionContext';

// 화면 컨텍스트에 맞춘 추천 질문 3~4개 (프로토타입마다 작성)
const SUGGESTED = ['이 화면의 진입 조건은?', '에러·빈 상태는 어떻게 처리돼?', '이 수치는 어떻게 계산돼?'];

function ChatToggle() {
  const c = useInspectionChat(); if (!c) return null;
  return <button className={`chat-toggle${c.open ? ' active' : ''}`} onClick={c.toggle} title="인스펙션 챗봇">챗봇</button>;
}

function ChatPanel() {
  const c = useInspectionChat();
  const { navigateTo, focusLogic } = useInspection();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);

  // 사용자가 바닥에 있을 때만 오토스크롤 (위로 스크롤해 읽는 중엔 방해 안 함)
  useEffect(() => {
    const el = scrollRef.current; if (!el) return;
    if (atBottom.current) el.scrollTop = el.scrollHeight;
  }, [c?.messages]);
  const onScroll = () => {
    const el = scrollRef.current; if (!el) return;
    atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  };

  if (!c?.open) return null;
  const { messages, sending, focusedNum, setFocusedNum, sendMessage, stop, clearMessages, applyProposal, discardProposal } = c;
  const send = (text: string) => { if (text.trim() && !sending) { sendMessage(text.trim()); setInput(''); } };

  // 본문의 [§id] → 클릭 가능한 citation 칩 (정책 패널로 이동)
  const renderContent = (text: string) => {
    const parts = text.split(/(\[§[\w-]+\])/g);
    return parts.map((p, i) => {
      const m = p.match(/^\[§([\w-]+)\]$/);
      if (m) return <button key={i} className="chat-cite" onClick={() => (m[1].startsWith('L-') ? focusLogic(m[1]) : navigateTo?.(m[1]))}>§{m[1]}</button>;
      return <ReactMarkdown key={i} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>{p}</ReactMarkdown>;
    });
  };

  return createPortal(
    <div className="chat-panel" role="log" aria-live="polite" aria-relevant="additions">
      <div className="chat-header">
        <span className="chat-header-title">인스펙션 챗봇</span>
        <button className="chat-clear-btn" onClick={clearMessages} title="대화 초기화">초기화</button>
      </div>

      {focusedNum && (
        <div className="chat-scope-chip">
          질문 범위: <strong>§{focusedNum}</strong>
          <button onClick={() => setFocusedNum(undefined)} aria-label="범위 해제">×</button>
        </div>
      )}

      <div className="chat-messages" ref={scrollRef} onScroll={onScroll}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>이 프로토타입의 사양·정책에 답합니다. 설명 모드에서 컴포넌트 우클릭 → "이것에 대해 물어보기".</p>
            <div className="chat-suggest">
              {SUGGESTED.map(q => <button key={q} onClick={() => send(q)}>{q}</button>)}
            </div>
          </div>
        )}
        {messages.map(m => (
          <div key={m.id} className={`chat-msg chat-msg--${m.role}${m.error ? ' chat-msg--error' : ''}`}>
            {renderContent(m.content)}
            {m.proposal && !m.applied && (
              <div className="chat-proposal">
                <div className="chat-proposal-head">§{m.proposal.target_num} 수정 제안</div>
                <InlineDiff oldText={m.proposal.old_body} newText={m.proposal.new_body} />
                <div className="chat-proposal-actions">
                  <button className="chat-apply" onClick={() => applyProposal(m.id)}>적용</button>
                  <button className="chat-discard" onClick={() => discardProposal(m.id)}>취소</button>
                </div>
              </div>
            )}
          </div>
        ))}
        {sending && <div className="chat-msg chat-msg--assistant chat-msg--loading">응답 중… <button className="chat-stop" onClick={stop}>중단</button></div>}
      </div>

      <div className="chat-input-area">
        <textarea className="chat-input" value={input} onChange={e => setInput(e.target.value)}
          placeholder="질문하거나 수정을 요청하세요…" disabled={sending}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); } }} />
        <button className="chat-send-btn" onClick={() => send(input)} disabled={sending || !input.trim()}>전송</button>
      </div>
    </div>,
    document.body
  );
}
```

> **스트리밍 throttle**: `acc` 갱신마다 setState하면 토큰당 리렌더로 thrashing이 난다. 위 코드는 단순화를 위해 매 델타 persist하지만, 체감 끊김이 있으면 `acc`를 ref에 모으고 `requestAnimationFrame` 또는 50ms throttle로 setState 한다.
> **마크다운 보안**: `react-markdown`은 기본 안전(raw HTML 이스케이프). **`rehype-raw`를 추가하지 않는다**(XSS). LLM 출력에 `dangerouslySetInnerHTML` 금지.
> **DescTooltip 연동**: "이것에 대해 물어보기" 버튼이 `setFocusedNum(num)` + `open=true`를 호출하도록 DescTooltip에 추가한다.

---

## 9. saveBody 재사용 + save-desc.js stale 검증 추가

텍스트 수정 Apply는 [desc-editing.md](desc-editing.md) §2의 `saveBody(scope, num, body)`를 그대로 호출한다 — **신규 백엔드 없음**. 단 챗봇 편집은 사람이 직접 입력한 게 아니라 LLM 제안이므로, save-desc.js에 **stale 검증**을 추가해 2차 가드를 둔다.

```js
// api/save-desc.js — 기존 함수에 expectedOld 검증 추가 (선택)
const { scope, num, body, expectedOld } = req.body || {};
// ... target 조회 후 ...
if (typeof expectedOld === 'string' && target.body !== expectedOld) {
  return res.status(409).json({ error: 'STALE', actual: target.body });
}
```

클라이언트는 Apply 시 `saveBody`에 `expectedOld`(=old_body)를 함께 보내고, `409 STALE`이면 챗 메시지에 "본문이 변경됨 — 재질문" 안내를 띄운다. 단일 사용자 프로토타입에서는 §6의 클라 측 검증만으로도 충분하므로 서버 검증은 외부 공유 시에만 추가한다.

---

## 10. CSS 추가분

```css
/* 토글·패널·헤더·메시지·입력은 SKILL.md Phase 9 CSS 유지. 아래는 고도화 추가분 */
.chat-scope-chip { display: flex; align-items: center; gap: 6px; padding: 6px 16px;
  background: var(--semantic-primary-line-light); font-size: 12px; color: var(--semantic-primary-default); flex-shrink: 0; }
.chat-scope-chip button { margin-left: auto; background: none; border: none; cursor: pointer; font-size: 14px; color: inherit; }

.chat-suggest { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; }
.chat-suggest button { text-align: left; font-size: 12.5px; padding: 7px 10px; border-radius: 8px;
  border: 1px solid var(--semantic-line-neutral); background: var(--semantic-bg-light);
  color: var(--semantic-text-default); cursor: pointer; }
.chat-suggest button:hover { background: var(--semantic-bg-default); }

.chat-cite { display: inline; padding: 0 5px; margin: 0 1px; border-radius: 4px; font-size: 11px;
  border: 1px solid var(--semantic-primary-default); background: var(--semantic-primary-line-light);
  color: var(--semantic-primary-default); cursor: pointer; vertical-align: baseline; }

.chat-proposal { margin-top: 8px; border: 1px solid var(--semantic-line-neutral); border-radius: 8px; overflow: hidden; }
.chat-proposal-head { padding: 6px 10px; font-size: 11.5px; font-weight: 700;
  background: var(--semantic-bg-light); color: var(--semantic-text-sub); }
.chat-diff { padding: 8px 10px; font-size: 12.5px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.chat-diff--add { background: #dcfce7; color: #166534; }
.chat-diff--del { background: #fee2e2; color: #991b1b; text-decoration: line-through; }
.chat-proposal-actions { display: flex; gap: 6px; padding: 8px 10px; border-top: 1px solid var(--semantic-line-neutral); }
.chat-apply { padding: 5px 14px; border: none; border-radius: 6px; background: var(--semantic-primary-default); color: #fff; cursor: pointer; font-size: 12px; }
.chat-discard { padding: 5px 12px; border: 1px solid var(--semantic-line-neutral); border-radius: 6px; background: none; color: var(--semantic-text-sub); cursor: pointer; font-size: 12px; }
.chat-stop { margin-left: 8px; font-size: 11px; padding: 2px 8px; border-radius: 4px; border: 1px solid currentColor; background: none; color: inherit; cursor: pointer; }

/* react-markdown 표·코드 기본 여백 */
.chat-msg table { border-collapse: collapse; font-size: 12px; margin: 4px 0; }
.chat-msg th, .chat-msg td { border: 1px solid var(--semantic-line-neutral); padding: 3px 7px; }
.chat-msg pre { background: var(--semantic-bg-light); border-radius: 6px; padding: 8px; overflow-x: auto; font-size: 12px; }
.chat-msg p { margin: 2px 0; } .chat-msg ul, .chat-msg ol { margin: 2px 0; padding-left: 18px; }
```

---

## 11. 토큰·컨텍스트 관리

| 항목 | 정책 |
|------|------|
| 메시지 히스토리 | 최근 `HISTORY_TURNS`턴(20메시지)만 API 전달. 슬라이딩 윈도우. 길어지면 헤더 "초기화" |
| 영속성 | `localStorage`에 최근 40메시지(프로토타입 규모엔 충분, Dexie/IndexedDB는 과함) |
| 컨텍스트 윈도우 | 전체 레이어 조립 ≈ 15~48k 토큰. `CONTEXT_TOKEN_BUDGET`(모델 상한에 맞춰 설정) 초과 시 축약 |
| 캐싱 | 불변 컨텍스트(system)를 messages 선두에 고정. `api`는 자동 프롬프트 캐싱이 적용되고, `local`은 서버의 prefix caching이 켜져 있을 때 이득이 생긴다 |
| GPU 점유 (`local`) | GPU 메모리 한계로 한 번에 한 모델만 적재되는 구성이 많다. 검토가 끝나면 관리 콘솔에서 모델을 내려 다른 사람이 쓸 수 있게 비운다 |

---

## 산출물 체크리스트

- [ ] `src/lib/chatConfig.ts` — `CHAT_PROVIDER`·`CHAT_MODEL`·`CHAT_DASHBOARD_URL` 단일 상수(하드코딩 제거)
- [ ] `src/lib/contextAssembler.ts` — 라우팅 없이 전부 주입 + 섹션 앵커 + data.json 직렬화
- [ ] `src/lib/chatTools.ts` — `propose_edit` 도구(num enum from data.json)
- [ ] `src/data/base-context.md` — grounding 규칙 + citation `[§id]` 형식 + 수정 도구 호출 조건
- [ ] `src/data/{prd,discovery,policies,changelog}-context.md` — 레이어 파일
- [ ] `api/chat.js` — 키 프록시(스트리밍 패스스루), `CHAT_API_BASE_URL`·`CHAT_API_KEY` 환경변수, 503·401·502 구조화 응답
- [ ] `vite.config.ts` — `/api/chat` dev proxy(로컬 dev에서 챗봇을 쓰려면 필수, §5-b)
- [ ] `.env.local` — `CHAT_API_BASE_URL`·`CHAT_API_KEY`, **`.gitignore` 등재 확인**
- [ ] `src/contexts/InspectionChatContext.tsx` — 스트리밍 파싱 + tool 분기 + saveBody 재사용 + localStorage + 503 안내 문구
- [ ] `src/components/InlineDiff.tsx` — jsdiff diffWords
- [ ] `ChatToggle`·`ChatPanel` — 마크다운 렌더·scope chip·추천질문·diff 카드·중단 버튼
- [ ] `intentClassifier.ts` **제거** (라우팅 폐기)
- [ ] (사외 공유 시) save-desc.js에 `expectedOld` stale 검증 추가
- [ ] (local 선택 시) LLM 서버 담당자에게 **tool calling 파싱 활성 여부** 확인(§1 — 꺼져 있으면 텍스트 수정 기능 불가)
- [ ] `npm i diff react-markdown remark-gfm rehype-highlight`
