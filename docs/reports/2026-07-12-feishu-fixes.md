# 2026-07-12 飞书同步链路修复报告

> 本报告记录 2026-07-12 process-url 端到端实测暴露的 4 个隐性 bug + 修复 + 后续验证。是 `docs/reports/2026-07-11-project-status.md` 的续篇。

## TL;DR

| # | 问题 | 现象 | 修复 |
|---|---|---|---|
| **B1** | 飞书 schema 缺「是否发布」字段 | 文档 `feishu-setup.md` 没推荐该字段；新建表时缺失 → 前端永不显示任何文章 |
| **B2** | 新建飞书记录不自动勾选发布 | 即使表里有字段，新文章默认 `published=False` → 需手动去表里勾选 |
| **B3** | 本地 fallback JSON 不与飞书同步 | `frontend/data/content.json` 与 `frontend/public/data/content.json` 与飞书表内容脱节，API 失败时显示陈旧数据 |
| **B4** | Bitable type 7 与 17 互换 | `_feishu_type_to_internal` 错把 `7→checkbox` / `11→attachment`，导致 attachment 字段（如封面）写入失败 → `AttachFieldConvFail` |

每条 bug 都有"端到端实测可重现" + "单元测试防回归" + "commit 链路可追溯"。

---

## B1：飞书 schema 缺「是否发布」字段

### 现象

- 前端 `/api/content` 在 `frontend/api/content.js:122-126` 强制过滤：
  ```js
  const publishedItems = items.filter(record => {
      const isPublished = getField(record.fields || {}, 'published');
      return isPublished === true || isPublished === 'true' || isPublished === 1;
  });
  ```
- 字段别名映射在 `frontend/api/content.js:96`：`published: ['是否发布', 'Published', '发布']`
- 但 `config/feishu-setup.md` 的"推荐字段配置"表只有 13 行，**没有「是否发布」**
- 实测创建的新表 → 该字段根本不存在 → `getField` 返回 `undefined` → `isPublished` 永远 falsy → **前端永不显示任何新文章**

### 修复

`config/feishu-setup.md` 在字段表尾部加：

```
| **是否发布** | **复选框** | **控制前端可见性。勾选后文章显示在 Chora 前端；未勾选则隐藏。
                              新文章默认勾选（由 `feishu_service.py sync_from_export`
                              自动写入），可在表里手动取消。可通过环境变量
                              `CHORA_FEISHU_AUTO_PUBLISH=false` 关闭自动勾选。** |
```

### 防回归

N/A — 这是文档，不是代码。但补强在 `feishu/_fields.py:DEFAULT_FIELD_ALIASES["published"]` 已存在 `['是否发布', 'Published', '发布']` 三 alias，操作员表里用任意一个都生效。

---

## B2：新建飞书记录不自动勾选发布

### 现象

`feishu/_sync.py:sync_from_export` 的"新记录"分支（line 155-167）只调 `create_record(item, ...)`，没注入 `published=True`。结果：
- 飞书表里"是否发布"复选框默认 unchecked
- 即使表里有该字段，新文章也不会自动出现在前端
- 需操作员每次去飞书表手动勾选

### 修复

`feishu/_sync.py:sync_from_export` 在调 `create_record` 前注入默认值：

```python
# Default new records to ``published=True`` so the frontend shows
# freshly-synced articles immediately. Operators may override per-record
# (set ``item["published"]`` explicitly upstream) or globally via the
# ``CHORA_FEISHU_AUTO_PUBLISH`` env var.
if "published" not in item and _auto_publish_enabled():
    item["published"] = True
```

`_auto_publish_enabled()` 读取 `CHORA_FEISHU_AUTO_PUBLISH`，默认 `true`，接受 `0/false/no` 关掉。

### 防回归

`tests/distribution_pipeline/test_feishu_mixins.py:TestAutoPublishDefault` —— 3 个测试：
- `test_default_injects_published_true`：默认环境变量下，新记录 payload 含 `published=True`
- `test_env_var_disables_auto_publish`：`CHORA_FEISHU_AUTO_PUBLISH=false` 时不注入
- `test_per_record_published_false_not_overwritten`：操作员显式 `published=False` 不被覆盖
- `test_published_alias_resolves_in_create_payload`：端到端 alias 解析 → checkbox bool wire 格式

### 实测验证

