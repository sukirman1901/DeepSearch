// Deep Search plugin for OpenCode
// Auto-registers MCP server and skills

import { existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pluginRoot = join(__dirname, "..");

// Find Python with venv or fallback to system python3
function findPython() {
  const venvPython = join(pluginRoot, "mcp", ".venv", "bin", "python3");
  if (existsSync(venvPython)) return venvPython;
  // Fallback: check common local install path
  const localVenv = join(process.env.HOME, "Documents/Developer/mining/mcp/.venv/bin/python3");
  if (existsSync(localVenv)) return localVenv;
  return "python3";
}

export default {
  name: "deep-search",
  version: "1.0.0",
  description: "Deep Search Engine MCP server: 7 sources, 10 consolidated tools, semantic search via ChromaDB",
  
  // Register MCP server
  mcp: {
    "deep-search": {
      command: findPython(),
      args: ["server.py"],
      cwd: join(pluginRoot, "mcp"),
      env: {
        PYTHONPATH: join(pluginRoot, "mcp")
      }
    }
  },
  
  // Register skills
  skills: {
    path: "./skills",
    default: "using-deep-search"
  },
  
  // Hook: inject skill content at session start
  hooks: {
    SessionStart: async (ctx) => {
      const fs = await import("fs");
      const path = await import("path");
      
      const skillPath = path.join(process.cwd(), "skills", "using-deep-search", "SKILL.md");
      if (fs.existsSync(skillPath)) {
        const content = fs.readFileSync(skillPath, "utf-8");
        ctx.injectContext(content);
      }
    }
  }
};
