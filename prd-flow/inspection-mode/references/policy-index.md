# 정책 인덱스 (Policy Index)

설명 모드 프로토타입에서, **컴포넌트별 정책·디스크립션을 한 곳에서 상세 가능하게 펼쳐 보여주는 우측 사이드 패널**. 항목을 클릭하면 해당 화면·컴포넌트로 자동 이동해 강조(펄스) 처리하고, 정책 내용을 토글로 펼쳐 보여준다. 컴포넌트를 직접 우클릭해도 동일한 디스크립션 툴팁이 뜬다.

## 1. 개요

### 무엇을 해결하는가
- 와이어프레임이 많아 복잡해질수록 "이 컴포넌트가 무슨 정책을 따르는지" 한눈에 매핑되지 않음.
- 우클릭만으로는 **전체 정책 목록**·**번호 체계**·**그룹화**를 인지하기 어려움.
- 검토자가 "정책 → 화면" 양방향으로 탐색할 수 있어야 함.

### 핵심 UX
- 우측 상단 토글로 **설명 모드 ON/OFF**.
- 설명 모드 ON 시 우측 사이드에 **정책 인덱스 패널** 표시.
- 패널에는 그룹별 헤더 + 항목(`[번호] 제목`) 리스트.
- 항목 클릭 → 해당 화면으로 전환 + 컴포넌트로 스크롤 + 펄스 + 디스크립션 펼침.
- 컴포넌트 우클릭 → 디스크립션 툴팁 표시 + 컴포넌트 강조.
- 설명 모드 ON 시 각 컴포넌트 점선 박스 **좌상단에 `[번호]` 배지**를 표시 → 박스만 보고 패널 항목과 즉시 매칭(`data-num` 기준).
- 패널은 `position: fixed`로 컨텐츠 위에 뜬다 → **설명 모드 ON 시 컨텐츠 영역을 패널 폭만큼 좁혀 가림을 방지한다**(특히 우측 정렬 버튼·요소가 패널 뒤에 숨는 문제). 아래 "패널 레이아웃" CSS 참조.

---

## 2. 데이터 모델

### `POLICIES` 배열 — 인덱스 정의
```js
var POLICIES = [
  { key:'policy',  num:'0-0', title:'권한 등급 구분',           group:'policy' },
  { key:'entry',   num:'1-0', title:'진입부',                   group:'entry' },
  { key:'rolecol', num:'2-0', title:'목록의 열람 가능 역할 컬럼', group:'role' },
  // ...
];
```
- `key`: 컴포넌트의 `data-desc` 값과 1:1 매핑.
- `num`: 표시용 번호. `[그룹]-[순번]`(섹션) + 선택적 하위 문자(`a, b, …`)로 표시 정보 단위. 예: `3-1` = 누적 주문 현황 섹션, `3-1b` = 그 안의 두 번째 표시 정보(총 주문 건수 카드). 섹션은 맨 윗줄에 한 문장 정의를 두고, 표시 정보(카드·값)는 하위 번호로 각각 넘버링한다. 패널은 하위 항목을 섹션 아래 들여쓰기로 렌더한다(`renderInspPanel`에서 `num` 끝 문자 유무로 판별).
- `title`: 패널에 표시되는 짧은 라벨.
- `group`: 그룹화 키.

### 그룹 정의 — `renderInspPanel` 내부
```js
var groups = {
  policy:'권한별 노출 정책',
  entry:'진입부',
  role:'문서별 열람 가능 역할',
  viewer:'문서 뷰어(열람)',
  exception:'예외 및 상태별 화면'
};
var order = ['policy','entry','role','viewer','exception'];
```
순서는 별도 `order` 배열로 지정 (객체 키 순서에 의존하지 않음).

### `POL_NAV` 맵 — 항목 클릭 시 화면 전환 시나리오
```js
var POL_NAV = {
  policy:  { sel:'[data-desc="policy"]',  go:function(cb){ showView('docs'); setTimeout(cb,80); } },
  rolecol: { sel:'[data-desc="rolecol"]', go:function(cb){ closeViewer(); closeNotice(); closeForm(); showView('docs'); setTimeout(cb,80); } },
  role:    { sel:'[data-desc="role"]',    go:function(cb){ closeViewer(); closeNotice(); showView('docs'); openForm('edit',1); setTimeout(cb,160); } },
  viewer:  { sel:'[data-desc="viewer"]',  go:function(cb){ vprep('none',cb,520); } },
  denied:  { sel:'[data-desc="denied"]',  go:function(cb){ vprep('denied',cb,160); } },
  // ...
};
```
- `sel`: 강조할 DOM 셀렉터.
- `go(cb)`: 해당 컴포넌트가 보이는 화면 상태로 만든 뒤 `cb` 실행. **이게 핵심 핸들러**.
  - 다른 모달·폼·뷰어가 열려 있다면 모두 닫고 시작.
  - 필요한 화면·모달·상태를 강제로 만든 뒤(`setForce`, `openDoc`, `openForm` 등) `setTimeout`으로 약간 대기시켜 DOM이 완성된 다음 `cb`.

