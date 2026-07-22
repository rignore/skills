# 실행 명령 모음 (복붙 가능)

실행 경로는 둘이다. **`codex exec`**(CLI 내장 1회 실행 — 플러그인 불필요, 스크립트·체인에 적합)과
**companion**(플러그인 동봉 잡 매니저 — 잡 추적·리뷰·이관). 같은 Codex 엔진이라
세션 로그·인증·과금은 동일하다. 플러그인이 없거나 체인 자동화면 exec,
세션 안에서 잡 여러 개를 추적하면 companion.

## Phase 0 — 환경 점검

```bash
codex --version        # 400 "requires a newer version" 에러 시: codex update
codex login status     # "Logged in using ChatGPT" 확인
```

## A. `codex exec` 경로 (실증 2에서 사용)

```bash
# worktree 격리 (태스크 체인이면 태스크마다)
cd <작업리포> && git worktree add ../<리포>-t<N> -b ai/local-t<N>-<슬러그>
cd ../<리포>-t<N>
# 의존성 설치 (프로젝트별 — manager 예시: ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm ci --ignore-scripts)

# 위임 — SPEC 파일을 통째로 프롬프트에. Bash run_in_background: true로 감쌀 것
codex exec --sandbox workspace-write "$(cat <SPEC파일>)"

# 완료 후 순서: 검토자가 typecheck·테스트 직접 재실행 → 검토자가 커밋(pitfalls #7)
# → main 병합 → worktree 정리 → 다음 태스크는 갱신된 main에서 worktree를 딴다
```

## B. companion 경로 (실증 1에서 사용)

```bash
# companion 러너 경로
COMPANION=~/.claude/plugins/marketplaces/openai-codex/plugins/codex/scripts/codex-companion.mjs

# 서브커맨드 목록 (task에 --help 쓰지 말 것 — 스레드가 시작된다, pitfalls #4)
node "$COMPANION" --help

# [실행] 작업 위임 — 반드시 작업 리포 cwd에서 (Codex sandbox가 여기로 격리됨)
cd <작업리포>
node "$COMPANION" task --background --write --fresh "<자립 SPEC 참조 프롬프트>"
# 반환: task-xxxx job-id

# [상태] 폴링 (running이 사라질 때까지)
node "$COMPANION" status <job-id>
node "$COMPANION" status --all         # job-id 회수용 (adversarial-review job 찾을 때)

# [결과]
node "$COMPANION" result <job-id>

# [적대 검증] — 기동이 느려 2분 Bash timeout에 걸린다. run_in_background로 감싸고,
# 끊겨도 job은 떠 있으니 status --all로 review-... job-id를 회수해 폴링 (pitfalls #5)
node "$COMPANION" adversarial-review --background --scope working-tree "<검증 focus>"

# [취소]
node "$COMPANION" cancel <job-id>

# 폴링 루프 (run_in_background: true로 실행)
for i in $(seq 1 60); do
  s=$(node "$COMPANION" status <job-id> 2>/dev/null)
  echo "$s" | grep -q "| running |" || { echo "DONE"; break; }
  sleep 15
done
```

## C. 검증 도구 (Phase 3)

- **Claude evaluator**: Agent tool, `subagent_type: evaluator`. 입력에 명세·산출물·정답표(원본) 경로만 준다. **생성 맥락은 넘기지 않는다** (judge≠solver).
- **원본 무결성 확인 (git 아닌 대상)**: `find <원본dir> -type f -newermt "40 minutes ago" | grep -v /.git/` 결과가 비어야 미변경. (git repo가 아니면 `git status --porcelain`은 거짓 양성 — pitfalls #6)
- **검토 시작은 `git status -s`로**: `git diff --stat`은 untracked 신규 파일을 안 보여준다 (pitfalls #9a). grep 검사는 파일 실존 확인 후에 (pitfalls #9b).
- **Codex 로그** (hung 진단 등): `/var/folders/.../T/codex-companion/<리포>-<해시>/jobs/<job-id>.log`. `status`의 Log 줄에 절대경로가 찍힌다.

## D. 실행 증빙·사용량 확인

"Codex가 진짜 돌았나 / 한도가 왜 안 주나" 의심이 들 때. 두 경로 공통(같은 엔진이라 로그 위치 동일).

- **세션 로그**: `~/.codex/sessions/YYYY/MM/DD/rollout-<시각>-<uuid>.jsonl`. 첫 줄 `session_meta`에 `cwd`·`session_id`·시작 시각과 **`originator`**(실행 경로 — `codex_exec`=CLI 비대화 / `codex-tui`=터미널 대화형 / `Codex Desktop`=앱 / `Claude Code`=플러그인 경유).
- **토큰 집계**: 같은 파일의 `event_msg` 중 `token_count` 이벤트에 누적 사용량. 캐시 비중이 커서(실증 2의 T1: 총 40.3만 중 캐시 적중 36.2만, 91% — 실소비 약 4.1만) 작은 태스크는 구독 한도 표시가 눈에 띄게 움직이지 않는 게 정상이다.
- **삼각 검증** (실행 실재 확인): ① 서버 에러 응답이 있었으면 그 자체가 API 도달 증명 ② 산출 파일 mtime이 실행 시간 창과 일치 ③ 세션 로그 토큰 집계 존재. 셋이 맞으면 "돌았는데 표시가 안 움직인 것", 셋 다 없으면 실행 자체가 안 된 것.
- **인증 방식 확인** (한도 소모 주체): `~/.codex/auth.json`의 키 이름만 확인 (`auth_mode`·`tokens` 있고 `OPENAI_API_KEY` 비어 있으면 ChatGPT 구독 과금). 값은 출력하지 않는다.
