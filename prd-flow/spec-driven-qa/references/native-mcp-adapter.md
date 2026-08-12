# Android Native MCP Adapter 계약

대상 독자: `native-android` runner provider 구현자와 Android QA 인프라 운영자

목적: 외부 Demo Video MCP의 Appium UiAutomator2 실행 흐름을 `runbook-v1`에 연결한다. 이 adapter는 외부 MCP를 호출하며 MCP runtime 코드를 범용 core에 복사하지 않는다.

이 문서는 외부 adapter 경계와 P3(Android MCP adapter) 실행 계약을 정의한다. `validate-contracts.py`는 `native-mcp-binding-v1`을 기계 검증한다. `compile-android-runbook.mjs`, `run-android-mcp.mjs`, `mcp-stdio-client.mjs`는 runtime 코드를 복사하지 않고 외부 MCP를 호출한다.

## 목차

1. 지원 범위와 경계
2. Adapter 입력과 local binding
3. MCP server identity와 capability discovery
4. MCP tool lifecycle과 최소 입출력
5. Artifact 등록
6. Runtime과 device
7. Runbook action mapping
8. Locator 선택과 실행
9. Mutation 승인과 격리
10. Evidence 수집
11. 보안과 redaction
12. iOS 방어와 종료 상태
13. 전체 action mapping 예시
14. P3(Android MCP adapter) MVP 구현과 실행
15. 적합성 기준

## 1. 지원 범위와 경계

| 항목 | 현재 계약 |
| --- | --- |
| Platform | Android native app |
| Automation backend | Appium UiAutomator2 |
| Device | 로컬 Android Emulator |
| Install artifact | APK |
| Appium endpoint | 로컬 `127.0.0.1` |
| iOS | contract only, 실행은 `unsupported` |
| Android physical device | `unsupported` |
| Android App Bundle | AAB는 `unsupported` |
| Remote device farm | `unsupported` |

Responsive mobile web은 이 adapter의 대상이 아니다. `target.platform=mobile_web`은 Playwright device context에서 실행해야 한다.

iOS `.app.zip`을 등록할 수 있다는 외부 MCP 기능은 iOS 실행 지원을 뜻하지 않는다. XCUITest backend가 없으므로 adapter는 iOS artifact를 설치하거나 앱을 실행하지 않는다. 정상 iOS contract와 잘못된 실행 가능 요청의 처리는 12절에서 분리한다.

## 2. Adapter 입력과 local binding

Adapter는 아래 두 입력을 받는다.

1. 검증과 승인이 끝난 `runbook-v1`
2. project runtime이 제공한 local binding

Android runbook은 아래 값을 가져야 한다.

```json
{
  "schema_version": "runbook-v1",
  "runbook_state": "preflight",
  "method": "native",
  "execution": {"enabled": true},
  "target": {
    "platform": "android",
    "device": "emulator",
    "artifact_type": "apk"
  },
  "runner_provider": "native-android"
}
```

Local binding은 `native-mcp-binding-v1` JSON이다. 이 파일의 canonical SHA-256을 `runner-request-v1.runtime_binding.sha256`에 저장한다.

최소 필드는 다음과 같다.

| Field | 요구사항 |
| --- | --- |
| `schema_version` | 반드시 `native-mcp-binding-v1`이다. |
| `binding_id` | Binding revision의 불변 ID다. |
| `server` | MCP server identity와 contract version이다. |
| `server.launch` | Absolute executable path, string argument 목록, 선택형 absolute working directory다. |
| `server.runtime_source` | 실행 코드 전용 directory tree의 절대 경로, canonical source digest, 파일 수, byte 합계다. |
| `capabilities` | Capability discovery snapshot과 schema hash다. |
| `artifact.local_path` | 로컬 APK의 절대 경로다. |
| `artifact.type` | 반드시 `apk`다. |
| `artifact.expected_sha256` | 승인된 APK의 SHA-256이다. |
| `readiness.java` | Absolute `JAVA_HOME`, exact `bin/java` path, executable SHA-256을 고정한다. |
| `readiness.apk_verifier` | Absolute `apksigner` path, verifier name, executable SHA-256을 고정한다. |
| `package_id` | 실행할 Android application ID다. |
| `device.runtime` | 반드시 `emulator`다. |
| `device.avd` | 사용할 Android Virtual Device 이름이다. |
| `device.udid` | 선택한 online Emulator serial이다. 값이 있으면 `emulator-`로 시작해야 한다. |
| `device.device_name` | Appium capability에 기록할 Emulator 이름이다. |
| `device.platform_version` | Android platform version 문자열이다. |
| `device.orientation` | `portrait` 또는 `landscape`다. |
| `device.language`, `device.locale` | 실행 locale을 고정한다. |
| `device.reset_policy` | MCP 입력 값인 `clean` 또는 `preserve`다. |
| `appium.server_url` | Credential이 없는 local HTTP URL이다. |
| `appium.driver` | 반드시 `uiautomator2`다. |
| `execution.max_duration_seconds` | `10..180` 범위에서 고정한다. |
| `execution.poll_interval_ms` | `50..5000` 범위의 terminal-state polling 간격이다. |
| `execution.request_timeout_ms` | 선택형 MCP request timeout이며 `1000..120000` 범위다. |

