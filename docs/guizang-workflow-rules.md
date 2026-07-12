# Guizang 工作流经验规则

本文把最近几轮小红书卡片修复沉淀为 Chora 的 Guizang 分发规则。后续新增文章、模板或图片能力时，先遵守本文，再扩展实现。

## 目标

- 保持文章哲思深度，不把深内容压成浅口号。
- 贴合小红书增长逻辑：首图有钩子，中间页有节奏，结尾有记忆点。
- 保持 Guizang 审美：有证据图、有版式变化、有可读性，不做重复模板堆叠。
- 把已知失败变成 planner、image asset、renderer、validator 的固定护栏。

## 必守规则

### 1. 卡片数量跟随洞察

- 洞察数量多时，不能固定生成 3 张。
- 默认结构：封面 + 关键洞察页 + 哲思结语 + closing。
- 小红书主卡组通常压到 8-10 张；若文章洞察超过 10 点，优先合并弱洞察，不删除核心洞察。
- 哲思结语应保留，除非原文没有形成独立的后设判断。

### 2. 每页只承载一个观看任务

- 标题负责抓住观点。
- 正文负责解释观点，不能只取洞察首句。
- 配图负责提供证据、氛围或空间，不做无关装饰。
- 页内不能出现两条以上语义重复文本，即使字号样式不同也算失败。
- 渲染前必须先分配 `copy_slots`：`hero` 只做主标题，`lead` 只出现一次，`details` 承接解释，`caption/meta` 只放来源或导流，不回填正文。
- 任何 recipe 不得把同一句正文同时塞进标题区、卡片主体和页脚。即使视觉层级不同，也算重复。

### 2.1 Scaffold label 不可见

- `注记`、`脉络`、`张力`、`信号`、`判断`、`余波`、`边界`、`后果` 等 scaffold label 只能作为内部占位或结构标签。
- 如果原文没有这些词，最终 PNG/HTML 中不能出现这些词。
- 需要标签感时，优先显示真实原文标题、真实短语、`WECHAT`、`CHORA ARCHIVE` 等内容身份，不显示内部抽象词。

### 3. 短文本不能回落到 M03

- M03 是中长 Editorial Essay Split，不是短文兜底模板。
- 短正文（约 150 字以内）优先 M11、M09 或 M10。
- 如果短正文有视觉关键词，先补 evidence 图，让页面走 M10。
- 连续短洞察也不能因为“避免重复 recipe”而把第二页塞进 M03。

### 4. 空白不是默认美学

- 1080x1440 卡片的有效内容应覆盖约 75% 以上高度。
- 下方 25% 以上空白无明确理由，判为 under-filled。
- 修法顺序：换 recipe、增大正文/标题、补 evidence 图、增加 marginalia/ledger/pull quote、合并相邻页。
- 禁止用空的 grid、Archive Index、结构框强行填补。

### 5. Closing 不叠加 Archive Index

- Closing page 使用独立 closing layout；Swiss closing 固定走 S07 Takeaway Ledger，避免为避重落到稀疏 S12。
- 不允许把 Archive Index / Margin Index / Structure Field 强行塞进 closing。
- 收尾页必须有：大标题、正文/邀请、3-4 个总结项或一个 closing block。
- footer 不能与正文或 index 面板重叠。
- 小红书 Swiss 尾卡 CTA 使用两组元素：`CHORA ARCHIVE + 图标 + URL` 为一组，`二维码 + RHIZOMATA` 为另一组。
- Chora URL 归属于 `CHORA ARCHIVE` 组，必须显示 `WWW.CHORA.AVISIONARY.TOP` 这类可识别站点文本；不要放在二维码下面。
- Rhizomata 归属于公众号组，二维码附近只保留 `WECHAT / RHIZOMATA` 这样的短标识，不写长说明。
- 尾卡 CTA 不使用多条分割线，靠组距、字号、灰阶和图标建立层级。

### 6. 图像是内容证据，不是随机氛围

- 每套小红书图文不能全是文字。
- 默认至少：封面图 + 3-4 张洞察 evidence 图。
- evidence 选择按语义优先级，不按固定页码。
- 图像请求要绑定 `target_insight_index`，避免跳页后配图错位。
- 外部图片必须写入 `xhs/assets/SOURCES.md`，保留 provider、source_url、query、用途和目标洞察。

### 7. 视觉关键词优先补图

