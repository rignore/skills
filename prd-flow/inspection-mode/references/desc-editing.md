# desc 직접 편집 기능 (data.json SoT)

설명 모드에서 툴팁·정책 패널의 desc를 **브라우저에서 직접 편집 → GitHub 커밋 → 자동 재배포**로 반영하는 표준 구현. 프롬프트 없이 비개발자가 desc를 고칠 수 있다.

이 기능을 켜면 desc의 단일 소스(SoT)가 `descs/data.json`이 된다. 화면 컴포넌트의 `DESC_*` 상수와 PolicyIndexPanel의 `body`가 두 곳에 흩어지는 drift를 구조적으로 차단한다.

> 배포 인프라(Vercel·GitHub Actions·토큰)는 [deployment.md](deployment.md) 참조. 이 문서는 **코드**만 다룬다.

---

## 핵심 원칙

1. **SoT는 `descs/data.json` 하나.** 화면 `.jsx`에는 `DESC_*` 상수를 두지 않는다. DescTooltip·PolicyIndexPanel 모두 이 파일에서 읽는다.
2. **DescTooltip에는 `num`만 넘긴다.** title·componentId·body는 data.json에서 조회한다.
3. **렌더러는 `DetailBody` 하나로 통일.** 툴팁(다크)·패널(라이트) 양쪽에서 `[헤더]`·`{L-n}` 칩을 일관되게 렌더.
4. **편집은 낙관적 갱신 + API 커밋.** 화면 즉시 반영 + `/api/save-desc`가 data.json 커밋 → 재배포로 영구화.
5. **🔴 섹션은 표시 정보 단위로 세분 넘버링 (SKILL.md Phase 5 필수 규칙 — SoT에서도 반드시 적용).** 한 섹션(`[n-n]`) 안에 값이 바인딩되는 개별 표시 정보(수치·카드·차트 등)나 인터랙션 요소가 여럿이면, 각각 하위 번호(`[n-na]`, `[n-nb]`…)로 **data.json `screenPolicies`에 별도 항목**을 만들고, 화면 `.jsx`는 표시 정보별로 **중첩 DescTooltip**을 감싼다. 섹션 desc 하나에 여러 표시 정보를 뭉뚱그리지 않는다.
   - 예: "주문 요약" 섹션(`2-2`) = 섹션 정의(`2-2`) + 총 주문 금액(`2-2a`) + 할인 적용액(`2-2b`) + 결제 수단 분포 차트(`2-2c`). 각각 별도 data.json 항목 + 중첩 `<DescTooltip num="2-2a">…`.
   - ⚠️ SoT 전환 시 흔한 누락: 섹션을 단일 num으로만 만들고 하위 표시 정보를 섹션 body에 줄글로 묶어버림. **값이 화면에 따로 렌더되면 desc도 따로 쪼갠다.**

---

## 파일 구성

```
wireframe/
├── descs/data.json              ← SoT (screenPolicies[] + logicPolicies[])
├── api/save-desc.js             ← 서버리스 함수 (data.json 커밋)
└── components/
    ├── InspectionContext.jsx    ← descData state + saveBody
    ├── DetailBody.jsx           ← [헤더]·{L-n} 칩 렌더 (공용)
    ├── EditableBody.jsx         ← DetailBody + 인라인 편집
    ├── DescTooltip.jsx          ← num 조회 + EditableBody + 실측 위치
    └── PolicyIndexPanel.jsx     ← data.json 목록 + EditableBody
```

---

## 1. `descs/data.json` — SoT

`screenPolicies`는 화면 컴포넌트 desc(DescTooltip), `logicPolicies`는 cross-cutting 로직(L-n). body 안의 `{L-n}`은 렌더 시 클릭 가능한 칩이 된다.

```json
{
  "screenPolicies": [
    {
      "num": "2-1",
      "group": "주간 요약 모달",
      "screen": "screen-02",
      "title": "AI 요약",
      "componentId": "AiSummarySection",
      "body": "LLM이 …\n\n[AI 생성 텍스트 구성]\n· …\n\n생성 방식 상세: {L-3}"
    }
  ],
  "logicPolicies": [
    {
      "num": "L-1",
      "title": "추천 우선순위 점수 산출",
      "refId": "RecommendSection",
      "refScreen": "screen-02",
      "body": "[가중치 합산]\n…"
    }
  ]
}
```