`device.avd`와 `device.udid` 중 하나 이상은 필수다. 여러 Emulator가 online이면 `device.udid`도 필수다. Adapter는 선택한 실제 serial을 output subject에 기록한다.

아래는 완전한 합성 sample binding이다. 특정 사용자 경로나 실제 앱 정보를 포함하지 않는다.

```json
{
  "schema_version": "native-mcp-binding-v1",
  "binding_id": "sample-android-emulator-r1",
  "server": {
    "name": "demo-video-mcp",
    "version": "1.0.0",
    "protocol_version": "2025-06-18",
    "transport": "stdio",
    "executable_sha256": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "runtime_source": {
      "kind": "directory_tree",
      "root_path": "/absolute/external-provider/src/external_mcp_server",
      "source_tree_sha256": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "file_count": 12,
      "total_bytes": 4096
    },
    "contract_version": "native-scenario-v1",
    "launch": {
      "executable_path": "/absolute/runtime/python",
      "arguments": ["-m", "external_mcp_server"],
      "working_directory": "/absolute/external-provider"
    }
  },
  "capabilities": {
    "discovered_at": "2026-08-01T01:00:00Z",
    "tools_list_sha256": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "native_scenario_schema_sha256": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "required_tools": [
      "get_native_video_scenario_schema",
      "register_native_app",
      "get_native_runtime_status",
      "inspect_native_app",
      "create_native_video_job",
      "preflight_video_job",
      "approve_video_job",
      "start_video_job",
      "get_video_job"
    ]
  },
  "artifact": {
    "type": "apk",
    "local_path": "/absolute/path/to/test-app.apk",
    "expected_sha256": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
  },
  "readiness": {
    "java": {
      "home_path": "/absolute/jdk",
      "executable_path": "/absolute/jdk/bin/java",
      "executable_sha256": "sha256:1111111111111111111111111111111111111111111111111111111111111111"
    },
    "apk_verifier": {
      "verifier": "apksigner",
      "executable_path": "/absolute/android-sdk/build-tools/35.0.0/apksigner",
      "executable_sha256": "sha256:2222222222222222222222222222222222222222222222222222222222222222"
    }
  },
  "package_id": "org.example.qasample",
  "device": {
    "runtime": "emulator",
    "avd": "qa-sample-api-35",
    "udid": "emulator-5554",
    "device_name": "qa-sample-emulator",
    "platform_version": "35",
    "orientation": "portrait",
    "language": "en",
    "locale": "US",
    "reset_policy": "clean"
  },
  "appium": {
    "server_url": "http://127.0.0.1:4723",
    "driver": "uiautomator2"
  },
  "execution": {
    "max_duration_seconds": 180,
    "poll_interval_ms": 500,
    "request_timeout_ms": 30000
  }
}
```

Local binding에도 password, token, signing key, APK bytes, Base64 artifact를 넣으면 안 된다. `readiness.apk_verifier`는 공개 verifier executable만 고정하며 certificate, keystore, signing key를 저장하지 않는다. 인증이 필요한 MVP 실행은 사용자가 Emulator에서 수동 로그인한 다음 `reset_policy=preserve`를 사용한다.

`server.runtime_source.root_path`는 외부 MCP의 실제 실행 source만 담은 전용 directory를 가리킨다. Repository root, filesystem root, virtual environment, runtime data, build artifact, credential file을 포함하면 안 된다. Digest manifest는 각 regular file의 NFC-normalized relative path, byte 수, SHA-256을 정렬한 `runtime-source-tree-v1` projection이다. Symbolic link, special file, 빈 directory tree는 거부한다. 절대 경로 자체는 source digest에 포함하지 않으므로 동일 source를 다른 local path로 옮겨도 digest는 유지된다. Capability discovery 전후의 tree identity가 달라지면 binding 생성을 거부한다. Python source를 직접 실행할 때는 `PYTHONDONTWRITEBYTECODE=1`처럼 bytecode cache 생성을 막고 source directory를 불변 상태로 유지한다.

`preserve`는 로그인 상태를 보존하지만 초기 상태 재현성을 보장하지 않는다. Adapter는 MCP 입력값인 `clean` 또는 `preserve`와 Emulator 식별자를 `runner-output-v1.subject.native_runtime`에 기록해야 한다.

## 3. MCP server identity와 capability discovery

Adapter는 tool 호출 전에 MCP `initialize`와 `tools/list` 결과를 binding과 대조한다.

`initialize` 응답은 최소한 아래 shape를 가져야 한다.

```json
{
  "protocolVersion": "2025-06-18",
  "capabilities": {"tools": {}},
  "serverInfo": {"name": "demo-video-mcp", "version": "1.0.0"}
}
```

Adapter는 아래 값을 canonical JSON SHA-256으로 고정한다.

- `tools/list`에서 tool name, input schema, output schema만 선택한 projection
- `get_native_video_scenario_schema`가 반환한 `schema`
- 실행할 MCP launcher executable의 digest
- 실행할 MCP runtime source directory tree의 digest, 파일 수, byte 합계

