// Deep Search plugin for OpenCode
// Auto-registers MCP server and skills

export default {
  name: "deep-search",
  version: "1.0.0",
  description: "Deep Search Engine MCP server: 7 sources, 28 tools, semantic search via ChromaDB",
  
  // Register MCP server
  mcp: {
    "deep-search": {
      command: "python3",
      args: ["server.py"],
      cwd: "./mcp",
      env: {
        PYTHONPATH: "./mcp"
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
