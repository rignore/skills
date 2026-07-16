# 인스펙션 챗봇 아키텍처 (Chat Completions 기반)

설명 모드 프로토타입에 주입하는 컨텍스트 기반 챗봇의 **전체 구현 코드**. SKILL.md Phase 6~9의 설계 결정을 코드로 구현한다.

> 설계 원칙·정책·체크포인트는 SKILL.md Phase 6~9에 있다. 이 문서는 **코드**만 다룬다.

## 아키텍처 한눈에

```
사용자 입력
  → 컨텍스트 조립 (전부 주입 + 섹션 앵커 [DOC §ID] + descs/data.json)
  → /api/chat 프록시 (키 서버측 보관, 스트리밍 패스스루)
  → OpenAI Chat Completions (stream + tools=[propose_edit])
  → tool_call?
      ├─ 없음(질문) → 마크다운 스트리밍 렌더 + citation 칩 → 클릭 시 정책 패널 이동
      └─ 있음(편집) → InlineDiff 카드 → Apply → 기존 saveBody() 재사용 → 재배포
```

핵심 설계 결정 4가지:
1. **컨텍스트 라우팅 폐기** — regex `intentClassifier` 제거. 75k 토큰 이하 코퍼스는 전부 주입이 라우팅보다 안전(잘못 분기 시 정보 누락이 순손실).
2. **grounding + citation** — "컨텍스트에서만 답·없으면 미정의 응답·섹션 id 인용"을 system prompt와 structured output으로 강제.
3. **텍스트 수정 = saveBody 재사용** — 챗봇은 `propose_edit` 도구로 수정안만 제안. Apply 시 기존 `InspectionContext.saveBody(scope, num, body)`를 호출 → 새 백엔드 불필요. ([desc-editing.md](desc-editing.md) §2·§7)
4. **키 프록시** — 외부 공유 프로토타입은 `api/chat.js` 서버리스 프록시로 키를 서버측에 보관. 클라이언트는 `/api/chat`만 호출.

---

## 1. 모델·환경 설정

```ts
// src/lib/chatConfig.ts

// 🔴 모델 id는 회전 주기가 빠르다. 하드코딩 금지 — 이 상수 하나만 갱신한다.
// 배포 시점에 platform.openai.com/docs/models 에서 최신 모델을 확인하고 교체할 것.
// (gpt-4o는 구형일 수 있음. 비용·컨텍스트 윈도우를 보고 워크호스 모델을 고른다.)
export const CHAT_MODEL = 'gpt-4o';

export const MAX_OUTPUT_TOKENS = 1024;
export const HISTORY_TURNS = 10;          // 최근 N턴(2N 메시지)만 API에 전달
export const CONTEXT_TOKEN_BUDGET = 75_000; // 이 이상이면 컨텍스트 축약 또는 client RAG 검토
```

키는 클라이언트에 두지 않는다. `api/chat.js` 프록시(§5)가 `process.env.OPENAI_API_KEY`로 보관한다.

> `VITE_OPENAI_API_KEY`는 빌드 시 번들에 **평문 인라인**되어 브라우저에 노출된다(Vite 공식 동작). 외부 공유 프로토타입에서는 반드시 프록시를 쓴다.

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

> **75k 가드레일**: 조립 결과가 `CONTEXT_TOKEN_BUDGET`을 넘으면 빌드 시 콘솔 경고를 남기고, 레이어 파일을 핵심 섹션만 남겨 축약한다. 100k를 넘으면 전부 주입을 포기하고 client-side RAG(precompute embeddings + cosine)로 전환한다 — 단 현 규모(통상 15~75k)에서는 불필요한 over-engineering이므로 도입하지 않는다.

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

`api/save-desc.js`와 같은 디렉토리에 둔다. Vercel이 서버리스 함수로 인식한다([deployment.md](deployment.md)).

```js
// api/chat.js
export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'OPENAI_API_KEY 미설정' });

  // 🔴 외부 공유 시 필수: Origin 검증 + per-IP rate limit + 모델/max_tokens 서버측 고정 + (선택) x-app-secret 헤더.
  //    무인증이면 URL만 알면 누구나 내 OpenAI 비용으로 호출 가능(open proxy 남용).
  try {
    const upstream = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ ...req.body, stream: true }),
    });
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
    res.status(500).json({ error: String(e) });
  }
}
```

> **환경변수**: Vercel 대시보드 → Settings → Environment Variables → `OPENAI_API_KEY` 추가(Production). `GITHUB_TOKEN`(save-desc용)과 별개. 빌드 방식은 deployment.md의 `vercel deploy --prod`(런타임 env 자동 주입)를 따른다.
> **spend-cap**: OpenAI는 하드 예산 컷오프를 제공하지 않으므로(대시보드 한도는 알림용), 선충전 잔액 + auto-recharge OFF인 전용 프로젝트 키를 쓴다.
> 🔴 **open proxy 남용 주의**: 프록시는 키 문자열만 숨긴다. `/api/chat`이 무인증 공개면 URL을 아는 누구나 내 계정으로 호출할 수 있다. 외부 공유 시 ① Origin/Referer 검증, ② per-IP rate limit, ③ 모델·max_tokens 서버측 고정, ④ (선택) `x-app-secret` 헤더를 함께 적용한다. 저한도 키는 최후 방어선일 뿐 남용 자체를 막지 못한다.

---

## 6. InspectionChatContext (스트리밍 + tool 분기)

```tsx
// src/contexts/InspectionChatContext.tsx
import { createContext, useContext, useState, useRef, useCallback, type ReactNode } from 'react';
import { assembleContext } from '../lib/contextAssembler';
import { PROPOSE_EDIT_TOOL } from '../lib/chatTools';
import { CHAT_MODEL, MAX_OUTPUT_TOKENS, HISTORY_TURNS } from '../lib/chatConfig';

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
      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

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
| 컨텍스트 윈도우 | 전체 레이어 조립 ≈ 15~75k 토큰. `CONTEXT_TOKEN_BUDGET`(75k) 초과 시 축약, 100k 초과 시 client RAG 검토 |
| 캐싱 | 불변 컨텍스트(system)를 messages 선두에 고정 → OpenAI 자동 프롬프트 캐싱 이득 |

---

## 산출물 체크리스트

- [ ] `src/lib/chatConfig.ts` — `CHAT_MODEL` 단일 상수(하드코딩 제거), 배포 전 최신 모델 확인 주석
- [ ] `src/lib/contextAssembler.ts` — 라우팅 없이 전부 주입 + 섹션 앵커 + data.json 직렬화
- [ ] `src/lib/chatTools.ts` — `propose_edit` 도구(num enum from data.json)
- [ ] `src/data/base-context.md` — grounding 규칙 + citation `[§id]` 형식 + 수정 도구 호출 조건
- [ ] `src/data/{prd,discovery,policies,changelog}-context.md` — 레이어 파일
- [ ] `api/chat.js` — 키 프록시(스트리밍 패스스루), `OPENAI_API_KEY` 환경변수
- [ ] `src/contexts/InspectionChatContext.tsx` — 스트리밍 파싱 + tool 분기 + saveBody 재사용 + localStorage
- [ ] `src/components/InlineDiff.tsx` — jsdiff diffWords
- [ ] `ChatToggle`·`ChatPanel` — 마크다운 렌더·scope chip·추천질문·diff 카드·중단 버튼
- [ ] `intentClassifier.ts` **제거** (라우팅 폐기)
- [ ] (외부 공유 시) save-desc.js에 `expectedOld` stale 검증 추가
- [ ] `npm i diff react-markdown remark-gfm rehype-highlight`
