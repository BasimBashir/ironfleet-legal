// opencode/index.js — IronFleet Legal for OpenCode. One module, both plugin APIs:
// V2 (OpenCode 2.x) calls setup(ctx); V1 (1.18.29+) calls server() for hooks.
// Everything is read from the plugin's own files (skills/, commands/, agents/,
// mcp/server.py, hooks/moot_gate_hook.py) — no copies to drift.
import fs from "node:fs"
import path from "node:path"
import { spawnSync } from "node:child_process"
import { fileURLToPath } from "node:url"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const PYTHON = process.env.IRONFLEET_PYTHON || "python"
const MCP = { type: "local", command: [PYTHON, path.join(ROOT, "mcp", "server.py")], enabled: true }
const WRITE_TOOLS = new Set(["write", "edit", "multiedit", "patch", "apply_patch"])
const DISALLOWED = { Bash: "bash", WebFetch: "webfetch", WebSearch: "websearch", Write: "write", Edit: "edit" }

function readKit(folder) {
  const dir = path.join(ROOT, folder)
  let names = []
  try { names = fs.readdirSync(dir) } catch { return [] }
  return names.filter((n) => n.endsWith(".md")).map((n) => {
    const text = fs.readFileSync(path.join(dir, n), "utf8")
    const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/)
    const meta = {}
    if (m) for (const line of m[1].split(/\r?\n/)) {
      const kv = line.match(/^([A-Za-z][\w-]*):\s*(.*)$/)
      if (kv) meta[kv[1]] = kv[2].trim().replace(/^"(.*)"$/, "$1")
    }
    return { name: n.slice(0, -3), meta, body: m ? text.slice(m[0].length) : text }
  })
}

// The moot gate: the same Python script Claude Code, Codex and Grok run as a hook.
// Not exported: the 1.x loader treats every named export as a plugin.
function gate(tool, args, cwd) {
  if (!WRITE_TOOLS.has(String(tool).toLowerCase())) return
  const r = spawnSync(PYTHON, [path.join(ROOT, "hooks", "moot_gate_hook.py")], {
    input: JSON.stringify({ tool_input: args || {}, cwd }), encoding: "utf8", timeout: 30000,
  })
  if (r.status === 2) throw new Error((r.stderr || "").trim() || "blocked by the IronFleet moot gate")
}

// ---------------------------------------------------------------- V1 (OpenCode 1.x)
async function server(input = {}) {
  const commands = readKit("commands")
  const agents = readKit("agents")
  return {
    config: async (cfg) => {
      cfg.mcp = cfg.mcp || {}
      if (!cfg.mcp.ironfleet) cfg.mcp.ironfleet = MCP
      cfg.skills = cfg.skills || {}
      cfg.skills.paths = cfg.skills.paths || []
      const skillsDir = path.join(ROOT, "skills")
      if (!cfg.skills.paths.includes(skillsDir)) cfg.skills.paths.push(skillsDir)
      cfg.command = cfg.command || {}
      for (const c of commands) {
        if (!(c.name in cfg.command)) cfg.command[c.name] = { template: c.body, description: c.meta.description }
      }
      cfg.agent = cfg.agent || {}
      for (const a of agents) {
        if (a.name in cfg.agent) continue
        const tools = {}
        for (const t of (a.meta.disallowedTools || "").split(",")) {
          const k = DISALLOWED[t.trim()]
          if (k) tools[k] = false
        }
        cfg.agent[a.name] = { description: a.meta.description, mode: "subagent", prompt: a.body, tools }
      }
    },
    "tool.execute.before": async (hook, output) => gate(hook.tool, output.args, input.directory),
  }
}

// ---------------------------------------------------------------- V2 (OpenCode 2.x)
async function setup(ctx) {
  await ctx.mcp.transform((editor) => { if (!editor.get("ironfleet")) editor.set("ironfleet", MCP) })
  const skillsDir = path.join(ROOT, "skills")
  await ctx.skill.transform((editor) => {
    for (const id of fs.readdirSync(skillsDir)) {
      const file = path.join(skillsDir, id, "SKILL.md")
      if (!fs.existsSync(file)) continue
      const text = fs.readFileSync(file, "utf8")
      const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/)
      const desc = m && (m[1].match(/^description:\s*(.*)$/m) || [])[1]
      editor.add({ id, name: id, description: desc || undefined, path: file, content: m ? text.slice(m[0].length) : text })
    }
  })
  await ctx.command.transform((editor) => {
    for (const c of readKit("commands")) {
      editor.add({
        name: c.name,
        description: c.meta.description,
        execute: async ({ sessionID, prompt, delivery }) => {
          await ctx.session.prompt({ ...prompt, sessionID, delivery,
            text: c.body.replaceAll("$ARGUMENTS", prompt.text || "") })
        },
      })
    }
  })
  // Stage agents: V2's agent editor is not used here; commands dispatch them through
  // ironfleet_agent_brief (the dispatch rule), so every stage still gets its brief.
  await ctx.tool.hook("execute.before", (event) => gate(event.tool, event.input, ctx.directory))
}

const IronfleetLegal = { id: "ironfleet-legal", setup, server }
export default IronfleetLegal