Server name, version, protocol version, executable hash, runtime source tree identity, tools-list hash, Native Scenario schema hash 중 하나라도 binding과 다르면 job을 만들지 않는다. 이 경우 `runner-output-v1.execution.status=not_started`와 `contract` error를 반환한다.

Capability discovery는 아래 required tool 아홉 개가 모두 있는지 확인해야 한다.

- `get_native_video_scenario_schema`
- `register_native_app`
- `get_native_runtime_status`
- `inspect_native_app`
- `create_native_video_job`
- `preflight_video_job`
- `approve_video_job`
- `start_video_job`
- `get_video_job`

Adapter는 발견한 schema에 없는 argument를 보내거나 누락 tool을 다른 tool로 대체하면 안 된다.

## 4. MCP tool lifecycle과 최소 입출력

Adapter는 외부 MCP를 아래 순서로 호출한다. Mutation approval이 provider `plan_hash`를 요구하므로 preflight와 실행은 서로 다른 명시적 단계다.

1. MCP process를 시작하기 전에 binding에 고정된 JDK와 `apksigner` hash를 대조하고 APK 서명을 검증한다.
2. `get_native_video_scenario_schema`로 현재 Native Scenario 입력 계약을 확인한다.
3. `register_native_app`으로 APK를 등록한다.
4. `get_native_runtime_status`로 runtime과 Emulator를 점검한다.
5. locator inventory가 필요하고 앱 실행 효과를 사용자가 승인한 경우에만 `inspect_native_app`을 호출한다.
6. `runbook-v1.steps`를 Native Scenario step으로 변환한다.
7. `create_native_video_job`으로 artifact와 변환한 scenario를 고정한다.
8. `preflight_video_job`으로 runtime, artifact hash, provider plan hash, mutation step을 확인한다.
9. Preflight-only 실행은 provider `plan_hash`, mutation step ID, artifact hash, JDK·APK verification record를 `native-mcp-preflight-v1`으로 반환하고 종료한다.
10. 외부 승인 시스템이 runbook plan hash와 provider plan hash를 결합한 승인 기록을 만든다.
11. 승인 기록이 새 job의 preflight 결과와 정확히 일치할 때만 `approve_video_job`을 호출한다.
12. `start_video_job`을 호출하고 `get_video_job`으로 terminal state까지 polling한다.
13. step result와 adapter가 수집한 구조화된 evidence를 `runner-output-v1`으로 변환한다.

아래 표는 MCP content wrapper를 해석한 뒤의 logical JSON payload 최소 shape다. Response에 필드가 없거나 type이 다르면 adapter는 contract error로 종료한다.

| Tool | Request 최소 shape | Response 최소 shape |
| --- | --- | --- |
| `get_native_video_scenario_schema` | `{}` | `{schema: object}`이며 schema가 Android platform과 지원 action을 닫힌 enum으로 정의한다. |
| `register_native_app` | `{platform:"android", path:string}` | `{artifact:{artifact_id,platform,format,sha256,size_bytes}, execution_support:{android,ios}}` |
| `get_native_runtime_status` | `{device:{runtime,avd?,udid?,device_name?,platform_version?,orientation,language?,locale?}}` | `{backend:"native-android",ready:boolean,checks:[{name,status,details}],connected_devices,available_avds}` |
| `inspect_native_app` | `{artifact_id,package_id,device,reset_policy,include_text,maximum_items,include_screenshot,confirm_app_launch}` | `{schema_version,trust,platform,package_id,device,inventory,artifact:{artifact_id,sha256}}` |
| `create_native_video_job` | `{scenario:object}` | `{job_id,state,plan_hash,artifacts}` |
| `preflight_video_job` | `{job_id:string}` | `{job:{job_id,state,plan_hash},preflight:{job_id,backend,plan_hash,checks,runtime,mutations,requires_approval,passed}}` |
| `approve_video_job` | `{job_id,plan_hash,approved_step_ids,confirm_external_changes:true}` | `{job_id,state,plan_hash,artifacts}` |
| `start_video_job` | `{job_id,plan_hash}` | `{job_id,state,plan_hash,artifacts}` |
| `get_video_job` | `{job_id}` | `{job_id,state,plan_hash,artifacts,manifest?}` |

`inspect_native_app` request는 기본적으로 `include_text=false`, `include_screenshot=false`를 사용한다. `confirm_app_launch=true`는 사용자가 설치·launch network effect를 승인한 뒤에만 전달한다.

MCP tool 이름에 `video`가 포함되어도 영상은 QA oracle이 아니다. 현재 외부 worker가 MP4를 생성하면 adapter는 이를 diagnostic attachment로만 분리한다.

Adapter는 자체 Appium session, artifact store 또는 worker를 범용 core에 복제하면 안 된다. 외부 MCP contract가 부족하면 MCP extension이나 별도 external provider를 추가하고 core에는 호출 경계만 둔다.

Adapter는 tool lifecycle과 response 변환에 LLM을 사용하면 안 된다. Tool request, response validation, polling, evidence 변환은 저장된 runbook과 binding만으로 결정해야 한다.

## 5. Artifact 등록

`register_native_app` 호출은 아래 입력만 사용한다.

