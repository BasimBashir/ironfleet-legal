// pi/extension.ts — IronFleet Legal for Pi. Pi core has no MCP, so this extension is
// the bridge: it starts the plugin's own stdio MCP server (mcp/server.py), registers
// every ironfleet_* tool with Pi, and runs the moot gate (hooks/moot_gate_hook.py)
// on Pi's write/edit tools. Skills and the 11 commands (as prompt templates) come
// from package.json's `pi` key — same files Claude Code reads.
import { spawn, spawnSync, type ChildProcessWithoutNullStreams } from "node:child_process"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { Type } from "typebox"

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const PYTHON = process.env.IRONFLEET_PYTHON || "python"
const SERVER = join(ROOT, "mcp", "server.py")

type Pending = { resolve: (v: any) => void; reject: (e: Error) => void }

class McpClient {
  private proc?: ChildProcessWithoutNullStreams
  private buf = ""
  private next = 1
  private pending = new Map<number, Pending>()

  private start() {
    const proc = spawn(PYTHON, [SERVER], { stdio: ["pipe", "pipe", "pipe"] })
    proc.stdout.setEncoding("utf8")
    proc.stdout.on("data", (chunk: string) => {
      this.buf += chunk
      let i: number
      while ((i = this.buf.indexOf("\n")) >= 0) {
        const line = this.buf.slice(0, i).trim()
        this.buf = this.buf.slice(i + 1)
        if (!line) continue
        let msg: any
        try { msg = JSON.parse(line) } catch { continue }
        const p = this.pending.get(msg.id)
        if (!p) continue
        this.pending.delete(msg.id)
        if (msg.error) p.reject(new Error(msg.error.message))
        else p.resolve(msg.result)
      }
    })
    proc.on("exit", () => {
      for (const p of this.pending.values()) p.reject(new Error("ironfleet MCP server exited — run the IronFleet doctor"))
      this.pending.clear()
      this.proc = undefined
    })
    this.proc = proc
  }

  request(method: string, params: object = {}): Promise<any> {
    if (!this.proc) this.start()
    const id = this.next++
    return new Promise((res, rej) => {
      this.pending.set(id, { resolve: res, reject: rej })
      this.proc!.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n")
    })
  }

  stop() { this.proc?.kill() }
}

// The tool list is read once, synchronously, so the tools exist before the first turn.
function listTools(): any[] {
  const input = [
    { jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18" } },
    { jsonrpc: "2.0", id: 2, method: "tools/list" },
  ].map((m) => JSON.stringify(m)).join("\n") + "\n"
  const r = spawnSync(PYTHON, [SERVER], { input, encoding: "utf8", timeout: 60000 })
  for (const line of (r.stdout || "").split("\n")) {
    try {
      const msg = JSON.parse(line)
      if (msg.id === 2) return msg.result.tools
    } catch { /* not a reply line */ }
  }
  return []
}

export default function ironfleetLegal(pi: any) {
  const client = new McpClient()
  const tools = listTools()
  if (!tools.length) {
    console.error("[ironfleet-legal] MCP server did not start — corpus tools unavailable; run the doctor skill")
  }
  for (const t of tools) {
    pi.registerTool({
      name: t.name,
      label: t.name.replace(/^ironfleet_/, "IronFleet "),
      description: t.description,
      parameters: Type.Unsafe(t.inputSchema),
      async execute(_id: string, params: object) {
        const res = await client.request("tools/call", { name: t.name, arguments: params || {} })
        const text = (res.content || []).map((c: any) => c.text || "").join("\n")
        if (res.isError) throw new Error(text)
        return { content: [{ type: "text", text }], details: {} }
      },
    })
  }

  // Moot gate on Pi's own write/edit tools: same script, same verdict.
  pi.on("tool_call", async (event: any, ctx: any) => {
    if (event.toolName !== "write" && event.toolName !== "edit") return
    const r = spawnSync(PYTHON, [join(ROOT, "hooks", "moot_gate_hook.py")], {
      input: JSON.stringify({ tool_input: event.input, cwd: ctx?.cwd || process.cwd() }),
      encoding: "utf8", timeout: 30000,
    })
    if (r.status === 2) return { block: true, reason: (r.stderr || "").trim() }
  })

  process.once("exit", () => client.stop())
}