- 화면 정책: `num`(예 `1-1`, `1-1a`), `group`, `screen`, `title`, `componentId`, `body`
- 로직 정책: `num`(예 `L-1`), `title`, `refId`(대표 컴포넌트), `refScreen`, `body`
- body 안 L-참조는 평문이 아니라 `{L-3}` 토큰으로 쓴다 (DetailBody가 칩으로 렌더).

---

## 2. `components/InspectionContext.jsx`

descData를 state로 보유(편집 시 낙관적 갱신). `saveBody`가 낙관적 반영 + API 커밋.

```jsx
import React, { createContext, useContext, useState } from 'react';
import descData from '../descs/data.json';

export const POLICY_FOCUS_LOGIC = 'policy:focus-logic';

const InspectionContext = createContext({
  active: false, toggle: () => {}, navigateTo: null,
  screenPolicies: [], logicPolicies: [],
  getScreenPolicy: () => null, getLogicPolicy: () => null,
  focusLogic: () => {}, saveBody: async () => ({ ok: false }),
});

export function InspectionProvider({ children, navigateTo }) {
  const [active, setActive] = useState(false);
  const [data, setData] = useState(descData);

  const getScreenPolicy = (num) => data.screenPolicies.find(p => p.num === num) || null;
  const getLogicPolicy = (num) => data.logicPolicies.find(p => p.num === num) || null;
  const focusLogic = (num) =>
    window.dispatchEvent(new CustomEvent(POLICY_FOCUS_LOGIC, { detail: num }));

  const saveBody = async (scope, num, body) => {
    setData(prev => {
      const next = JSON.parse(JSON.stringify(prev));
      const list = scope === 'logic' ? next.logicPolicies : next.screenPolicies;
      const t = list.find(p => p.num === num);
      if (t) t.body = body;
      return next;
    });
    try {
      const r = await fetch('/api/save-desc', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scope, num, body }),
      });
      const j = await r.json().catch(() => ({}));
      return r.ok ? { ok: true, ...j } : { ok: false, error: j.error || `HTTP ${r.status}` };
    } catch (e) {
      return { ok: false, error: String((e && e.message) || e) };
    }
  };

  return (
    <InspectionContext.Provider value={{
      active, toggle: () => setActive(p => !p), navigateTo: navigateTo || null,
      screenPolicies: data.screenPolicies, logicPolicies: data.logicPolicies,
      getScreenPolicy, getLogicPolicy, focusLogic, saveBody,
    }}>
      {children}
    </InspectionContext.Provider>
  );
}

export const useInspection = () => useContext(InspectionContext);
```

---

## 3. `components/DetailBody.jsx` — 공용 렌더러

```jsx
import React from 'react';

// [헤더] → 소제목, 빈 줄 → 간격, {L-n} → 칩. variant: 'panel'(라이트) | 'tooltip'(다크)
export function DetailBody({ body, onLogicClick, variant = 'panel' }) {
  if (!body) return null;
  const cls = variant === 'tooltip'
    ? { h: 'dtd-h', l: 'dtd-l', sp: 'dtd-sp' }
    : { h: 'ipd-h', l: 'ipd-l', sp: 'ipd-sp' };
  return (
    <div>
      {body.split('\n').map((line, i) => {
        const t = line.trim();
        if (t === '') return <div key={i} className={cls.sp} />;
        if (t.charAt(0) === '[') return <div key={i} className={cls.h}>{t}</div>;
        const parts = t.split(/(\{L-\d+\})/g);
        const hasRef = parts.length > 1;
        return (
          <div key={i} className={cls.l}>
            {hasRef
              ? parts.map((p, j) => {
                  const m = p.match(/^\{(L-\d+)\}$/);
                  if (m) return <button key={j} className="ipd-ref" onClick={() => onLogicClick && onLogicClick(m[1])}>{m[1]}</button>;
                  return p;
                })
              : line}
          </div>
        );
      })}
    </div>
  );
}
```

