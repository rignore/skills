import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { StdioMcpClient } from "../mcp-stdio-client.mjs";

test("stdio client initializes, lists tools, and unwraps structured tool output", async () => {
  const server = path.resolve(import.meta.dirname, "fixtures/fake-mcp-stdio-server.mjs");
  const client = new StdioMcpClient({ executablePath: process.execPath, arguments: [server], timeoutMs: 5_000 });
  try {
    await client.start();
    const initialized = await client.initialize("2025-06-18");
    assert.equal(initialized.serverInfo.name, "fake-mcp");
    const listed = await client.listTools();
    assert.deepEqual(listed.tools.map((tool) => tool.name), ["echo"]);
    const output = await client.callTool("echo", { value: "fixture" });
    assert.deepEqual(output, { echoed: "fixture" });
  } finally {
    await client.close();
  }
});