当前高优先级：

- 第三空间 / 公共空间 / 咖啡馆 / 图书馆 / 公园。
- 身份 / 表演 / 点赞 / 社交媒体 / 外在动机。
- 孤独与孤寂 / 渴望连接 / 主动独处。
- 沉默 / 自主权 / 记录 / 测量 / 变现。
- 数据 / 合成 / 清洗 / 视觉理解 / 模型实验室。
- 互惠 / 创作者 / 粉丝 / 算法 / 内容系统。

### 8. 中文强调色按语义切分

- 强调色不能拆开中文联合语义。
- 失败例：只强调“双”，留下“刃剑”。
- 优先强调完整短语：`双刃剑`、`第三空间`、`优先级漂移`、`外在动机`。
- 若无法安全切分，宁可强调标题前半句或不强调。

### 9. 首图钩子要重写，不照搬原标题

- 不保留无意义数字前缀，例如 `0 粉丝` 误变成封面孤立的 `0`。
- 长英文标题要变成中文增长钩子或哲思钩子。
- 封面不承载全部信息，只给读者一个继续滑动的理由。

### 10. 风格随文章内容切换

- 不能所有文章都长一样。
- Guizang 模式是视觉姿态，不是主题标签：Editorial 适合深读和杂志感；Swiss 适合系统、数据、工具和流程。
- 同一套卡片只用一个视觉系统；不要 Editorial 和 Swiss 混用，除非用户明确要 hybrid。
- 主题 token 必须来自 Guizang presets，不随手造色。

### 11. 深色主题必须先保可读

- `midnight-ink` 只适合孤独、夜景、影视、游戏等暗调内容，不是通用高级感开关。
- 深色背景要降低纹理抢眼程度，保证正文对比。
- WebGL / grain 是氛围层，不能压过正文。
- 导出后必须用手机缩略尺度检查标题和正文。

### 12. Text-on-image 需要 subject safety

- 全图封面或图上叠字前，必须确认 quiet zone 和 light test。
- 标题不能压脸、手、产品关键特征。
- 每张图要有明确 `object-position`。
- 默认先尝试无 mask；若失败，只加局部、图片色调 tint，不加全画布黑幕。

### 13. 图源 API 与版权状态分离

- Pexels / Unsplash API key 只解决获取候选，不解决版权判断。
- `license_status` 默认仍是 `unverified`，除非 provider 明确返回可用许可。
- 最终是否图内署名，由用户决定；但来源记录必须保留。

### 14. QA 是交付条件，不是可选项

每次声称完成前至少检查：

- 单元测试通过。
- 真实文章导出命令通过。
- `manifest.json` 中 Guizang validator 状态明确。
- PNG 数量、尺寸、命名通过。
- `validate-social-deck.mjs` 或 artifact contract 无 fail。
- contact sheet 或关键单图已目检。
- validator 通过不等于视觉通过；标题裁切、重心偏移、假图入版和大片空白必须靠关键 PNG 目检确认。

### 14.1 Daily 后处理必须记录并继续

- `process_video.py`、`process_podcast.py` 在 `rewritten.md` 成功生成后自动触发 Guizang XHS 分发包。
- 分发失败不能中断主内容归档；错误必须写入当前内容目录的 `distribution_errors.log`。
- 批量补 rewrite 默认不自动生图；需要使用 `python3 batch_rewrite.py --generate-distribution` 显式开启。
- 自动后处理默认走 `platform=xhs`、`renderer=guizang`、`guizang_mode=auto`。
- 自动后处理与 Guizang CLI 默认 `image_assets=plan`，只复制本地素材、写搜索计划；不得生成本地 CSS/SVG 概念 fallback。外部候选或下载必须显式选择 `candidates` / `download`。
- 静默 daily 流不得在图源选择上停下来询问用户；用配置和 `SOURCES.md` 留痕。

### 14.2 XHS 文案必须按题材生成

- `post.md` 正文不能固定使用同一段通用解释或“如果只记一件事”模板。
- 文案要从首个洞见、文章题材和频道信息里选择开场角度、读者场景和 2-3 个问题。
- Tags 要先保留来源标签与语义标签，再保留 `深度阅读`、`Chora`、`Rhizomata` 品牌标签。

### 14.3 标题断行必须保护语义短语