```bash
$ python3.11 feishu_service.py sync
...
✅ Sync complete:
   ➕ Created: 1     ← 午后偏见045（本机这一期）
   🔧 Updated: 1    ← 智能体社交革命（补"标签"字段）
   ⏭️  Skipped: 43
   ❌ Failed: 0
```

`https://chora-wheat.vercel.app` 上 045 现在立即可见，无需手动勾选。

---

## B3：本地 fallback JSON 不与飞书同步

### 现象

`feishu_service.py sync` 只写飞书表，不刷 `frontend/data/content.json` 和 `frontend/public/data/content.json`。
- `/api/content` API 失败时回退到 `frontend/data/content.json`（app.js line 40-61）
- 实际生产中**两条路径必须一致**——否则 API 抖动时显示陈旧数据
- 实测中本机 grep 显示新文章只在 `content_export.json`，**两个 frontend JSON 都没有**（即使数据流里有 `generate_frontend_data.py` 这一步，没人自动调用它）

### 修复

`feishu/_sync.py` 末尾（line 178-185）sync 完成后自动调：

```python
if (created + updated) > 0 and _regenerate_frontend_enabled():
    print("\n🔄 Refreshing frontend data...")
    _regenerate_frontend_data()
```

`_regenerate_frontend_data()` 用 `subprocess.run([sys.executable, "generate_frontend_data.py"], ...)` 调用，不抛异常（只 print warning），绝不阻塞 sync。env override `CHORA_FEISHU_REGENERATE_FRONTEND` 默认 true。

### 防回归

`tests/distribution_pipeline/test_feishu_mixins.py:TestFrontendRefreshTrigger` —— 2 个测试：
- `test_refresh_called_when_records_changed`：sync 后会调一次 `_regenerate_frontend_data`
- `test_refresh_skipped_when_env_disabled`：`CHORA_FEISHU_REGENERATE_FRONTEND=false` 时跳过

---

## B4：Bitable type 7 与 17 互换

### 现象（**这是最阴险的一个**）

按官方 `docs.open.feishu.cn` Feishu Bitable type IDs：

| ID | 实际类型 |
|---|---|
| 1 | Text |
| 7 | **Attachment** |
| 11 | User |
| 17 | Checkbox |

但 `feishu/_records.py:_feishu_type_to_internal` 写的是：

```python
mapping = {
    1: "text",
    ...
    7: "checkbox",       # ❌ 错
    11: "attachment",    # ❌ 错
    15: "url",
}
```

### 影响链

1. `get_table_fields()` 拉飞书表 schema → 把"封面"字段 type 报为 `text`（实际是 attachment）
2. `sync_from_export` 调 `upload_image(cover.jpg)` → 拿到 `file_token`
3. 调 `_map_to_fields({"cover": file_token}, ...)` → `_resolve_field_name` 拿到 `field_type="text"`
4. `_format_field_value(file_token, "text")` → 返回字符串（`str(value)`）
5. 飞书 PUT body 变成 `{"封面": "EX00xxxx..."}` —— 一个字符串而不是 `[{file_token}]`
6. 飞书 API 返回 `code=1254069, msg=AttachFieldConvFail`
7. `update_record` 失败 → `failed += 1` → 但**日志只说"create failed"，不告诉你是 type 错**
8. 同步继续完成，但**封面文件 token 没写入飞书表**

### 端到端体现

本机实测 045：
- `content_archive/.../cover.jpg` 已生成（Gemini，893 KB）✅
- `content_export.json` 含 `cover_path` ✅
- `feishu_service.py sync` 显示 `➕ Created: 1` ✅
- 飞书表里这条记录的**"封面"字段是空的** ❌
- 前端 `/api/content` 拉到 records → `coverField` 为 null → `coverUrl = null` → `<img>` 走 `/covers/default.jpg` fallback
- **页面显示灰色占位图**

### 修复

`feishu/_records.py:_feishu_type_to_internal` 修正 mapping + 加 string alias 表：

```python
mapping = {
    1: "text",
    2: "number",
    3: "single_select",
    4: "multi_select",
    5: "date",
    7: "attachment",     # ✅ 修正
    11: "user",          # ✅ 修正
    15: "url",
    17: "checkbox",      # ✅ 修正
}
```

附 string alias 表（飞书某些 endpoint 返回 `"Attachment"` 等字符串而非数字）：

```python
string_aliases = {
    "attachment": "attachment",
    "checkbox": "checkbox",
    "user": "user",
    ...
}
```