---

## 4. `components/EditableBody.jsx` — 인라인 편집

```jsx
import React, { useState } from 'react';
import { DetailBody } from './DetailBody';
import { useInspection } from './InspectionContext';

export function EditableBody({ scope, num, body, variant = 'panel', onLogicClick }) {
  const { saveBody } = useInspection();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const cls = variant === 'tooltip' ? 'eb eb-tooltip' : 'eb eb-panel';

  function startEdit(e) { e && e.stopPropagation(); setDraft(body); setMsg(''); setEditing(true); }
  async function save(e) {
    e && e.stopPropagation();
    setSaving(true); setMsg('');
    const r = await saveBody(scope, num, draft);
    setSaving(false);
    if (r.ok) { setEditing(false); setMsg(r.unchanged ? '' : '저장됨 · 재배포 약 1분 후 영구 반영'); }
    else setMsg('저장 실패: ' + r.error);
  }

  if (editing) {
    return (
      <div className={cls}>
        <textarea className="eb-area" value={draft} onChange={e => setDraft(e.target.value)}
          onClick={e => e.stopPropagation()}
          rows={Math.min(20, Math.max(6, draft.split('\n').length + 1))} />
        <div className="eb-actions">
          <button className="eb-btn eb-save" onClick={save} disabled={saving}>{saving ? '저장 중…' : '저장'}</button>
          <button className="eb-btn eb-cancel" onClick={e => { e.stopPropagation(); setEditing(false); }} disabled={saving}>취소</button>
        </div>
        {msg && <div className="eb-msg">{msg}</div>}
      </div>
    );
  }
  return (
    <div className={cls}>
      <DetailBody body={body} variant={variant} onLogicClick={onLogicClick} />
      <button className="eb-btn eb-edit" onClick={startEdit}>✎ 편집</button>
      {msg && <div className="eb-msg">{msg}</div>}
    </div>
  );
}
```

---

## 5. `components/DescTooltip.jsx` — num 조회 + 편집 + 실측 위치

기존 Phase 3 DescTooltip을 아래로 대체한다. 핵심 변경: `num`으로 data.json 조회, 본문은 `EditableBody`, 위치는 **실측 후 보정**(하단 공간 부족 시 커서 위로).

```jsx
import React, { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { useInspection } from './InspectionContext';
import { EditableBody } from './EditableBody';
import { DetailBody } from './DetailBody';

const DT_CLOSE_ALL = 'dt:close-all';

export function DescTooltip({ num, desc: descProp, label: labelProp, componentId: cidProp, children }) {
  const { active, getScreenPolicy, focusLogic } = useInspection();
  const policy = num ? getScreenPolicy(num) : null;
  const body = (policy && policy.body) || descProp || '';
  const label = (policy && policy.title) || labelProp;
  const componentId = (policy && policy.componentId) || cidProp;

  const [show, setShow] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const cursor = useRef({ x: 0, y: 0 });
  const tooltipRef = useRef(null);

  useEffect(() => { if (!active) setShow(false); }, [active]);
  useEffect(() => {
    const handler = () => setShow(false);
    window.addEventListener(DT_CLOSE_ALL, handler);
    return () => window.removeEventListener(DT_CLOSE_ALL, handler);
  }, []);
  useEffect(() => {
    if (!show) return;
    const onOutside = (e) => { if (tooltipRef.current && !tooltipRef.current.contains(e.target)) setShow(false); };
    document.addEventListener('mousedown', onOutside, true);
    return () => document.removeEventListener('mousedown', onOutside, true);
  }, [show]);
  useEffect(() => {
    if (!show) return;
    const onKey = (e) => { if (e.key === 'Escape') setShow(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [show]);

  // 실측 기반 위치 보정: 우측 부족→왼쪽, 하단 부족→위
  useLayoutEffect(() => {
    if (!show || !tooltipRef.current) return;
    const { x: cx, y: cy } = cursor.current;
    const w = tooltipRef.current.offsetWidth;
    const h = tooltipRef.current.offsetHeight;
    const m = 8;
    const x = cx + w + m > window.innerWidth ? Math.max(m, cx - w - 4) : cx + 4;
    const y = cy + h + m > window.innerHeight ? Math.max(m, cy - h - m) : cy + m;
    setPos({ x, y });
  }, [show]);

  function handleContextMenu(e) {
    if (!active) return;
    e.preventDefault();
    e.stopPropagation();
    const wasShown = show;
    window.dispatchEvent(new CustomEvent(DT_CLOSE_ALL));
    if (!wasShown && body) {
      cursor.current = { x: e.clientX, y: e.clientY };
      setPos({ x: e.clientX + 4, y: e.clientY + 8 });
      setShow(true);
    }
  }

  return (
    <div
      className={active ? `dt-wrap${show ? ' dt-wrap--selected' : ''}` : undefined}
      data-comp-id={componentId}
      data-num={active ? (num || undefined) : undefined}
      onContextMenu={handleContextMenu}
    >
      {children}
      {active && show && createPortal(
        <div ref={tooltipRef} className="dt-box" style={{ left: pos.x, top: pos.y }} onClick={e => e.stopPropagation()}>
          {label && <div className="dt-label">{label}</div>}
          {num
            ? <EditableBody scope="screen" num={num} body={body} variant="tooltip" onLogicClick={focusLogic} />
            : <DetailBody body={body} variant="tooltip" onLogicClick={focusLogic} />}
        </div>,
        document.body
      )}
    </div>
  );
}
```