```json
{
  "platform": "android",
  "path": "/absolute/path/to/test-app.apk"
}
```

Adapter는 호출 전에 아래 조건을 확인해야 한다.

- 경로가 절대 경로다.
- file extension과 승인된 artifact type이 `apk`다.
- 실제 파일 SHA-256이 `artifact.expected_sha256`과 같다.
- Binding에 고정된 `JAVA_HOME/bin/java`가 `java -version`을 성공하고, exact `apksigner verify --print-certs`가 signer certificate를 한 건 이상 보고한다.
- 파일이 AAB, APK bytes, Base64 string 또는 signing material이 아니다.

외부 MCP는 APK를 private storage에 복사하고 artifact ID와 SHA-256으로 고정해야 한다. Private copy 권한은 소유자만 읽고 쓸 수 있는 `0600`이어야 한다. Adapter는 MCP가 반환한 artifact hash와 실행 전 hash를 대조한다.

Artifact hash가 다르면 설치하거나 실행하지 않는다. 이 경우 `execution.status=not_started`와 artifact hash blocker 후보를 반환한다.

## 6. Runtime과 device

`get_native_runtime_status`는 최소한 아래 항목을 점검해야 한다.

- `adb`
- Android Emulator와 지정 AVD
- Appium server
- UiAutomator2 driver
- 현재 외부 worker가 녹화를 강제하는 동안 필요한 FFmpeg

Adapter는 dependency를 자동 설치하거나 원격 Appium server로 우회하면 안 된다. 필요한 runtime이 없으면 `execution.status=not_started`와 누락 runtime blocker 후보를 반환한다.

Device는 `runtime=emulator`여야 한다. `udid`를 지정한다면 `emulator-` prefix를 가진 serial만 허용한다. Adapter는 physical device serial을 거부한다.

실행 결과에는 다음 device 정보를 남긴다.

- AVD와 Emulator serial
- Android platform version
- orientation, language, locale
- reset policy
- Appium과 UiAutomator2 version

## 7. Runbook action mapping

QA adapter는 아래 여덟 action만 지원한다. `provider_args`는 compile이 끝난 literal object다. `_ref`, environment substitution, locator candidate 배열을 포함하면 안 된다.

| Runbook `action` | Required `provider_args` | Native Scenario `action` |
| --- | --- | --- |
| `launch` | `{hold_ms: integer}` | `{type:"launch"}` |
| `wait_for` | `{locator:{by,value,nth?},state:enum["present","absent"],hold_ms:integer}` | `{type:"wait_for",target:<locator>,state:<state>}` |
| `tap` | `{locator:{by,value,nth?},hold_ms:integer}` | `{type:"tap",target:<locator>}` |
| `fill` | `{locator:{by,value,nth?},value:string,hold_ms:integer}` | `{type:"fill",target:<locator>,value:<value>}` |
| `press_key` | `{key:enum["BACK","ENTER","HOME","TAB"],hold_ms:integer}` | `{type:"press_key",key:<key>}` |
| `back` | `{hold_ms:integer}` | `{type:"back"}` |
| `swipe` | `{direction:enum["up","down","left","right"],percent:number,hold_ms:integer}` | `{type:"swipe",direction:<direction>,percent:<percent>}` |
| `pause` | `{milliseconds:integer,hold_ms:integer}` | `{type:"pause",milliseconds:<milliseconds>}` |

`percent`는 `0.1..1.0`, `milliseconds`와 `hold_ms`는 `0..30000` 범위다. `fill.value`는 compile 시점에 확정한 비민감 fixture 값이어야 한다.

공통 field는 아래와 같이 mapping한다.

| Runbook field | Native Scenario field | 규칙 |
| --- | --- | --- |
| `id` | `id` | 변경하지 않는다. |
| `description` | `title` | 사람이 preflight에서 확인할 수 있는 문장으로 보존한다. |
| `timeout_ms` | `timeout_ms` | `1..120000` literal을 그대로 전달한다. |
| `provider_args.hold_ms` | `hold_ms` | Literal을 그대로 전달한다. |
| `retry_policy` | `retry_policy` | `safe` 또는 `never`를 그대로 전달한다. |
| `mutation` | `effects`, `approval` | 9절의 mutation mapping을 따른다. |
| `provider_defaults_version` | Adapter audit metadata | MCP step에는 넣지 않지만 runner output에 보존한다. |

첫 step은 정확히 한 번의 `launch`여야 한다. Adapter가 다른 위치에 launch를 삽입하거나 생략하면 안 된다. 좌표 기반 tap과 screenshot action은 공통 QA mapping에 포함하지 않는다.

`wait_for present|absent`는 Android MVP의 기본 deterministic UI oracle이다. Step 성공만으로 backend 상태를 증명하지 않는다. 저장, 전송, 결제처럼 backend mutation이 있는 기능은 API, DB 또는 integration test evidence를 별도로 수집해야 한다.

## 8. Locator 선택과 실행

Locator 우선순위는 아래 순서로 고정한다.

1. `accessibility_id`
2. `id`
3. `text`
4. `class_name`
5. `xpath`