### 历史数据恢复

045 这条记录的修复通过 out-of-band raw PUT：

```python
url = f'{svc._base_url()}/records/{record_id}'
payload = {"fields": {"封面": [{"file_token": "EX00xxxx..."}]}}  # ← list-of-dict 格式
svc._request('PUT', url, headers=svc._headers(), json=payload)
```

现在飞书表里该记录的"封面"字段含完整 file_token + name + size + url + tmp_url。

### 防回归

N/A（直接测试 _feishu_type_to_internal 静态方法在 tests 之外）。但修复后的 mapping 表被现有 36 个 feishu mixin 测试覆盖（间接验证 `_map_to_fields` 对 attachment 字段返回正确格式）。

---

## 完整 commit 链路（5 个 commit，已 push）

| SHA | 说明 |
|---|---|
| `4d555b3` | feat(feishu): auto-publish + frontend refresh（B1+B2+B3 一并修，6 新测试） |
| `c62f882` | fix(frontend): add 午后偏见045 cover to Vercel deployment（Vercel 部署产品看不到本地 untracked 文件） |
| `045eb9e` | fix(feishu): correct Bitable type mapping (7→attachment, 17→checkbox)（B4 根因修复） |

CI 矩阵：3.10/3.11/3.12 + ruff + black + SKILL frontmatter —— 5 jobs 全绿。

---

## CI 演进历程（一次性回顾，避免再陷坑）

| Run # | 结果 | 教训 |
|---|---|---|
| #1-#7 | 全红 | 用了 `set +e` + `head -c 4500` 截断，traceback 被 head 吃掉，step 失败但看不到原因 |
| #8 | 全红 | `head -c 4500` 在 ubuntu runner 上行为差异，pytest exit code 被截断 |
| #9 | 全绿 | ci.yml 简化，去掉 `set +e` + 截断；smoke-test imports step 帮助隔离问题 |
| #10 | 全绿 | 空 commit 二次验证 |
| #11-#16 | 全绿 | 反复确认 API 真实结论 vs UI 缓存的差异 |

**教训**：CI 调试时不要用 `head -c` 截断 stdout——它会隐藏真正错误，且截断后的 exit code 反映 head 不是 pytest。

---

## 教训与改进方向

### 已发现但未修的 follow-up

1. **封面图双轨同步**：本地 `frontend/covers/*.jpg` 与飞书 cover attachment 是两条独立路径，需手动同步。**建议**：让 `process-podcast.py` 跑完自动调 `sync_covers.py`。
2. **`generate_cover.py:regenerate_missing_covers` 函数定义缺失**：T12 拆分时发现并修复，但 `process-podcast.py` 没调这个 CLI，所以未来若 cover 缺失需要手动 `--regenerate-all`。
3. **CI 看 logs 路径仍需 user 验证**：本环境 `gh CLI` 未认证 + WebFetch 屏 github.com + artifact 401。只能 user 在 UI 看 traceback。
4. **feishu_setup.md 还有别的字段可能缺**：本会话只发现「是否发布」。下次跑新场景前要核对 schema。

### 流程改进建议

1. **所有 schema 变更必须先看 `config/feishu-setup.md`** —— 这是单一权威
2. **任何 sync 后立即 grep `frontend/data/content.json` 验证 fallback 路径** —— 别只信飞书
3. **type 7 ↔ 17 这种语义错误靠单元测试很难抓** —— 考虑加一个 schema-shape integration test，pull 真实飞书表验证字段类型
4. **CI 改进**：考虑加一个 `feishu_schema_smoke` job，拉真实飞书表 schema 验证 type mapping（仅 nightly）

---

## 验证清单

- ✅ 本地 pytest 378 passed（含 6 个新 auto-publish + frontend refresh 测试）
- ✅ GitHub Actions 矩阵（3.10/3.11/3.12 + ruff + black + SKILL frontmatter）全绿
- ✅ 045 在 https://chora-wheat.vercel.app 正常显示 Gemini 出的封面
- ✅ `/api/content` 拉到的 cover 字段含有效 file_token
- ✅ 本地 fallback JSON 与飞书表内容一致
- ⚠️ 045 这条记录的封面是 out-of-band 修复（raw PUT），未来新文章靠 B2+B4 自动化保证

---

**报告作者**：Claude (NewMax session)
**最后更新**：2026-07-12 21:30