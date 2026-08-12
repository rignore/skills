import readline from "node:readline";

const lines = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

function respond(id, result) {
  process.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", id, result })}\n`);
}

lines.on("line", (line) => {
  const message = JSON.parse(line);
  if (!("id" in message)) return;
  if (message.method === "initialize") {
    respond(message.id, { protocolVersion: message.params.protocolVersion, capabilities: { tools: {} }, serverInfo: { name: "fake-mcp", version: "1.0.0" } });
  } else if (message.method === "tools/list") {
    respond(message.id, { tools: [{ name: "echo", inputSchema: { type: "object" }, outputSchema: { type: "object" } }] });
  } else if (message.method === "tools/call") {
    const value = { echoed: message.params.arguments.value };
    respond(message.id, { content: [{ type: "text", text: JSON.stringify(value) }], structuredContent: value, isError: false });
  } else {
    respond(message.id, {});
  }
});