Runbook Compiler는 inspection inventory와 versioned project config를 대조하고 아래 우선순위에서 사용할 수 있는 첫 locator 하나를 선택한다. 선택한 literal `{by,value,nth?}`만 `provider_args.locator`에 저장한다. 후보 목록과 `value_ref`는 저장하지 않는다.

Adapter는 runbook에 고정된 locator 하나만 Native Scenario target으로 전달한다. 해당 locator가 0개 또는 여러 개로 해석되더라도 낮은 우선순위 locator, text, XPath 또는 좌표로 fallback하면 안 된다. `xpath`는 Compiler가 더 높은 우선순위 locator가 없음을 확인한 경우에만 선택할 수 있다.

좌표 tap은 금지한다. Locator가 0개 또는 여러 개로 해석되어 runbook의 고정 `nth`로 해결할 수 없으면 해당 step을 `error`로 끝내고 `locator_result`를 남긴다.

`inspect_native_app`은 resource ID, accessibility label, class와 locator 후보만 수집한다. UI text는 기본적으로 제외한다. 필요한 경우에도 민감 정보가 없다는 승인을 받은 범위만 수집한다.

Inspection은 앱을 설치하고 실행하므로 read-only가 아니다. 앱 launch가 외부 API를 호출할 수 있다는 사실을 사용자에게 알리고 명시적 승인을 받은 뒤 `confirm_app_launch=true`로 호출해야 한다. Screenshot 수집은 기본 `false`다.

## 9. Mutation 승인과 격리

Android에서는 아래 action을 최소 `potential` mutation으로 분류한다.

- `launch`
- `tap`
- `fill`
- `press_key`
- `back`

`swipe`가 pagination, refresh 또는 외부 요청을 유발할 수 있으면 `potential` 이상으로 분류한다. Adapter는 runbook보다 mutation 등급을 낮추면 안 된다.

Mutation step mapping은 다음과 같다.

| `runbook.steps[].mutation` | Native `effects` | Native `approval` | Native `retry_policy` |
| --- | --- | --- | --- |
| `none` | `["local_read"]` | `none` | `safe` 또는 고정된 `never` |
| `potential` | `["potential_mutation"]` | `required` | `never` |
| `confirmed` | `["potential_mutation"]` | `required` | `never` |

Adapter는 `preflight_video_job` 결과에서 exact mutation step ID와 provider `plan_hash`를 읽는다. 아래 조건을 모두 충족할 때만 `approve_video_job`을 호출한다.

- `runbook.integrity.plan_sha256`이 승인 기록의 runbook plan hash와 같다.
- preflight의 provider `plan_hash`가 승인 기록의 provider plan hash와 같다.
- preflight mutation step ID가 `mutation_policy.approval_scope` 및 승인 기록의 step ID와 같다.
- 승인 환경이 현재 격리 환경과 같다.
- 승인 기록이 만료되지 않았다.
- Runbook이 `runbook_state=executable`이다. `runbook_state=preflight`는 `approval_ref=null`이어야 하며 `approve_video_job`과 `start_video_job`을 호출할 수 없다.

`approve_video_job`의 `confirm_external_changes=true`는 위 승인 기록을 검증한 뒤에만 설정한다. 실행 agent의 자기 승인이나 자연어 확인은 승인 기록을 대신할 수 없다.

CI에서 mutation runbook을 재생하려면 위 값을 결합한 immutable approval record가 먼저 저장되어 있어야 한다. 기록이 없거나 값이 다르면 `execution.status=not_started`와 approval blocker 후보를 반환한다.

Mutation action은 실패하거나 worker가 중단되어도 자동 재시도하지 않는다.

`fixture.destructive=true`인 runbook은 `fixture.environment=isolated`일 때만 실행한다. 오류와 경계 상태는 fixture, mock, seed script 또는 test endpoint로 만든다. 운영 데이터를 직접 수정해 상태를 만들면 안 된다.

## 10. Evidence 수집

Adapter는 아래 구조화된 evidence를 수집한다.

| Evidence kind | 내용 |
| --- | --- |
| `structured_log` | step 시작·종료, status, error, elapsed time |
| `locator_result` | locator type, match count, 선택된 element의 sanitization된 속성 |
| `ui_hierarchy` | oracle에 필요한 node만 남긴 sanitization된 hierarchy |
| `android_logcat` | 실행 시간 범위의 crash, exception, 관련 application log |
| `api_state`, `db_state` | 허용된 test interface가 반환한 backend 상태 |
| `build_hash`, `artifact_hash` | build reference와 등록 APK SHA-256 |

각 evidence item은 `result-v1`의 ID, kind, 수집 시각, producer, SHA-256, `redactions`를 포함해야 한다. Payload는 `record`에, result-relative file은 `artifact_ref`에 두며 두 필드 중 정확히 하나만 사용한다.

현재 외부 MCP에서 즉시 재사용할 수 있는 기본 증거는 Native Scenario의 step result와 `wait_for present|absent` 결과다. UI hierarchy snapshot이나 logcat이 필요한 oracle인데 외부 MCP가 이를 반환하지 않으면 adapter가 성공으로 간주하면 안 된다. 필요한 provider extension이 없으면 `missing_evidence`에 기록하고 Judge가 `insufficient_evidence`를 판정하게 한다.

