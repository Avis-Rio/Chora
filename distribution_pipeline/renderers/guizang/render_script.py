import json


ROLE_SUFFIX = {
    "cover": "cover",
    "insight": "insight",
    "concept-map": "concept",
    "philosophy": "philosophy",
    "closing": "closing",
}


def build_xhs_render_targets(pages: list[dict]) -> list[dict]:
    targets = []
    for page in pages:
        page_id = page.get("id", "")
        role = ROLE_SUFFIX.get(page.get("role", ""), "card")
        targets.append(
            {
                "selector": f"#{page_id}",
                "filename": f"{page_id}-{role}.png",
            }
        )
    return targets


def build_render_script(html_name: str, targets: list[dict]) -> str:
    targets_json = json.dumps(targets, ensure_ascii=False, indent=2)
    html_name_json = json.dumps(html_name)
    return f"""#!/usr/bin/env node
  const fs = require("node:fs");
  const path = require("node:path");
  const {{ pathToFileURL }} = require("node:url");
  const {{ chromium }} = require("playwright");

const htmlName = {html_name_json};
const targets = {targets_json};

async function launchBrowser() {{
  try {{
    const browser = await chromium.launch({{
      args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
    }});
    return {{ browser, cleanup: async () => {{ await browser.close(); }} }};
  }} catch (error) {{
    const browserPath = process.env.PLAYWRIGHT_BROWSERS_PATH || "(default cache)";
    throw new Error(
      `Guizang renderer could not launch Playwright Chromium. ` +
      `PLAYWRIGHT_BROWSERS_PATH=${{browserPath}}. ` +
      `Install browsers with: PLAYWRIGHT_BROWSERS_PATH=${{browserPath}} npx playwright install chromium\\n` +
      (error && error.stack ? error.stack : String(error))
    );
  }}
}}

async function waitForReady(page) {{
  await page.waitForLoadState("domcontentloaded");
  await Promise.race([
    page.evaluate(() => document.fonts && document.fonts.ready),
    page.waitForTimeout(3000),
  ]).catch(() => {{}});
  await page.waitForTimeout(900);
}}

async function main() {{
  const root = __dirname;
  const outputDir = path.join(root, "output");
  fs.mkdirSync(outputDir, {{ recursive: true }});

  console.log(`Guizang render: opening ${{htmlName}}`);
  const {{ browser, cleanup }} = await launchBrowser();
  const page = await browser.newPage({{
    viewport: {{ width: 2400, height: 1800 }},
    deviceScaleFactor: 1,
  }});

  const url = pathToFileURL(path.join(root, htmlName)).href;
  await page.goto(url, {{ waitUntil: "domcontentloaded", timeout: 45000 }});
  await waitForReady(page);

  for (const target of targets) {{
    console.log(`Guizang render: screenshot ${{target.selector}} -> ${{target.filename}}`);
    const locator = page.locator(target.selector).first();
    if (await locator.count() === 0) {{
      throw new Error(`Missing screenshot target: ${{target.selector}}`);
    }}
    await locator.screenshot({{ path: path.join(outputDir, target.filename) }});
    console.log(`WROTE ${{target.filename}}`);
  }}

  await cleanup();
  console.log(`Guizang render: completed ${{targets.length}} image(s)`);
}}

main().catch((error) => {{
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
}});
"""