화면 `.jsx`에서는 `num`만 넘긴다: `<DescTooltip num="2-1"><div .../></DescTooltip>`

---

## 6. `components/PolicyIndexPanel.jsx` — 핵심 변경점

- 정책 데이터를 `useInspection()`의 `screenPolicies`/`logicPolicies`에서 가져온다(상수 배열 제거).
- 본문 렌더를 `EditableBody`로 (화면 탭 `scope="screen"`, 로직 탭 `scope="logic"`).
- `{L-n}` 칩이 DescTooltip에서 클릭될 때를 위해 `POLICY_FOCUS_LOGIC` 이벤트를 수신.

```jsx
import { useInspection, POLICY_FOCUS_LOGIC } from './InspectionContext';
import { EditableBody } from './EditableBody';
// …
const { active, screenPolicies, logicPolicies } = useInspection();
// 화면 탭: <EditableBody scope="screen" num={policy.num} body={policy.body} variant="panel" onLogicClick={handleLogicRefChip} />
// 로직 탭: <EditableBody scope="logic" num={policy.num} body={policy.body} variant="panel" onLogicClick={handleLogicRefChip} />

// DescTooltip의 {L-n} 칩 클릭 수신
useEffect(() => {
  const handler = (e) => handleLogicRefChip(e.detail);
  window.addEventListener(POLICY_FOCUS_LOGIC, handler);
  return () => window.removeEventListener(POLICY_FOCUS_LOGIC, handler);
}, [logicPolicies]);
```

---

## 7. `api/save-desc.js` — 서버리스 함수

`Root Directory/api/` 에 둔다. Vercel이 자동으로 서버리스 함수로 인식한다(Vite 프로젝트에서도 동작). `DESC_PATH`만 프로토타입별로 환경변수 또는 기본값으로 맞춘다.

