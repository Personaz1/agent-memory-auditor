import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";

const __dirname = dirname(fileURLToPath(import.meta.url));

function run(command, args, cwd) {
  return new Promise((resolve) => {
    const p = spawn(command, args, { cwd, env: process.env });
    let out = "";
    let err = "";
    p.stdout.on("data", (d) => (out += d.toString()));
    p.stderr.on("data", (d) => (err += d.toString()));
    p.on("close", (code) => resolve({ code, out, err }));
    p.on("error", (e) => resolve({ code: 1, out, err: String(e) }));
  });
}

export default function register(api) {
  api.logger?.info?.("[agent-memory-auditor] loaded");

  api.registerCommand({
    name: "memory-audit",
    description: "Audit memory files. Usage: /memory-audit [status|run]",
    acceptsArgs: true,
    requireAuth: true,
    handler: async (ctx) => {
      const arg = (ctx.args || "status").trim().toLowerCase();
      const report = join(__dirname, "report.md");
      const json = join(__dirname, "report.json");
      const mem = join(__dirname, "memory");

      if (arg === "status") {
        return { text: [
          "Agent Memory Auditor status",
          `- memory dir: ${mem}`,
          `- report.md: ${existsSync(report) ? "present" : "missing"}`,
          `- report.json: ${existsSync(json) ? "present" : "missing"}`,
        ].join("\n") };
      }

      if (arg === "run" || arg === "") {
        const r = await run("python3", ["src/audit.py", "--dir", "memory", "--out", "report.md", "--json", "report.json"], __dirname);
        if (r.code !== 0) {
          return { text: "Audit failed:\n" + (r.err || r.out) };
        }
        return { text: "✅ Memory audit completed. Artifacts: report.md, report.json" };
      }

      return { text: "Usage:\n/memory-audit\n/memory-audit status\n/memory-audit run" };
    },
  });
}