- 标题断行不能把 `新形态`、`大宗商品`、`自主权`、人名或英文专名切断。
- 下一行不能以 `的/之/与/和` 等虚词开头；必要时宁可让上一行稍长。
- 新增标题概念时，同步补 `title_breaker.py` 保护词与回归测试。

### 15. 微信封面对必须分开构图

- 21:9 主封面使用近完整标题，但要控制为单行或近单行，避免宽画布标题折行告警。
- 1:1 方形封面使用独立短标题，不从 21:9 盲裁。
- 必须同时输出 pair preview，方便检查两张封面的视觉关系。
- 宽封面可用封面图或语义证据图；方形封面默认以大字和留白建立识别，不强行塞图。

## 当前已机器化的护栏

- `--no-export-images` 不启动 Chrome / Playwright。
- 每张 page 进入 renderer 前会注入 `copy_slots`，避免正文在标题、卡片和脚注中重复出现。
- 图片 evidence 绑定 `target_insight_index`，跳页后仍能命中正确洞察。
- 外部图源去重，避免多页复用同一 URL。
- 创作者增长、AI 技术、孤独心理内容可自动选择不同主题。
- 短文本页优先 M11/M09/M10，避免空白 M03。
- Editorial 16 个 recipe 都已有 renderer；新增 recipe 必须带结构测试。
- Swiss S01-S12 都已有专属 renderer；新增 Swiss 路由必须保留单 accent、hairline/grid、低字重大标题。
- Category cookbook 已有机器识别、scope notes 和 deck sequence；旅行、职场、游戏、影视、美食、彩妆、健身、家居、穿搭、情感、推荐至少要带 category hints。
- Category cookbook 不能被单个泛词触发；必须有显式标签/类别名或至少两项证据，避免把“技术路线”误判成旅行、“时间管理”误判成职场。
- WeChat Editorial 封面对已接入：21:9、1:1、pair preview 三画板同文件生成。
- S08 image hero 和 M16 image-led cover 自动路由必须有 `subject_map`；没有 subject map 的图片只能走非叠字 recipe。
- Swiss 洞见页若有真实证据图但没有 `subject_map`，只能进入非叠字 evidence panel，不能丢图回到纯文字页，也不能仅因“有图”强制改派 S04。
- Swiss S09 KPI Tower 至少需要 2 个真实数字；只有一个数字时优先回到 S03 File Card，避免单指标撑塔。
- Swiss S06 Pipeline 至少需要 3 个流程/枚举节点；中文顿号枚举可以拆成结构节点，节点不足时不得硬排三栏。
- 图上叠字 HTML 必须写入 `subject map` 和 `thumbnail policy`；静态 QA 会检查 R8/R9/R10。
- Swiss 数据型 recipe 会先抽原文真实数字；无真实数字时必须显式标记 `proxy`，不能伪装成事实指标。
- Swiss proxy metric 不得把 `P01/P02` 这类内部占位符渲染到页面；R14 会阻断。
- closing 不再塞 Archive Index。
- 重复文本渲染有回归测试；静态 QA 的 R11 会阻断单张卡片内部较长可见文案重复。
- scaffold label 泄露有回归测试；静态 QA 的 R12 会阻断 `注记/脉络/张力` 等内部标签进入最终卡片。
- Swiss closing CTA 已固定为 Chora Archive 组与 Rhizomata 组，不再把 URL、二维码、公众号名混成一组。
- 深色主题已有 `paper-wash` 和背景降噪。
- daily rewrite 后处理已接入 `distribution_pipeline.automation.generate_distribution_after_rewrite()`，失败写入 `distribution_errors.log` 并继续主流程。

## 后续落地顺序

1. 先做 3-5 篇真实文章回归导出，确认 `copy_slots`、R11/R12、尾卡 CTA 在不同题材下都稳定。
2. 进入“贴近原 Guizang 出图风格”：补原作者示例中的图文拼贴、留白控制、图像证据墙、账单/清单/行程类结构。
3. 对 WeChat 21:9 + 1:1 封面对做多文章抽检，继续收敛短标题规则。
4. 强化 M06/M12 与 screenshot/map 资产：多图墙、截图框、路线图仍需更细语义输入。
5. 把 thumbnail readability 从静态规则升级为真实 360px 缩略图像素检查。
6. 把 category cookbook 的 scope notes 写入更显式的用户侧提示或 manifest review。
7. 为 Swiss 数据型 recipe 增加更强的中文数字/货币/时间单位抽取。