Screenshot과 MP4는 선택형 diagnostic attachment다. 이 파일은 evidence registry에 넣지 않으며 Pass 판정에 쓰지 않는다.

## 11. 보안과 redaction

Adapter는 tool argument, log, UI hierarchy, result, manifest에 아래 값을 기록하면 안 된다.

- password와 token
- session cookie와 authorization header
- signing key
- APK file bytes와 Base64 artifact
- 사용자가 입력한 민감 정보

`fill`은 비민감 fixture 값만 받을 수 있다. 인증 정보가 필요한 경우 MCP action으로 입력하지 않고 수동 로그인한 Emulator 상태를 사용한다.

UI hierarchy와 logcat은 수집 직후 redaction한다. 원문에 민감값이 포함되면 artifact로 저장하지 않고 redaction 사실과 제거한 field category만 기록한다.

## 12. iOS 방어와 종료 상태

### 12.1 정상 iOS contract

정상 iOS scenario는 아래 조건을 모두 만족한다.

- `method=native`
- `target.platform=ios`
- `target.device=simulator`
- `target.artifact_type=app_zip`
- `runner_provider=native-ios`
- `execution.enabled=false`

Validator는 이 scenario를 contract로 허용한다. Downstream 실행 요청이 들어오면 dispatcher는 trace-only `runbook-v1`과 `runner-output-v1`을 만들 수 있지만 어떤 MCP tool도 호출하면 안 된다. Output은 아래 값을 가져야 한다.

- `execution.status=not_started`
- `errors[].category=unsupported`
- non-empty `unsupported_reason`
- 빈 `step_results`와 `evidence`

Independent Judge는 이 observation을 `unsupported`로 판정한다.

### 12.2 잘못된 iOS 실행 가능 요청

`target.platform=ios`이면서 `execution.enabled=true`인 scenario는 contract error다. Validator가 runbook compile 전에 거부해야 한다.

잘못된 요청이 validation을 우회해 Android adapter에 도달해도 adapter는 `register_native_app`, `get_native_runtime_status`, `inspect_native_app`, job tool을 호출하면 안 된다. 방어적으로 `execution.status=not_started`, `errors[].category=unsupported`, `unsupported_reason="native-ios provider is not implemented"`를 반환한다.

Android physical device, AAB, remote Appium 요청도 validation 단계에서 거부한다. Adapter까지 도달하면 같은 방식으로 tool을 호출하지 않고 unsupported capability를 기록한다.

### 12.3 Android 종료 상태

| 상황 | `execution.status` | 추가 정보 | 최종 verdict 후보 |
| --- | --- | --- | --- |
| Android Emulator와 APK로 실행 완료 | `completed` | 구조화된 evidence | Judge가 `pass`, `fail`, `conflict`, `insufficient_evidence` 중 판정 |
| APK hash, runtime, 승인, fixture isolation 문제로 시작하지 못함 | `not_started` | blocker 후보 | `blocked` |
| 실행 도중 environment 문제로 완료하지 못함 | `partial` | blocker 후보 | `blocked` |
| 실행은 끝났지만 필요한 hierarchy, logcat, API·DB 상태가 없음 | `completed` | missing evidence 후보 | `insufficient_evidence` |

App crash나 locator 불일치가 제품 동작의 관측 결과라면 environment blocker로 바꾸면 안 된다. 구조화된 crash 또는 locator evidence를 남기고 Judge가 expected와 대조하게 한다.

## 13. 전체 action mapping 예시

아래 합성 sample은 지원 action 여덟 개의 frozen runbook step을 모두 보여준다. 실제 project selector나 계정을 포함하지 않는다.