---

## 3. 마크업 컨벤션

### 컴포넌트 측 (인덱스에 등록되는 모든 컴포넌트)
```html
<div class="viewer"
     data-desc="viewer"
     data-mk="tl"
     data-num="3-0"
     data-label="[3-0] 뷰어 기본 구조"
     data-body="[3-0] 뷰어 기본 구조&#10;&#10;· 모달로 직접 화면 위에 열림&#10;· 뷰어 내부 동작 제약&#10;  - 다운로드·인쇄 없음&#10;  - 이전/다음 문서 이동 없음">
  ...
</div>
```
- `data-desc`: `POLICIES`의 `key`와 일치.
- `data-num`: 번호. 시각화·검색용.
- `data-label`: 툴팁 상단 라벨.
- `data-body`: 툴팁·디스크립션 본문. 줄바꿈은 `&#10;`로.

### 패널 컨테이너
```html
<div class="insp-panel" id="inspPanel">
  <div class="ip-head" data-act="togglePanel">
    <div class="ip-headL">
      <span class="ip-title">정책 인덱스</span>
      <span class="ip-count" id="ipCount"></span>
    </div>
    <svg class="ip-chev" .../>
  </div>
  <p class="ip-desc">항목을 클릭하면 해당 화면으로 이동해 정책 위치를 짚어 줍니다. 요소를 우클릭해도 볼 수 있어요.</p>
  <div id="ipList"></div>
</div>
```

### `renderInspPanel`이 생성하는 항목 마크업
```html
<div class="ip-group">권한별 노출 정책</div>
<div class="ip-row" data-key="policy">
  <button class="ip-item" data-act="gotoPolicy" data-key="policy">
    <span class="ip-num">0-0</span>
    <span class="ip-label">권한 등급 구분</span>
    <svg class="ip-ic" .../>  <!-- chevron, 열렸을 때 90도 회전 -->
  </button>
  <div class="ip-detail">  <!-- detailHtml(body) 결과 -->
    <div class="ipd-l">· 역할 등급: 관리자 / 편집자 / 뷰어</div>
    <div class="ipd-l">  - UserProjectRole → 프로젝트별 부여</div>
    ...
  </div>
</div>
```

---

## 4. 핵심 함수

### `renderInspPanel()` — 패널 그리기
```js
function renderInspPanel() {
  var groups = { /* 그룹 라벨 맵 */ };
  var order = [ /* 그룹 표시 순서 */ ];
  var html = '';
  order.forEach(function(g){
    html += '<div class="ip-group">' + groups[g] + '</div>';
    POLICIES.filter(function(p){ return p.group === g; }).forEach(function(p){
      var el = document.querySelector('[data-desc="' + p.key + '"]');
      var body = el ? el.getAttribute('data-body') : '';
      html += '<div class="ip-row" data-key="' + p.key + '">' +
                '<button class="ip-item" data-act="gotoPolicy" data-key="' + p.key + '">' +
                  '<span class="ip-num">' + p.num + '</span>' +
                  '<span class="ip-label">' + p.title + '</span>' +
                  '<svg class="ip-ic" ...></svg>' +
                '</button>' +
                '<div class="ip-detail">' + detailHtml(body) + '</div>' +
              '</div>';
    });
  });
  $('ipList').innerHTML = html;
  $('ipCount').textContent = POLICIES.length + '개';
}
```
- `data-body`는 해당 컴포넌트에서 **직접 읽음** → SoT 단일화 (디스크립션이 한 곳에만 존재).
- 컴포넌트가 DOM에 항상 존재해야 함 (`display:none` 상태여도 OK).

