# 多平台采集目标地址环境变量配置：实施计划

## 目标

在现有 Amazon 目标地址登记方案基础上，将 eBay、Walmart、Temu、AliExpress、SHEIN、TikTok Shop 一并登记为可配置的采集目标地址。范围仅限根目录环境文件中的 URL 变量登记：

- 本地环境文件登记 7 个平台的实际目标 URL。
- 示例环境文件登记同名变量与非敏感占位值。
- 不改造爬虫读取配置、CLI、API、前端或任何平台的抽取逻辑。

## 当前事实及依据

- 原计划位于本目录，标题为“Amazon 爬取目标地址环境变量配置：实施计划”，审核状态为“待审核”，批准信息为“未批准”；原计划尚未执行，现因用户新增目标平台而作范围修订。
- 根目录示例环境文件当前为 181 字节，包含 MONGODB_URI、MONGODB_DATABASE、MONGODB_DOM_COLLECTION、CRAWLER_OUTPUT_DIR、CRAWLER_TIMEOUT_MS、CRAWLER_HEADLESS 六个现有变量；尚未包含任何采集目标 URL 变量。
- 根目录本地环境文件当前为 0 字节，且 .gitignore 已忽略该文件，不会进入普通 Git 变更集合。
- backend/src/insightx/crawler/config.py 的 CrawlerSettings 当前没有 *_CRAWL_TARGET_URL 字段。
- backend/src/insightx/crawler/__main__.py 当前要求通过 --url 显式传入单次爬取地址。
- backend/src/insightx/crawler/service.py 的 validate_http_url 接受任意绝对 HTTP(S) URL，当前没有平台域名白名单。
- 后端 API 与前端目前只暴露 Amazon US；README、PRD、docs/architecture.md 将非 Amazon 平台适配描述为后续能力，不能把本次配置登记解释为已完成多平台抓取实现。
- 工作区当前存在与本任务无关的既存未跟踪目录 backend/src/insightx/services/；本任务不得修改或清理该目录。

## 预计变更文件

- docs/plans/2026-09-14-amazon-crawl-target-env/plan.md：本次审核前更新任务范围、事实、步骤和验收标准。
- .env.local：获批后仅幂等追加下列 7 个变量；已有同名变量一律保留，不覆盖、不改写已有值：
  - AMAZON_CRAWL_TARGET_URL=https://www.amazon.com/gp/product/B0052TBWM4
  - EBAY_CRAWL_TARGET_URL=https://www.ebay.com/
  - WALMART_CRAWL_TARGET_URL=https://www.walmart.com/
  - TEMU_CRAWL_TARGET_URL=https://www.temu.com/
  - ALIEXPRESS_CRAWL_TARGET_URL=https://www.aliexpress.com/
  - SHEIN_CRAWL_TARGET_URL=https://www.shein.com/
  - TIKTOK_SHOP_CRAWL_TARGET_URL=https://shop.tiktok.com/
- .env.example：获批后仅幂等追加下列 7 个同名变量和非敏感占位值：
  - AMAZON_CRAWL_TARGET_URL=https://www.amazon.com/gp/product/<ASIN>
  - EBAY_CRAWL_TARGET_URL=https://www.ebay.com/<SEARCH_OR_ITEM_PATH>
  - WALMART_CRAWL_TARGET_URL=https://www.walmart.com/<SEARCH_OR_ITEM_PATH>
  - TEMU_CRAWL_TARGET_URL=https://www.temu.com/<SEARCH_OR_PRODUCT_PATH>
  - ALIEXPRESS_CRAWL_TARGET_URL=https://www.aliexpress.com/<SEARCH_OR_ITEM_PATH>
  - SHEIN_CRAWL_TARGET_URL=https://www.shein.com/<SEARCH_OR_PRODUCT_PATH>
  - TIKTOK_SHOP_CRAWL_TARGET_URL=https://shop.tiktok.com/<SHOP_OR_PRODUCT_PATH>
- docs/plans/2026-09-14-amazon-crawl-target-env/result.md：仅在实施和验证完成后按真实结果创建。

## 实施步骤与分工

1. 主代理在实施前重新读取两个环境文件，建立变量键名和既有值的只读基线；确认本地文件仍不包含待新增键，示例文件仍只有既有 6 个键。
2. 主代理以幂等方式更新本地环境文件：逐行检查每个键是否已存在；仅追加缺失键；遇到同名键时保留原行并记录为“既有值未覆盖”。不修改原有 MONGODB、CRAWLER 配置。
3. 主代理以同样的幂等方式更新示例环境文件：只追加缺失的目标 URL 键，使用上述非敏感占位值，不覆盖已有键，不加入真实 ASIN、商品路径或广告参数。
4. 主代理执行静态验证，确认 7 个键在两个文件中齐全、两个文件的键名一致、示例值均为占位形式、真实收集值通过 HTTP(S) URL 解析、广告诉求参数未写入示例文件。
5. 主代理检查 Git 忽略行为和工作区差异，确认本地环境文件未被普通 Git 跟踪，且除获批文件与既存未跟踪目录外无额外修改。
6. 本任务不需要子代理：变更集中在两个根目录环境文件和同目录计划/结果文档，拆分会造成重叠写入而没有实质并行收益。

## 验证与验收

1. 使用只输出键名的命令分别读取两个环境文件，逐项核对上述 7 个变量；不得输出本地环境文件中无关变量的值。
2. 使用 Python 标准库 urllib.parse 对 7 个拟登记 URL 做静态校验，要求 scheme 为 http 或 https、hostname 非空；不发起网络请求，不验证页面可抓取性。
3. 对示例环境文件检查：7 个值均含对应占位符，不含 B0052TBWM4、gclid=、gbraid=、adurl= 或 ved=。
4. 对本地环境文件执行 Git 忽略检查，确认其被 .gitignore 的现有规则匹配。
5. 执行 git status --short，并与计划阶段基线对比：只允许出现本次获批文件变化；预先存在的 backend/src/insightx/services/ 未跟踪状态保持原样。
6. 验收条件：两文件均包含 7 个同名变量；本地文件记录 7 个目标根地址或指定 Amazon 商品地址；同名已有值没有被覆盖；示例文件只含非敏感占位符；没有多平台抓取实现、API 或前端变更。

## 风险与非目标

- 当前 CrawlerSettings 不读取这些变量，CLI 仍要求 --url；本次只登记目标地址，不承诺运行爬虫时自动按平台选择或使用这些变量。
- eBay、Walmart、Temu、AliExpress、SHEIN、TikTok Shop 的页面结构、反爬策略、登录墙、地区跳转和抓取合规性均未验证；本次不发起真实抓取测试。
- SHEIN、TikTok Shop 等根地址可能发生地区重定向或随时间变化；本次只登记用户当前要求的平台入口。
- 非目标：不新增 CrawlerSettings 字段；不修改 CLI；不修改后端 API、任务模型、数据库、前端选择器或评论抽取；不实现平台适配器；不新增依赖；不提交、推送、创建 PR 或部署。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-14
- 批准信息：用户于 2026-09-14 回复“开始”，明确批准本计划执行。