```json
[
  {
    "id": "launch-app",
    "action": "launch",
    "description": "Launch the approved APK",
    "mutation": "potential",
    "arguments": null,
    "provider_args": {"hold_ms": 800},
    "timeout_ms": 30000,
    "retry_policy": "never",
    "max_attempts": 1,
    "provider_defaults_version": "native-android-defaults-v1"
  },
  {
    "id": "wait-for-sample-control",
    "action": "wait_for",
    "description": "Wait for the sample control",
    "mutation": "none",
    "arguments": null,
    "provider_args": {
      "locator": {
        "by": "accessibility_id",
        "value": "qa-sample-control"
      },
      "state": "present",
      "hold_ms": 800
    },
    "timeout_ms": 10000,
    "retry_policy": "safe",
    "max_attempts": 1,
    "provider_defaults_version": "native-android-defaults-v1"
  },
  {
    "id": "tap-sample-control",
    "action": "tap",
    "description": "Tap the sample control",
    "mutation": "potential",
    "arguments": null,
    "provider_args": {
      "locator": {"by": "id", "value": "org.example.qasample:id/sample_action"},
      "hold_ms": 800
    },
    "timeout_ms": 10000,
    "retry_policy": "never",
    "max_attempts": 1,
    "provider_defaults_version": "native-android-defaults-v1"
  },
  {
    "id": "fill-sample-field",
    "action": "fill",
    "description": "Fill a non-sensitive sample value",
    "mutation": "potential",
    "arguments": null,
    "provider_args": {
      "locator": {"by": "accessibility_id", "value": "qa-sample-field"},
      "value": "sample-value",
      "hold_ms": 800
    },
    "timeout_ms": 10000,
    "retry_policy": "never",
    "max_attempts": 1,
    "provider_defaults_version": "native-android-defaults-v1"
  },
  {
    "id": "submit-sample-key",
    "action": "press_key",
    "description": "Submit the sample value with Enter",
    "mutation": "potential",
    "arguments": null,
    "provider_args": {"key": "ENTER", "hold_ms": 800},
    "timeout_ms": 10000,
    "retry_policy": "never",
    "max_attempts": 1,
    "provider_defaults_version": "native-android-defaults-v1"
  },
  {
    "id": "return-from-sample",
    "action": "back",
    "description": "Return from the sample screen",
    "mutation": "potential",
    "arguments": null,
    "provider_args": {"hold_ms": 800},
    "timeout_ms": 10000,
    "retry_policy": "never",
    "max_attempts": 1,
    "provider_defaults_version": "native-android-defaults-v1"
  },
  {
    "id": "swipe-sample-list",
    "action": "swipe",
    "description": "Swipe the local sample list",
    "mutation": "none",
    "arguments": null,
    "provider_args": {"direction": "up", "percent": 0.7, "hold_ms": 800},
    "timeout_ms": 10000,
    "retry_policy": "safe",
    "max_attempts": 1,
    "provider_defaults_version": "native-android-defaults-v1"
  },
  {
    "id": "pause-for-sample-state",
    "action": "pause",
    "description": "Pause for the sample state",
    "mutation": "none",
    "arguments": null,
    "provider_args": {"milliseconds": 500, "hold_ms": 0},
    "timeout_ms": 1000,
    "retry_policy": "safe",
    "max_attempts": 1,
    "provider_defaults_version": "native-android-defaults-v1"
  }
]
```

Adapter는 위 frozen 값을 다시 해석하거나 보완하지 않고 아래 Native Scenario step으로 변환한다.

```json
[
  {
    "id": "launch-app",
    "title": "Launch the approved APK",
    "action": {"type": "launch"},
    "effects": ["potential_mutation"],
    "approval": "required",
    "retry_policy": "never",
    "timeout_ms": 30000,
    "hold_ms": 800
  },
  {
    "id": "wait-for-sample-control",
    "title": "Wait for the sample control",
    "action": {
      "type": "wait_for",
      "target": {
        "by": "accessibility_id",
        "value": "qa-sample-control"
      },
      "state": "present"
    },
    "effects": ["local_read"],
    "approval": "none",
    "retry_policy": "safe",
    "timeout_ms": 10000,
    "hold_ms": 800
  },
  {
    "id": "tap-sample-control",
    "title": "Tap the sample control",
    "action": {
      "type": "tap",
      "target": {"by": "id", "value": "org.example.qasample:id/sample_action"}
    },
    "effects": ["potential_mutation"],
    "approval": "required",
    "retry_policy": "never",
    "timeout_ms": 10000,
    "hold_ms": 800
  },
  {
    "id": "fill-sample-field",
    "title": "Fill a non-sensitive sample value",
    "action": {
      "type": "fill",
      "target": {"by": "accessibility_id", "value": "qa-sample-field"},
      "value": "sample-value"
    },
    "effects": ["potential_mutation"],
    "approval": "required",
    "retry_policy": "never",
    "timeout_ms": 10000,
    "hold_ms": 800
  },
  {
    "id": "submit-sample-key",
    "title": "Submit the sample value with Enter",
    "action": {"type": "press_key", "key": "ENTER"},
    "effects": ["potential_mutation"],
    "approval": "required",
    "retry_policy": "never",
    "timeout_ms": 10000,
    "hold_ms": 800
  },
  {
    "id": "return-from-sample",
    "title": "Return from the sample screen",
    "action": {"type": "back"},
    "effects": ["potential_mutation"],
    "approval": "required",
    "retry_policy": "never",
    "timeout_ms": 10000,
    "hold_ms": 800
  },
  {
    "id": "swipe-sample-list",
    "title": "Swipe the local sample list",
    "action": {"type": "swipe", "direction": "up", "percent": 0.7},
    "effects": ["local_read"],
    "approval": "none",
    "retry_policy": "safe",
    "timeout_ms": 10000,
    "hold_ms": 800
  },
  {
    "id": "pause-for-sample-state",
    "title": "Pause for the sample state",
    "action": {"type": "pause", "milliseconds": 500},
    "effects": ["local_read"],
    "approval": "none",
    "retry_policy": "safe",
    "timeout_ms": 1000,
    "hold_ms": 0
  }
]
```

현재 external MCP step schema는 `max_attempts`를 받지 않는다. Adapter는 binding의 server version과 provider defaults가 runbook의 고정 `max_attempts` semantics와 같은지 compile 단계에서 확인해야 한다. 다르면 job을 만들지 않는다.

`wait-for-sample-control` 성공은 control 존재만 증명한다. Backend 저장 상태까지 expected에 포함되어 있으면 별도 `api_state` 또는 `db_state`가 없을 때 Pass를 판정할 수 없다.

