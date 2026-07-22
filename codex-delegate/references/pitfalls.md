# 함정 10건 — 이미 겪었다, 반복 금지

Phase 2 착수 전에 훑는다. 각 항목은 실증에서 실제로 밟았거나 밟을 뻔한 것이다.

1. **Codex adversarial-review는 대형 diff에서 hung.** 65파일 diff에서 실제 검사는 1분 30초에 끝났는데 이후 22분간 무활동으로 최종 findings를 못 냈다(23분 경과 후 취소). 1파일 diff는 완주했다. → 검증 대상 diff를 작게 쪼개고, Claude evaluator를 주 게이트로 둔다. adversarial-review는 보조.

2. **SPEC 설계 결함이 실행 결함으로 나타난다.** SPEC 예시가 파서로 읽을 수 없는 구조면 Codex가 그대로 재현해 산출물이 조용히 깨진다(원자 59% 소실 사례). → 목표 산출 형식을 파서로 검증 가능한 구조로 준다. `spec-guide.md` 규율 1.

3. **슬래시 커맨드는 모델이 직접 못 부른다.** `/codex:transfer`·`/codex:status` 등은 `disable-model-invocation: true`다. → companion.mjs를 Bash로 직접 호출한다(`commands.md`).

4. **`companion task`에 `--help`가 없다.** `task --help`를 치면 실제 Codex 스레드가 시작된다(인자를 프롬프트로 해석). → 서브커맨드 목록은 `companion --help`로 본다.

5. **`companion adversarial-review --background`가 2분 Bash timeout에 걸린다.** background인데도 기동이 느려 Bash가 2분에 끊긴다. 하지만 **job은 뜬다.** → `status --all`로 `review-...` job-id를 회수한 뒤 폴링한다. 이 명령은 `run_in_background: true`로 감싼다.

6. **git 무결성 검사가 거짓 양성을 낸다.** 대상이 git repo가 아니면 `git status --porcelain`이 빈 문자열을 반환하고 `[ -z "$(...)" ]`가 참이 돼 "unchanged"로 오판한다. → git repo가 아니면 `find <dir> -type f -newermt "<N> minutes ago"`로 최근 수정 파일을 확인한다.

7. **workspace-write 샌드박스는 worktree 커밋을 차단한다.** worktree의 git 메타데이터는 본 저장소(`<repo>/.git/worktrees/<name>/`)에 있는데 샌드박스 쓰기 허용 범위는 worktree 폴더뿐이라 `index.lock` 생성이 거부된다. Codex는 구현을 마치고 커밋만 실패한다. → SPEC에서 커밋 지시를 아예 빼고 "커밋은 검토자가 한다"로 역할을 고정한다.

8. **모델-CLI 버전 불일치가 400 에러로 나타난다.** `~/.codex/config.toml`의 model이 설치된 CLI보다 새 버전을 요구하면 API가 400을 반환하고 작업이 시작조차 안 된다. 증상만 보면 원인을 알기 어렵다. → Phase 0에서 `codex --version`을 확인하고, 400 "requires a newer version"이면 `codex update`(standalone 자체 업데이터).

9. **검토 스크립트 자체의 함정 2개.**
   - (a) `git diff --stat`은 untracked 신규 파일을 보여주지 않는다. Codex가 새 파일을 만들었으면 diff만 보고 "누락"으로 오판한다. → 검토는 `git status -s`로 전체 파일 목록부터 확인한다.
   - (b) `grep <패턴> <파일> || echo "✅ 없음"` 패턴은 **파일이 존재하지 않아도 ✅를 출력한다** (grep이 파일 부재로 실패해도 nonzero). → 파일 실존을 먼저 확인하고 grep한다.

10. **`codex exec`가 기동 직후 hung — 원격 MCP 서버가 원인일 수 있다** (2026-07-21 실증).
   세션 로그에 `task_started` 하나만 남기고 130분 무활동(도구 호출 0·토큰 0·파일 변경 0),
   프로세스는 살아 있어 완료/실패 알림이 영원히 안 온다. `~/.codex/config.toml`에 등록된
   원격 MCP 서버(url 타입)가 접속을 붙잡으면 기동이 막히는 것으로 추정 — 같은 설정으로
   직전 3회는 통과했으므로 **비결정적**이다. 1번 항목(adversarial-review hung)과는 다른
   유형이다(그쪽은 검사 후 멈춤, 이쪽은 시작 전 멈춤).
   → 대응 2개를 함께 쓴다.
   - **예방**: 태스크에 MCP가 불필요하면 `-c 'mcp_servers={}'`로 끄고 실행한다.
   - **탐지(필수)**: 위임 직후 **활동 감시기**를 함께 건다 — `~/.codex/sessions/`의 해당
     세션 로그에서 도구 호출(function_call·local_shell_call) 발생 여부를 30초 간격으로
     폴링, 8분간 0이면 STALL 판정 후 kill·재기동. "완료 알림 대기"만으로는 hung을 영원히
     못 잡는다.