```js
const REPO = process.env.DESC_REPO || '{owner}/{repo}';  // 프로토타입 모음 repo로 교체
const PATH = process.env.DESC_PATH || '{project}/wireframe/descs/data.json';  // 프로토타입별 교체
const BRANCH = process.env.DESC_BRANCH || 'main';

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST 메서드만 허용됩니다.' });
  const { scope, num, body } = req.body || {};
  if ((scope !== 'screen' && scope !== 'logic') || !num || typeof body !== 'string')
    return res.status(400).json({ error: 'scope(screen|logic), num, body(문자열)가 필요합니다.' });

  const token = process.env.GITHUB_TOKEN;
  if (!token) return res.status(500).json({ error: 'GITHUB_TOKEN 환경변수가 설정되지 않았습니다.' });

  const api = `https://api.github.com/repos/${REPO}/contents/${PATH}`;
  const headers = { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'User-Agent': 'desc-editor' };
  try {
    const getRes = await fetch(`${api}?ref=${BRANCH}`, { headers });
    if (!getRes.ok) return res.status(502).json({ error: 'data.json 읽기 실패', detail: await getRes.text() });
    const file = await getRes.json();
    const data = JSON.parse(Buffer.from(file.content, 'base64').toString('utf-8'));

    const list = scope === 'logic' ? data.logicPolicies : data.screenPolicies;
    const target = Array.isArray(list) ? list.find(p => p.num === num) : null;
    if (!target) return res.status(404).json({ error: `${scope} 정책 ${num}을(를) 찾을 수 없습니다.` });
    if (target.body === body) return res.status(200).json({ ok: true, unchanged: true });
    target.body = body;

    const newContent = JSON.stringify(data, null, 2) + '\n';
    const putRes = await fetch(api, {
      method: 'PUT', headers,
      body: JSON.stringify({
        message: `edit(desc): ${scope} ${num} 인스펙션 편집`,
        content: Buffer.from(newContent, 'utf-8').toString('base64'),
        sha: file.sha, branch: BRANCH,
      }),
    });
    if (!putRes.ok) return res.status(502).json({ error: '커밋 실패', detail: await putRes.text() });
    const result = await putRes.json();
    return res.status(200).json({ ok: true, commit: result.commit && result.commit.sha });
  } catch (e) {
    return res.status(500).json({ error: '처리 중 오류', detail: String(e) });
  }
}
```

> **보안**: 이 API는 무인증이다. 공개 URL이면 누구나 desc를 수정할 수 있다(git 이력에 남아 되돌리기는 쉬움). 외부 공유 프로토타입이면 `x-edit-secret` 헤더 검증 등 최소 보호를 추가한다.

---

## 8. CSS 추가분

```css
/* DetailBody 다크 변형 (툴팁) */
.dtd-h { font-size: 11.5px; font-weight: 700; color: #9db4e8; margin: 9px 0 3px; }
.dtd-l { font-size: 12.5px; line-height: 1.6; color: #d6dbe8; white-space: pre-wrap; }
.dtd-sp { height: 6px; }

/* 인라인 편집 — eb-tooltip(다크) / eb-panel(라이트) */
.eb { position: relative; }
.eb-edit { margin-top: 8px; font-size: 11px; padding: 3px 9px; border-radius: 4px; cursor: pointer; border: 1px solid transparent; }
.eb-tooltip .eb-edit { background: rgba(125,164,248,0.15); border-color: rgba(125,164,248,0.4); color: #9db4e8; }
.eb-tooltip .eb-edit:hover { background: rgba(125,164,248,0.28); }
.eb-panel .eb-edit { background: #f0f3ff; border-color: rgba(74,113,255,0.3); color: #4a71ff; }
.eb-panel .eb-edit:hover { background: #e4ebff; }
.eb-area { width: 100%; box-sizing: border-box; font-family: inherit; font-size: 12px; line-height: 1.55; border-radius: 6px; padding: 8px; resize: vertical; }
.eb-tooltip .eb-area { background: #11131c; color: #e2e6f0; border: 1px solid rgba(125,164,248,0.45); }
.eb-panel .eb-area { background: #fff; color: #171719; border: 1px solid rgba(74,113,255,0.45); }
.eb-actions { display: flex; gap: 6px; margin-top: 6px; }
.eb-btn { font-size: 11px; padding: 4px 12px; border-radius: 4px; cursor: pointer; border: none; }
.eb-btn:disabled { opacity: 0.5; cursor: default; }
.eb-save { background: #4a71ff; color: #fff; }
.eb-cancel { background: transparent; }
.eb-tooltip .eb-cancel { color: #9db4e8; border: 1px solid rgba(125,164,248,0.4); }
.eb-panel .eb-cancel { color: #70737c; border: 1px solid rgba(112,115,124,0.3); }
.eb-msg { font-size: 11px; margin-top: 6px; line-height: 1.5; }
.eb-tooltip .eb-msg { color: #9db4e8; }
.eb-panel .eb-msg { color: #4a71ff; }
```

`ipd-ref`(L-n 칩)는 파란 배경이라 다크·라이트 양쪽에서 보인다 — 공용.

---

## 🔴 프롬프트(에이전트) 수정 시 SoT 동기화 — 브라우저 편집분 보호 (필수)

desc 편집 기능을 켜면 `data.json`의 SoT는 **원격 repo**다. 브라우저 편집은 `/api/save-desc`로 **원격에만** 커밋되고, 로컬 작업본(`prd-flow/{project}/wireframe/descs/data.json`)은 그 변경을 모른다.

따라서 에이전트가 프롬프트로 desc·정책을 수정할 때 **로컬 사본을 통째로 복사·커밋하면 원격의 브라우저 편집분이 옛 로컬 버전으로 덮어써져 초기화된다.** (원격을 `git pull`로 받아도, 직후 로컬 전체본을 `cp`로 덮으면 동일하게 소실된다.)

**규칙 — 전체 덮어쓰기 금지:**
1. 수정 **직전** 원격 `data.json`을 최신으로 가져온다 (`git pull` 또는 GitHub contents API). 이것이 SoT다.
2. 그 최신본을 **로컬 작업본에 먼저 반영**(원격 → 로컬 동기화)한 뒤, 그 위에서 **대상 항목(num)만** 수정한다. 로컬의 옛 전체본을 원격에 cp 하지 않는다.
3. 커밋·push.

**권장 구현**: 가능하면 `save-desc`와 같은 **num 단위 패치 경로**로 수정한다(특정 `num`의 `body`만 교체). 전체 파일 직렬화 후 복사하는 절차는 다른 num의 원격 편집분을 날릴 위험이 크다.

**세션 시작 시**: desc 편집이 켜진 프로토타입을 프롬프트로 손대기 전, 로컬 `data.json`을 원격에서 1회 동기화한다. 로컬 작업본은 "참고 사본"이며 SoT가 아니다.

이 원칙은 `data.json` 외에 `FORMULAS.md` 등 **원격이 편집·배포되는 다른 SoT 파일에도 동일**하게 적용한다.

### 🔴 기능 범위·정책 변경은 prd-sync로 PRD 동기화 (필수)

desc·화면 편집이 단순 표현 수정이 아니라 **제품 범위 변경**(화면 추가·제외, 단일 화면 통합, 임계·정책의 하드코딩 결정 등)이면, 이는 디스크립션 SoT를 넘어 **PRD가 SoT인 `EP-`의 포함 범위·완료 상태 변경**이다. 직접 편집으로 끝내지 말고 편집 직후 **prd-sync를 호출**해 PRD에 역전파(컨펌 게이트)한다.

- 예: "알림 화면은 안 만든다", "위젯은 빼고 상세 팝업 하나로", "임계는 코드에 고정"처럼 Epic 범위·완료 상태가 달라지는 결정은 prd-sync가 필요하다.
- 이걸 누락하면 PRD가 drift된 채 남아, 그 PRD를 입력으로 하는 후속 개발 단계(ai-dlc의 유저스토리·유닛 분할)가 제외된 기능까지 만들어 낸다(실제 발생). 수식·표시 형식 같은 디스크립션 내부 변경은 역전파 대상이 아니다(레이어 분리 유지).

---

## 적용 체크리스트

- [ ] desc를 화면 `.jsx`의 `DESC_*` 상수가 아니라 `descs/data.json`에 모았다 (SoT)
- [ ] (프롬프트 수정 시) 원격 SoT를 먼저 동기화하고 대상 num만 수정했다 — 로컬 전체본 cp 금지
- [ ] 화면 `.jsx`의 DescTooltip은 `num`만 넘긴다 (label·componentId·desc 제거)
- [ ] body 안 L-참조는 `{L-n}` 토큰으로 (평문 "로직 탭 L-n" 금지)
- [ ] DetailBody·EditableBody·InspectionContext(saveBody)·api/save-desc.js 배치
- [ ] CSS에 `dtd-*`·`eb-*` 추가
- [ ] `api/save-desc.js`의 `DESC_PATH`를 해당 프로토타입 경로로 설정
- [ ] 배포 인프라는 [deployment.md](deployment.md) 따라 1회 설정