## 14. P3(Android MCP adapter) MVP 구현과 실행

P3(Android MCP adapter) MVP compiler는 action 범위를 첫 `launch` 한 건과 하나 이상의 `wait_for present|absent`로 제한한다. Locator는 `accessibility_id`를 먼저 선택하고 없으면 Android resource `id`를 선택한다. 다른 action과 `text`, `class_name`, `xpath` locator는 문서 계약에는 남아 있지만 후속 확장 전까지 compiler가 거부한다.

Binding은 core가 아닌 project runtime이 작성한다. 실제 APK path, package ID, AVD, Emulator serial, MCP executable path, runtime source root는 binding에만 둔다.

Binding 생성 시 JDK와 APK verifier도 절대 경로로 고정한다.

```bash
node scripts/prepare-native-mcp-binding.mjs \
  --mcp-executable /absolute/path/to/external-mcp \
  --mcp-runtime-root /absolute/path/to/external-mcp-source \
  --apk /absolute/path/to/test-app.apk \
  --java-home /absolute/path/to/jdk \
  --apksigner /absolute/path/to/android-sdk/build-tools/35.0.0/apksigner \
  --package-id org.example.qasample \
  --binding-id sample-android-emulator-r1 \
  --avd qa-sample-api-35 \
  --output native-mcp-binding.json
```

```bash
python3 scripts/validate-contracts.py native-mcp-binding.json

node scripts/compile-android-runbook.mjs \
  --scenario scenario.json \
  --config native-android-config.json \
  --preflight \
  --output runbook-preflight.json

node scripts/run-android-mcp.mjs \
  --request runner-request-preflight.json \
  --runbook runbook-preflight.json \
  --binding native-mcp-binding.json \
  --preflight-only \
  --output native-preflight.json
```

외부 승인 시스템은 `native-preflight.json`의 `runbook_plan_sha256`, `provider_plan_hash`, `runtime_binding_sha256`, `approved_step_ids`, `environment`를 승인 기록에 고정한다. `runtime_binding_sha256`는 launcher, 외부 MCP runtime source tree, tool schema, Native Scenario schema, APK, JDK·APK verifier, Emulator, Appium 설정을 포함한 binding 전체를 고정한다. 그 기록으로 executable runbook을 다시 compile한 다음 `--preflight-only` 없이 runner를 실행한다. Runner는 실행 직전에 승인 기록의 `runtime_binding_sha256`가 runner request 및 실제 binding hash와 같은지 검사한다.

Readiness 필드가 없는 이전 binding과 그 binding hash를 참조한 승인 기록은 신규 실행에 사용할 수 없다. Binding을 다시 생성하고 새 preflight의 plan·provider·runtime binding hash로 승인을 받아야 한다. 기존 결과 파일은 당시 실행의 historical evidence로만 보존한다.

Runner는 `wait_for` terminal result에서 `locator_result`를 만든다. 완료된 Android 결과에는 실제 실행에서 관측한 Appium과 UiAutomator2 version이 필요하다. External MCP가 version을 반환하지 않으면 전용 Appium debug log의 성공한 session, package ID, 실행 시간 범위, version을 deterministic collector로 확인한다. Collector는 log SHA-256과 구조화 version record만 evidence registry에 넣고 원문 log, MP4, screenshot, Base64 recording payload는 넣지 않는다. External MCP가 UI hierarchy나 logcat을 반환하지 않으면 이를 생성했다고 주장하지 않고 `missing_evidence`에 기록한다.

## 15. 적합성 기준

Android adapter 구현은 아래 항목을 모두 충족해야 한다.

- 외부 MCP를 호출하고 runtime 코드를 core에 복사하지 않는다.
- MCP client를 시작하기 전에 launcher executable과 runtime source tree가 binding digest와 일치하는지 다시 계산한다.
- MCP client를 시작하기 전에 exact JDK와 `apksigner` executable hash를 다시 계산하고 APK 서명 검증을 성공한다.
- MCP initialize identity, tool schema, Native Scenario schema를 binding hash와 대조한다.
- Required tool request·response의 최소 shape를 검증한다.
- Android Emulator와 APK만 실행한다.
- iOS, physical device, AAB, remote Appium을 실행하지 않고 `execution.status=not_started`와 unsupported reason을 반환한다.
- APK를 absolute local path로만 등록하고 hash를 고정한다.
- inspection 전 앱 launch 효과를 승인받는다.
- Compiler가 우선순위로 선택한 locator 하나만 실행하고 fallback하지 않는다.
- Runbook의 timeout, retry, hold, provider defaults version을 바꾸지 않는다.
- mutation step에 exact approval과 `retry_policy=never`를 강제한다.
- destructive fixture의 격리 환경을 확인한다.
- Artifact hash와 step·locator 결과를 수집한다. UI hierarchy나 logcat provider extension이 없으면 `missing_evidence`에 기록한다.
- screenshot, MP4, 실행 agent 자기 보고를 Pass 증거로 사용하지 않는다.
- 증거가 부족하면 `insufficient_evidence`로 판정할 수 있도록 누락 항목을 명시한다.
