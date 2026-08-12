import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { StdioMcpClient } from "../mcp-stdio-client.mjs";

const executablePath = process.env.SPEC_DRIVEN_QA_DEMO_VIDEO_MCP;

test("current Demo Video MCP exposes the required Android contract", { skip: !executablePath }, async () => {
  const client = new StdioMcpClient({ executablePath, arguments: [], workingDirectory: path.dirname(path.dirname(executablePath)), timeoutMs: 10_000 });
  try {
    await client.start();
    const initialized = await client.initialize("2025-06-18");
    assert.equal(initialized.serverInfo.name, "demo-video-mcp");
    assert.equal(typeof initialized.serverInfo.version, "string");
    const listed = await client.listTools();
    const names = new Set(listed.tools.map((tool) => tool.name));
    for (const name of [
      "get_native_video_scenario_schema", "register_native_app", "get_native_runtime_status",
      "inspect_native_app", "create_native_video_job", "preflight_video_job",
      "approve_video_job", "start_video_job", "get_video_job",
    ]) assert.equal(names.has(name), true, `missing ${name}`);
    const nativeSchema = await client.callTool("get_native_video_scenario_schema", {});
    assert.equal(nativeSchema.schema.type, "object");
    assert.equal(nativeSchema.schema.properties.platform.const, "android");
  } finally {
    await client.close();
  }
});
