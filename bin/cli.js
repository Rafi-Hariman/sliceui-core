#!/usr/bin/env node
"use strict";

/*
 * sliceui — zero-dependency installer & environment manager.
 *
 * Manages the 2-space installation of the sliceui skill:
 *   --global  -> ~/.claude/skills/sliceui
 *   --project -> ./.claude/skills/sliceui
 * and bootstraps an isolated Python .venv with lxml (PEP 668 safe).
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");

const PACKAGE_ROOT = path.join(__dirname, "..");
const SKILL_SRC = path.join(PACKAGE_ROOT, "skills", "sliceui");

const PROJECT_CONTEXT_TEMPLATE = `# SliceUI Project Context

> Isi template ini dengan konvensi proyek Anda. Skill sliceui akan memprioritaskan
> nilai di dalam file ini di atas default bawaan (bahkan saat skill berjalan dari
> instalasi global di \`~/.claude/skills/sliceui/\`).

## Tech Stack
<!-- Contoh: Angular 17 + TypeScript + SCSS, atau Laravel 11 + Blade + Bootstrap 5.3. -->

## Styling System
<!-- Contoh: Bootstrap 5.3 via CDN, Tailwind CSS, SCSS modules, atau plain CSS. -->

## Design Tokens

### Colors
<!-- brand/primary: #... ; neutral: #... ; border: #... ; background: #... -->

### Typography
<!-- font family utama, fallback, ukuran heading/body, letter-spacing. -->

### Spacing
<!-- skala spacing (4/8/12/16/24/32 px), radius, shadow. -->

## Reusable Components Mapping
| Figma Node | Komponen Proyek |
|------------|-----------------|
| Button     |                 |
| Input      |                 |
| Select     |                 |
| Tabs       |                 |
| Card       |                 |
| Chart      |                 |

## Folder Output Convention
<!-- Contoh: src/app/features/<feature>/ ; resources/views/ ; public/ -->
`;

function isWindows() {
  return process.platform === "win32";
}

function homeSkillDir() {
  return path.join(os.homedir(), ".claude", "skills", "sliceui");
}

function findPython() {
  const candidates = isWindows()
    ? ["python", "python3", "py"]
    : ["python3", "python"];
  for (const c of candidates) {
    const r = spawnSync(c, ["--version"], { stdio: "ignore" });
    if (r.status === 0) return c;
  }
  return null;
}

function venvBin(venvDir, name) {
  return isWindows()
    ? path.join(venvDir, "Scripts", name + ".exe")
    : path.join(venvDir, "bin", name);
}

function copySkill(dest) {
  if (!fs.existsSync(SKILL_SRC)) {
    throw new Error(`Skill source not found: ${SKILL_SRC}`);
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  // cpSync merges into an existing destination; it never deletes extra files,
  // so a pre-existing project-context.md is preserved on re-install.
  fs.cpSync(SKILL_SRC, dest, { recursive: true });
}

function doctor(skillDir) {
  skillDir = skillDir || homeSkillDir();
  console.log("\n== sliceui doctor ==");
  console.log(`Target: ${skillDir}`);

  const py = findPython();
  if (!py) {
    console.error("ERROR: python3 not found. Install Python 3 and retry.");
    process.exitCode = 1;
    return false;
  }
  console.log(`Python: ${py}`);

  const pyScript = path.join(skillDir, "scripts", "sliceui.py");
  if (!fs.existsSync(pyScript)) {
    console.error(
      `ERROR: ${pyScript} not found. Run 'sliceui init --global' or 'sliceui init --project' first.`
    );
    process.exitCode = 1;
    return false;
  }

  const lxmlCheck = spawnSync(py, ["-c", "import lxml"], { stdio: "ignore" });
  let venvPython = null;

  if (lxmlCheck.status === 0) {
    console.log("lxml: available globally");
  } else {
    console.log("lxml: not global — creating isolated .venv (PEP 668 safe)");
    const venvDir = path.join(skillDir, ".venv");

    const venvRes = spawnSync(py, ["-m", "venv", venvDir], { stdio: "inherit" });
    if (venvRes.status !== 0) {
      console.error("ERROR: failed to create virtual environment.");
      process.exitCode = 1;
      return false;
    }

    const pip = venvBin(venvDir, "pip");
    const pipRes = spawnSync(pip, ["install", "--quiet", "lxml"], {
      stdio: "inherit",
    });
    if (pipRes.status !== 0) {
      console.error("ERROR: failed to install lxml into .venv.");
      process.exitCode = 1;
      return false;
    }
    venvPython = venvBin(venvDir, "python");
    console.log("lxml: installed into .venv");
  }

  // Smoke test the actual engine.
  const smokePy = venvPython || py;
  const smoke = spawnSync(smokePy, [pyScript, "--help"], { encoding: "utf8" });
  if (smoke.status !== 0) {
    console.error("ERROR: smoke test `sliceui.py --help` failed.");
    console.error(smoke.stderr || "");
    process.exitCode = 1;
    return false;
  }

  console.log("sliceui.py --help: OK");
  console.log("Environment ready.");
  return true;
}

function initGlobal() {
  const dest = homeSkillDir();
  try {
    copySkill(dest);
  } catch (e) {
    console.error("ERROR: " + e.message);
    return false;
  }
  console.log(`Installed sliceui skill -> ${dest}`);
  return doctor(dest);
}

function initProject() {
  const dest = path.join(process.cwd(), ".claude", "skills", "sliceui");
  try {
    copySkill(dest);
  } catch (e) {
    console.error("ERROR: " + e.message);
    return false;
  }
  console.log(`Installed sliceui skill -> ${dest}`);
  return doctor(dest);
}

function initContext(force) {
  const dir = path.join(process.cwd(), ".claude", "skills", "sliceui");
  const file = path.join(dir, "project-context.md");
  fs.mkdirSync(dir, { recursive: true });
  if (fs.existsSync(file) && !force) {
    console.log(
      `project-context.md already exists at ${file} (use --force to overwrite).`
    );
    return true;
  }
  fs.writeFileSync(file, PROJECT_CONTEXT_TEMPLATE);
  console.log(`Created ${file}`);
  return true;
}

function printHelp() {
  console.log(`sliceui — High-precision Figma XML (.figml) UI slicing skill and CLI engine for Claude Code

Usage:
  sliceui init --global          Install skill to ~/.claude/skills/sliceui
  sliceui init --project         Install skill to ./.claude/skills/sliceui
  sliceui init --context         Scaffold project-context.md (--force overwrites)
  sliceui doctor [--target <dir>]  Verify Python + lxml (auto-creates .venv)
  sliceui --help | -h            Show this help

Examples:
  npx sliceui init --global
  npx sliceui init --project
  npx sliceui init --context --force
  npx sliceui doctor --target ~/.claude/skills/sliceui
`);
}

function main(argv) {
  const args = argv.slice(2);

  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    printHelp();
    return 0;
  }

  const cmd = args[0];
  const rest = args.slice(1);

  if (cmd === "init") {
    if (rest.includes("--global")) return initGlobal() ? 0 : 1;
    if (rest.includes("--project")) return initProject() ? 0 : 1;
    if (rest.includes("--context")) {
      return initContext(rest.includes("--force")) ? 0 : 1;
    }
    console.error("ERROR: init requires one of --global, --project, --context.");
    return 1;
  }

  if (cmd === "doctor") {
    let target = null;
    const ti = rest.indexOf("--target");
    if (ti !== -1 && rest[ti + 1]) target = rest[ti + 1];
    return doctor(target) ? 0 : 1;
  }

  console.error(`ERROR: unknown command '${cmd}'. Run 'sliceui --help'.`);
  return 1;
}

process.exit(main(process.argv));
