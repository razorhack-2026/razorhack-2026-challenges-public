#!/usr/bin/env node
/*
 * strucpp_bundle.mjs - build an OpenPLC Runtime v4 upload bundle from ST.
 *
 * The v4 runtime does NOT compile Structured Text. It expects the C++ that
 * STruC++ generates, plus the STruC++ runtime headers, a defines.h carrying
 * PROGRAM_MD5, and any conf/*.json plugin configs. This script mirrors the
 * OpenPLC Editor's own packaging (composeRuntimeV4Bundle +
 * runProgramBuildPipeline) so the runtime's scripts/compile.sh accepts it.
 *
 * Pin STruC++ to the version the target runtime expects (runtime v4.3.1 <->
 * STruC++ v0.7.0, the version the Editor pins in binary-versions.json).
 *
 * Usage:
 *   node tools/strucpp_bundle.mjs --strucpp <strucpp checkout> \
 *        --st <program.st> --out <staging dir> [--conf name=path ...]
 *
 * Then zip the staging dir's CONTENTS (not the dir itself) as program.zip.
 */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

function args() {
  const a = process.argv.slice(2);
  const o = { conf: [] };
  for (let i = 0; i < a.length; i++) {
    const k = a[i];
    const v = a[i + 1];
    if (k === "--strucpp") { o.strucpp = v; i++; }
    else if (k === "--st") { o.st = v; i++; }
    else if (k === "--out") { o.out = v; i++; }
    else if (k === "--conf") { o.conf.push(v); i++; }
    else { console.error(`unknown arg ${k}`); process.exit(2); }
  }
  if (!o.strucpp || !o.st || !o.out) {
    console.error("usage: strucpp_bundle.mjs --strucpp DIR --st FILE --out DIR [--conf name=path]");
    process.exit(2);
  }
  return o;
}

const opt = args();
const sc = path.resolve(opt.strucpp);
const strucpp = await import(pathToFileURL(path.join(sc, "dist/index.js")).href);
const loader = await import(pathToFileURL(path.join(sc, "dist/node/library-loader.js")).href);

// Standard IEC libraries (TON/CTU/R_TRIG, std functions). Same set a default
// Editor project carries; OSCAT/softmotion are opt-in there, so omitted here.
const LIBS = ["iec-standard-fb.stlib", "iec-std-functions.stlib", "additional-function-blocks.stlib"];
const libraries = LIBS
  .map((f) => path.join(sc, "libs", f))
  .filter((p) => fs.existsSync(p))
  .map((p) => loader.loadStlibFromFile(p));

const source = fs.readFileSync(opt.st, "utf8");
const md5 = crypto.createHash("md5").update(source).digest("hex");

const result = strucpp.compile(source, {
  headerFileName: "generated.hpp",
  fileName: "program.st",
  debug: true,
  lineMapping: true,
  libraries,
  md5,
  pouIncludes: [],
});

if (!result.success) {
  console.error("STruC++ compilation failed:");
  for (const e of result.errors) {
    console.error(`  program.st:${e.line}:${e.column}: ${e.message}`);
  }
  process.exit(1);
}

const files = {};
files["program.st"] = source;
if (result.cppFiles && result.cppFiles.length > 0) {
  for (const f of result.cppFiles) files[f.name] = f.content;
} else {
  files["generated.cpp"] = result.cppCode;
}
files["generated.hpp"] = result.headerCode;
if (result.debugTableCpp !== undefined) files["generated_debug.cpp"] = result.debugTableCpp;
if (result.debugMap !== undefined) files["debug-map.json"] = JSON.stringify(result.debugMap, null, 2);
files["defines.h"] = `#pragma once\n// Program MD5\n#define PROGRAM_MD5 "${md5}"\n`;
files["c_blocks.h"] = "// Empty file\n";

const incDir = path.join(sc, "src", "runtime", "include");
for (const h of fs.readdirSync(incDir)) {
  if (h.endsWith(".hpp") || h.endsWith(".h")) {
    files[`strucpp_runtime/include/${h}`] = fs.readFileSync(path.join(incDir, h), "utf8");
  }
}

for (const c of opt.conf) {
  const [name, p] = c.split("=");
  files[`conf/${name}.json`] = fs.readFileSync(p, "utf8");
}

const out = path.resolve(opt.out);
fs.rmSync(out, { recursive: true, force: true });
for (const [rel, content] of Object.entries(files)) {
  const dest = path.join(out, rel);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, content);
}

const warn = result.warnings ? result.warnings.length : 0;
console.log(`bundle ok: ${Object.keys(files).length} files, md5 ${md5}, ${warn} warning(s) -> ${out}`);