### `detailHtml(body)` — `data-body` 텍스트 → HTML 변환
```js
// 한 줄의 선행 공백·리스트 마커("1. "·"- "·"· ")를 hanging indent 스타일로 환산.
// 마커 폭만큼 첫 줄을 당겨(text-indent 음수) 항목이 감싸일(wrap) 때 그 줄도
// 항목 텍스트 시작에 정렬되게 한다.
function lineIndentStyle(rawLine) {
  var lead = (rawLine.match(/^ */)[0] || '').length;
  var content = rawLine.slice(lead);
  if (content === '' || content.charAt(0) === '[') return { content: content, style: '' };
  var marker = (content.match(/^(?:\d+\.|[-·])\s+/) || [''])[0];
  var indent = lead + marker.length;
  if (indent === 0) return { content: content, style: '' };
  return { content: content, style: 'padding-left:' + indent + 'ch;text-indent:-' + marker.length + 'ch;' };
}

function detailHtml(body) {
  var ls = (body || '').split('\n');
  var o = '';
  ls.forEach(function(l){
    var r = lineIndentStyle(l);
    if (r.content === '') {
      o += '<div class="ipd-sp"></div>';      // 빈 줄 = 섹션 간격
    } else if (r.content.charAt(0) === '[') {
      o += '<div class="ipd-h">' + esc(r.content) + '</div>';  // [...] = 섹션 헤더
    } else {
      o += '<div class="ipd-l" style="' + r.style + '">' + esc(r.content) + '</div>';  // hanging indent
    }
  });
  return o;
}
```
- **hanging indent**: 선행 공백을 그대로 두지 않고 `padding-left`+음수 `text-indent`로 옮긴다 → 항목이 다음 줄로 감싸일 때 그 줄도 항목 텍스트 시작에 맞춰 정렬된다.
- **하지 말 것(과거 버그)**: `esc(l)`로 선행 공백을 보존하고 `white-space: pre-wrap`에만 의존하면, 감싸인 줄이 좌측 끝으로 돌아가 들여쓰기가 깨져 보인다.

### `gotoPolicy(key)` — 항목 클릭 핸들러
```js
function gotoPolicy(key) {
  var cfg = POL_NAV[key];
  if (!cfg) return;
  if (!inspect) toggleInspect();              // 설명 모드 강제 ON
  hideTip();
  var row = document.querySelector('.ip-row[data-key="' + key + '"]');
  var willOpen = row ? !row.classList.contains('open') : true;

  // 다른 row 모두 닫기
  Array.prototype.forEach.call(
    document.querySelectorAll('.ip-row'),
    function(r){ r.classList.remove('open'); }
  );
  if (!willOpen) return;                      // 같은 항목 재클릭 = 토글 close

  row.classList.add('open');
  try { row.scrollIntoView({ block:'nearest' }); } catch(_){}

  cfg.go(function(){
    var el = document.querySelector(cfg.sel);
    if (!el) return;
    try { el.scrollIntoView({ block:'center', behavior:'smooth' }); } catch(_){}
    pulseEl(el);
    el.classList.add('dt-sel');
    setTimeout(function(){ el.classList.remove('dt-sel'); }, 1800);
  });
}
```

### `pulseEl(el)` — 펄스 1회
```js
function pulseEl(el) {
  el.classList.remove('pol-pulse');
  void el.offsetWidth;                        // 리플로우 강제 → 애니메이션 재실행
  el.classList.add('pol-pulse');
  setTimeout(function(){ el.classList.remove('pol-pulse'); }, 1300);
}
```

### `showTipFor(el)` / 우클릭 핸들러 — 컴포넌트 직접 강조
```js
document.addEventListener('contextmenu', function(e){
  if (!inspect) return;
  var target = e.target.closest('[data-desc]');
  if (!target) return;
  e.preventDefault();
  hideTip();
  target.classList.add('dt-sel');
  // 디스크립션 박스 위치 계산 후 표시
  ...
});
```

### `hideTip()` — 강조 일괄 해제
```js
function hideTip() {
  box.style.display = 'none';
  Array.prototype.forEach.call(
    document.querySelectorAll('.dt-sel'),
    function(el){ el.classList.remove('dt-sel'); }
  );
  // 컬럼 특수 케이스 해제
  Array.prototype.forEach.call(
    document.querySelectorAll('.rc-active'),
    function(el){ el.classList.remove('rc-active'); }
  );
}
```

---

## 5. 핵심 CSS

