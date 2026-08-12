import { spawn } from "node:child_process";
import readline from "node:readline";

import { ContractError, assertPlainObject } from "./web-provider-lib.mjs";

export class StdioMcpClient {
  constructor({ executablePath, arguments: commandArguments = [], workingDirectory = undefined, timeoutMs = 30_000 }) {
    this.executablePath = executablePath;
    this.commandArguments = commandArguments;
    this.workingDirectory = workingDirectory;
    this.timeoutMs = timeoutMs;
    this.child = null;
    this.pending = new Map();
    this.nextId = 1;
    this.stderrBytes = 0;
  }

  async start() {
    if (this.child) return;
    this.child = spawn(this.executablePath, this.commandArguments, {
      cwd: this.workingDirectory,
      env: process.env,
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.child.stderr.on("data", (chunk) => {
      this.stderrBytes += chunk.length;
    });
    this.child.once("error", (error) => this.#rejectAll(new ContractError("E_MCP_LAUNCH_FAILED", `MCP process could not start (${error.code ?? error.name})`)));
    this.child.once("exit", (code, signal) => {
      this.#rejectAll(new ContractError("E_MCP_PROCESS_EXITED", `MCP process exited before completing requests (code=${code}, signal=${signal ?? "none"})`));
    });
    const lines = readline.createInterface({ input: this.child.stdout, crlfDelay: Infinity });
    lines.on("line", (line) => this.#handleLine(line));
  }

  #handleLine(line) {
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      this.#rejectAll(new ContractError("E_MCP_PROTOCOL_INVALID", "MCP stdout contained invalid JSON"));
      return;
    }
    const pending = this.pending.get(message.id);
    if (!pending) return;
    this.pending.delete(message.id);
    clearTimeout(pending.timer);
    if (message.error) {
      pending.reject(new ContractError("E_MCP_RPC_ERROR", "MCP returned a JSON-RPC error", "$", { rpc_code: message.error.code }));
    } else {
      pending.resolve(message.result);
    }
  }

  #rejectAll(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }

  request(method, params = {}) {
    if (!this.child?.stdin?.writable) return Promise.reject(new ContractError("E_MCP_NOT_STARTED", "MCP client is not started"));
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new ContractError("E_MCP_TIMEOUT", `MCP request timed out: ${method}`));
      }, this.timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
    });
  }

  notify(method, params = {}) {
    if (!this.child?.stdin?.writable) throw new ContractError("E_MCP_NOT_STARTED", "MCP client is not started");
    this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", method, params })}\n`);
  }

  async initialize(protocolVersion) {
    const result = await this.request("initialize", {
      protocolVersion,
      capabilities: {},
      clientInfo: { name: "spec-driven-qa-native-adapter", version: "1.0.0" },
    });
    this.notify("notifications/initialized");
    return result;
  }

  async listTools() {
    return this.request("tools/list");
  }

  async callTool(name, argumentsValue) {
    const result = await this.request("tools/call", { name, arguments: argumentsValue });
    assertPlainObject(result, "E_MCP_TOOL_RESULT_INVALID", "$", "MCP tool result must be an object");
    if (result.isError === true) throw new ContractError("E_MCP_TOOL_ERROR", `MCP tool failed: ${name}`);
    if (result.structuredContent && typeof result.structuredContent === "object") return result.structuredContent;
    const text = result.content?.find((item) => item?.type === "text")?.text;
    if (typeof text !== "string") throw new ContractError("E_MCP_TOOL_RESULT_INVALID", `MCP tool returned no structured payload: ${name}`);
    try {
      const parsed = JSON.parse(text);
      assertPlainObject(parsed, "E_MCP_TOOL_RESULT_INVALID", "$", "MCP tool text payload must decode to an object");
      return parsed;
    } catch (error) {
      if (error instanceof ContractError) throw error;
      throw new ContractError("E_MCP_TOOL_RESULT_INVALID", `MCP tool text payload is not JSON: ${name}`);
    }
  }

  async close() {
    if (!this.child) return;
    const child = this.child;
    this.child = null;
    child.stdin.end();
    if (child.exitCode === null) child.kill("SIGTERM");
    await new Promise((resolve) => {
      if (child.exitCode !== null) return resolve();
      const timer = setTimeout(() => {
        if (child.exitCode === null) child.kill("SIGKILL");
        resolve();
      }, 1_000);
      child.once("exit", () => {
        clearTimeout(timer);
        resolve();
      });
    });
  }
}
