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
                "width": 1080,
                "height": 1440,
            }
        )
    return targets


# 純 JS 模板（無 f-string 轉義困擾），用 {html_name_json} / {targets_json} / {browser_path} 占位
_RENDER_SCRIPT_TEMPLATE = r"""#!/usr/bin/env node
  const fs = require("node:fs");
  const path = require("node:path");
  const { pathToFileURL } = require("node:url");

const htmlName = {html_name_json};
const targets = {targets_json};

function _wkhtmltoimagePath() {
  const explicit = process.env.WKHTMLTOIMAGE_PATH;
  const candidates = [
    explicit,
    "/usr/local/bin/wkhtmltoimage",
    "/opt/homebrew/bin/wkhtmltoimage",
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

function _loadPlaywrightChromium() {
  try {
    return require("playwright").chromium;
  } catch (error) {
    error.message = `Playwright package unavailable: ${error.message}`;
    throw error;
  }
}

function _chromiumCandidates() {
  // 顯式環境變量：PLAYWRIGHT_CHROMIUM_PATH
  // 注意：自動枚舉 /Applications/Google Chrome 或 ms-playwright 緩存
  // 已被禁用——macOS sandbox / 系統策略拒絕時會觸發 Crashpad 崩潰。
  // 調用方需顯式設置路徑或使用其他渲染器（wkhtmltoimage）。
  const out = [];
  const explicit = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  if (explicit && fs.existsSync(explicit)) out.push(explicit);
  return out;
}

async function launchBrowser() {
  // 策略：優先 Playwright，wkhtmltoimage 僅作兜底。
  // wkhtmltoimage 的舊 WebKit 對現代 CSS 支持有限，不能作首選渲染器。
  const wkPath = _wkhtmltoimagePath();
  const forcedRenderer = process.env.GUIZANG_RENDERER;
  if (forcedRenderer === "wkhtmltoimage" && wkPath) {
    return { browser: null, wkhtmltoimage: true, wkhtmltoimagePath: wkPath, cleanup: async () => {} };
  }
  let chromium = null;
  try {
    chromium = _loadPlaywrightChromium();
  } catch (error) {
    if (wkPath) {
      console.log(`Guizang render: Playwright unavailable, falling back to wkhtmltoimage`);
      return { browser: null, wkhtmltoimage: true, wkhtmltoimagePath: wkPath, cleanup: async () => {} };
    }
    throw error;
  }
  const candidates = _chromiumCandidates();
  const baseArgs = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"];
  if (candidates.length === 0) {
    try {
      const browser = await chromium.launch({ args: baseArgs });
      return { browser, cleanup: async () => { await browser.close(); } };
    } catch (error) {
      if (wkPath) {
        console.log(`Guizang render: Playwright launch failed, falling back to wkhtmltoimage`);
        return { browser: null, wkhtmltoimage: true, wkhtmltoimagePath: wkPath, cleanup: async () => {} };
      }
      throw new Error(
        "No Chromium executable found or Playwright-managed Chromium failed to launch. " +
        "Set PLAYWRIGHT_CHROMIUM_PATH, run npx playwright install chromium, " +
        "or install wkhtmltoimage (brew install wkhtmltopdf) for sandbox-safe rendering.\n" +
        (error && error.stack ? error.stack : String(error))
      );
    }
  }
  let lastError = null;
  for (const exe of candidates) {
    try {
      const browser = await chromium.launch({ executablePath: exe, args: baseArgs });
      return { browser, cleanup: async () => { await browser.close(); } };
    } catch (error) {
      console.log(`Guizang render: launch failed for ${exe}, trying next`);
      lastError = error;
    }
  }
  if (wkPath) {
    console.log(`Guizang render: explicit Chromium launch failed, falling back to wkhtmltoimage`);
    return { browser: null, wkhtmltoimage: true, wkhtmltoimagePath: wkPath, cleanup: async () => {} };
  }
  throw new Error(
    `Guizang renderer could not launch any Chromium. Tried ${candidates.length} candidate(s).\n` +
    (lastError && lastError.stack ? lastError.stack : String(lastError))
  );
}

async function waitForReady(page) {
  await page.waitForLoadState("domcontentloaded");
  await Promise.race([
    page.evaluate(() => document.fonts && document.fonts.ready),
    page.waitForTimeout(3000),
  ]).catch(() => {});
  await page.waitForTimeout(900);
}

async function _screenshotWithWkhtmltoimage(root, outputDir, htmlName, wkPath) {
  // wkhtmltoimage 不支持 selector 截圖：把每個 target.selector 對應的 section 隔離到臨時 HTML
  const { execFileSync } = require("node:child_process");
  const fullHtml = fs.readFileSync(path.join(root, htmlName), "utf-8");
  for (const target of targets) {
    const idMatch = target.selector.match(/#([a-zA-Z0-9_-]+)/);
    if (!idMatch) continue;
    const sectionId = idMatch[1];
    // 抽出該 section 為獨立 HTML（含原有 style）
    const sectionMatch = fullHtml.match(new RegExp(`<section[^>]*id=["']${sectionId}["'][\\s\\S]*?</section>`));
    if (!sectionMatch) {
      throw new Error(`Section not found in HTML: ${sectionId}`);
    }
    const styleMatch = fullHtml.match(/<style>[\s\S]*?<\/style>/);
    const styleBlock = styleMatch ? styleMatch[0] : "";
    const size = {
      width: Number(target.width) || 1080,
      height: Number(target.height) || 1440,
    };
    const isolatedHtml = `<!doctype html><html><head><meta charset="utf-8">${styleBlock}</head><body style="margin:0;padding:0;background:#fff">${sectionMatch[0]}</body></html>`;
    const tmpPath = path.join(root, `_tmp_${sectionId}.html`);
    fs.writeFileSync(tmpPath, isolatedHtml, "utf-8");
    const outPath = path.join(outputDir, target.filename);
    console.log(`Guizang render: wkhtmltoimage ${target.selector} -> ${target.filename}`);
    try {
      execFileSync(wkPath, [
        "--width", String(size.width),
        "--height", String(size.height),
        "--quality", "70",
        "--javascript-delay", "1500",
        "--enable-local-file-access",
        tmpPath, outPath,
      ], { stdio: "inherit" });
    } finally {
      try { fs.unlinkSync(tmpPath); } catch (e) {}
    }
    console.log(`WROTE ${target.filename}`);
  }
}

async function main() {
  const root = __dirname;
  const outputDir = path.join(root, "output");
  fs.mkdirSync(outputDir, { recursive: true });

  console.log(`Guizang render: opening ${htmlName}`);
  const launched = await launchBrowser();
  if (launched.wkhtmltoimage) {
    // 沙箱安全模式：走 wkhtmltoimage
    await _screenshotWithWkhtmltoimage(root, outputDir, htmlName, launched.wkhtmltoimagePath);
    await launched.cleanup();
    console.log(`Guizang render: completed ${targets.length} image(s)`);
    return;
  }
  const { browser, cleanup } = launched;
  const page = await browser.newPage({
    viewport: { width: 2400, height: 1800 },
    deviceScaleFactor: 1,
  });

  const url = pathToFileURL(path.join(root, htmlName)).href;
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
  await waitForReady(page);

  for (const target of targets) {
    console.log(`Guizang render: screenshot ${target.selector} -> ${target.filename}`);
    const locator = page.locator(target.selector).first();
    if (await locator.count() === 0) {
      throw new Error(`Missing screenshot target: ${target.selector}`);
    }
    await locator.screenshot({ path: path.join(outputDir, target.filename) });
    console.log(`WROTE ${target.filename}`);
  }

  await cleanup();
  console.log(`Guizang render: completed ${targets.length} image(s)`);
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
"""


def build_render_script(html_name: str, targets: list[dict]) -> str:
    """Generate the render.cjs content. Uses str.replace for placeholders to avoid f-string brace escape."""
    targets_json = json.dumps(targets, ensure_ascii=False, indent=2)
    html_name_json = json.dumps(html_name)
    return (
        _RENDER_SCRIPT_TEMPLATE
        .replace("{html_name_json}", html_name_json)
        .replace("{targets_json}", targets_json)
    )