### 패널 레이아웃
```css
.insp-panel {
  position: fixed; top: 58px; right: 16px; z-index: 900;
  width: min(300px, calc(100vw - 32px));
  max-height: calc(100dvh - 74px);
  overflow-y: auto;
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 12px; box-shadow: var(--lv2);
  padding: 14px; display: none;
}
body.inspect .insp-panel { display: block; }

/* 패널이 컨텐츠를 가리지 않도록 — ON 시 컨텐츠 영역을 패널 폭만큼 좁힌다 (필수).
   대상은 메인 컨텐츠 컨테이너(vanilla: .app-body / React: 메인 레이아웃·스크롤 래퍼).
   값 = 패널 width(300) + right(16) + 여백 ≈ 332px. */
body.inspect .app-body { padding-right: 332px; transition: padding-right 0.18s ease; }
@media (max-width: 760px) { body.inspect .app-body { padding-right: 0; } }

.ip-group { /* 그룹 헤더 */ }
.ip-row { /* 항목 행 */ }
.ip-item { /* 클릭 버튼 (번호 + 라벨 + chev) */ }
.ip-row.open .ip-ic { transform: rotate(90deg); color: var(--primary); }
.ip-detail { display: none; padding: 4px 10px 12px; }
.ip-row.open .ip-detail { display: block; }

.ipd-h  { font: 700 14px var(--sans); margin: 9px 0 3px; }   /* 소제목도 기본 14px */
.ipd-l  { font: 400 14px/1.55 var(--sans); white-space: pre-wrap; }  /* 기본 본문 14px · 들여쓰기는 detailHtml의 hanging indent(padding/text-indent)로 처리 */
.ipd-sp { height: 6px; }
```

### 컴포넌트 강조 (점선 → 실선 + 펄스)
```css
/* 표시: 점선 outline + 좌상단 넘버링 배지 */
body.inspect [data-desc] {
  position: relative;            /* 넘버링 배지(::before) 기준 */
  outline: 2px dashed var(--primary);
  outline-offset: -2px;
  border-radius: var(--r-sm);
  cursor: context-menu;
}
/* 좌상단 넘버링 배지 — data-num(예: "1-1")을 패널 항목 번호와 동일하게 표시.
   data-num은 컴포넌트 마크업에 정적으로 두거나, 패널 렌더 시 JS로 주입한다. */
body.inspect [data-desc][data-num]::before {
  content: "[" attr(data-num) "]";
  position: absolute; top: 0; left: 0; z-index: 3;
  background: var(--primary); color: #fff;
  font: 700 10px/1.5 var(--sans);
  padding: 1px 6px;
  border-radius: var(--r-sm) 0 6px 0;
  pointer-events: none;
}

/* 선택됨: 실선 + 안쪽 tint */
body.inspect [data-desc].dt-sel {
  outline-style: solid;
  box-shadow: inset 0 0 0 3px rgba(74,113,255,.18);
}

/* 펄스: 안쪽 영역만 한 번 차오름 */
@keyframes polPulse {
  0%   { box-shadow: inset 0 0 0 9999px rgba(74,113,255,.45); }
  100% { box-shadow: inset 0 0 0 9999px rgba(74,113,255,0); }
}
.pol-pulse { animation: polPulse 1.2s ease-out 1; border-radius: var(--r-sm); }
```

### 컬럼(테이블 열) 특수 케이스
일반 outline 방식은 분산된 요소에 동작하지 않으므로 별도 처리:
```css
body.inspect td.rc, body.inspect th.rc {
  position: relative;
  background: rgba(74,113,255,.06);
}
body.inspect td.rc::before, body.inspect th.rc::before {
  content: ''; position: absolute; inset: 0;
  border-left: 2px dashed var(--primary);
  border-right: 2px dashed var(--primary);
  pointer-events: none;
}
body.inspect th.rc::before { border-top: 2px dashed var(--primary); }
body.inspect tbody tr:last-child td.rc::before { border-bottom: 2px dashed var(--primary); }
body.inspect th[data-desc="rolecol"] { outline: none !important; }

/* 활성화: 실선 + 배경 펄스 */
body.inspect td.rc.rc-active, body.inspect th.rc.rc-active {
  background: rgba(74,113,255,.14);
  animation: rcPulse 1.2s ease-out 1;
}
body.inspect td.rc.rc-active::before, body.inspect th.rc.rc-active::before {
  border-left-style: solid; border-right-style: solid;
}
@keyframes rcPulse {
  0%   { background: rgba(74,113,255,.5); }
  100% { background: rgba(74,113,255,.14); }
}
```

JS에서는 `data-desc="rolecol"`이 선택될 때 모든 `td.rc, th.rc`에 `rc-active`를 같이 토글:
```js
if (el.getAttribute('data-desc') === 'rolecol') {
  Array.prototype.forEach.call(
    document.querySelectorAll('td.rc, th.rc'),
    function(c){ c.classList.add('rc-active'); }
  );
}
```

---

## 6. `data-body` 작성 규칙

디스크립션 본문은 **일관된 텍스트 컨벤션**으로 작성. detailHtml이 이를 파싱.

```
[3-3] 페이지 위치

[표시]
· 현재 페이지 / 전체 페이지
  - 예: 2/10
· 첫 진입은 항상 1페이지·맨 앞 (이어보기 없음)

[이동]
· 이전·다음 버튼 또는 페이지 번호 직접 입력
· 입력값 처리
  - 범위 밖 값 → 1~전체로 자동 보정
  - 숫자 아님·빈 값 → 현재 페이지 유지
```

규칙:
- 첫 줄: `[번호] 제목` (툴팁 라벨과 동일)
- 빈 줄: 섹션 구분 (`<div class="ipd-sp">`)
- `[...]`로 시작하는 줄: 섹션 헤더 (`<div class="ipd-h">`)
- `·`로 시작: 1차 항목
- 공백 2칸 + `-`로 시작: 2차 하위 항목 (들여쓰기)
- `→` 분기/결과는 같은 줄 또는 하위로
- HTML 속성에 넣을 때는 `\n`을 `&#10;`로, `"`를 `&quot;`로 인코딩

---

## 7. 함정 (Gotchas)

### ① 컨테이너 안쪽 누출
부모 컴포넌트가 `.pol-pulse` 될 때, **자식이 `background:transparent`**면 부모 inset 펄스 색이 안쪽 영역까지 비쳐서 의도와 같이 깜빡이는 것처럼 보임.
- 해결: 자식 요소에 부모와 같은 `background`를 명시적으로 부여하여 차단.
- 예: `.vh { background: var(--bg); }`, `.vfoot { background: var(--bg); }`

### ② 컬럼에 outline·box-shadow 펄스가 안 통함
테이블 컬럼은 분산된 셀(`td.rc`, `th.rc`)들로 구성되어, 단일 element 펄스 효과(outline / inset box-shadow)가 한 셀에만 적용되어 안쪽만 깜빡이는 식의 버그.
- 해결: 컬럼 전용 `rc-active` 클래스를 모든 셀에 토글, `background` 펄스로 전 셀 동시 효과.

### ③ 펄스 재실행
같은 element에 `.pol-pulse`를 다시 부여해도 애니메이션이 재시작되지 않음.
- 해결: `classList.remove` → `void el.offsetWidth` (리플로우 강제) → `classList.add` 순서.

### ④ 개조식 들여쓰기는 hanging indent로 처리 (감싸인 줄 정렬)
선행 공백을 그대로 보존하고 `white-space: pre-wrap`에만 의존하면, 항목이 길어져 다음 줄로 감싸일(wrap) 때 그 줄이 좌측 끝으로 돌아가 들여쓰기가 깨져 보인다.
```js
// ✗ 옛 방식 — 감싸인 줄이 좌측 끝으로 돌아감
o += '<div class="ipd-l">' + esc(l) + '</div>';           // 선행 공백만 보존
// ○ hanging indent — lineIndentStyle로 선행 공백·마커를 padding/text-indent로 옮김
var r = lineIndentStyle(l);
o += '<div class="ipd-l" style="' + r.style + '">' + esc(r.content) + '</div>';
```

### ⑤ POL_NAV의 `go(cb)` 대기 시간
화면 전환·모달 실행 직후 바로 `scrollIntoView`·펄스를 적용하면 DOM이 아직 안 그려져서 대상 누락.
- 모달 단순 실행: 80~160ms
- 모달 + 뷰어 + 문서 로딩: 520~1150ms (실패 상태 시뮬레이션은 더 길게)

### ⑥ `setTimeout` 해제 누락
선택된 요소가 화면 전환·다른 항목 클릭으로 사라져도 `dt-sel`/`rc-active`가 그대로 남는 경우 → `hideTip()`이 모든 잔존 강조를 일괄 제거하도록 처리.

---

## 8. 스킬 통합 전 체크리스트

- [ ] `POLICIES`, `POL_NAV` 데이터 모델을 프로토타입 단위로 정의 가능하게 노출.
- [ ] 각 컴포넌트에 `data-desc`, `data-num`, `data-label`, `data-body` 4종 attribute 부여.
- [ ] `renderInspPanel`을 DOM 렌더 후 한 번 호출 (`renderTable()` 등 모든 view 초기화 후).
- [ ] `body.inspect` 클래스로 설명 모드 토글 (패널 표시·컴포넌트 outline 등 일괄).
- [ ] 컨테이너 안쪽 transparent 누출 → 자식 background 점검.
- [ ] 분산 컴포넌트(테이블 컬럼·반복 셀)는 별도 active 클래스로 처리.
- [ ] `data-body` 작성 규칙을 디스크립션 SoT로 강제 (들여쓰기, 섹션 헤더, 빈 줄).
- [ ] `detailHtml`이 `lineIndentStyle`로 hanging indent 적용 (선행 공백·마커 → padding/text-indent). 감싸인 줄이 항목 시작에 정렬되는지 확인.
