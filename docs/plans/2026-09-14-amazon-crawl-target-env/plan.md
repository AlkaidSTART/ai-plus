# Amazon 爬取目标地址环境变量配置：实施计划

## 目标

将用户提供的 Google 广告跳转链接中嵌入的 Amazon 商品目标地址，以环境变量 `AMAZON_CRAWL_TARGET_URL` 写入根目录 `.env.local`；在根目录 `.env.example` 中仅登记同名变量和非敏感占位值，不出现真实商品 ID，也不写入 Google 广告参数。

## 当前事实及依据

- 根目录同时存在 `.env.local` 与 `.env.example`，当前均为 0 字节；`ls -la` 已确认。
- 根目录 `.gitignore` 已忽略 `.env.local`，未忽略 `.env.example`。
- `backend/src/insightx/crawler/config.py` 当前只定义 MongoDB、输出目录、超时和无头模式等 `CrawlerSettings` 字段，没有 Amazon 目标地址字段；`backend/src/insightx/crawler/__main__.py` 的 `--url` 仍是必填 CLI 参数。
- 用户提供的链接外层是 Google 广告跳转地址，最终 Amazon 商品地址为 `https://www.amazon.com/gp/product/B0052TBWM4`，后续参数是 Google/Amazon 跟踪参数。
- 本次最小解释为：只登记运行目标地址，不改造爬虫配置读取和 CLI 行为；不把 Google 跳转地址或跟踪参数写入环境文件。

## 预计变更文件

- `.env.local`：新增一行 `AMAZON_CRAWL_TARGET_URL=https://www.amazon.com/gp/product/B0052TBWM4`。该文件已被 Git 忽略，不提交。
- `.env.example`：新增一行 `AMAZON_CRAWL_TARGET_URL=https://www.amazon.com/gp/product/<ASIN>`，作为非敏感示例；`<ASIN>` 是占位符，不包含 `B0052TBWM4`，也不包含任何用户提供的广告参数或标识。
- 不修改后端代码、测试、README、PRD、架构文档或其他配置文件。

## 实施步骤与分工

1. 主代理追加 `.env.local` 的唯一环境变量行，值使用 Amazon 商品直链 `https://www.amazon.com/gp/product/B0052TBWM4`。
2. 主代理追加 `.env.example` 的同名变量行，值只使用占位符 URL `https://www.amazon.com/gp/product/<ASIN>`。
3. 主代理检查变量键名一致，且示例文件未出现真实 ASIN、Google `gclid`、`gbraid`、`ved` 或 `adurl` 等值。
4. 本任务无需子代理；变更仅涉及两个根目录环境文件，拆分委派不会产生实质并行收益。

## 验证与验收

1. 使用只输出变量键名、不输出值的命令确认两个文件都包含 `AMAZON_CRAWL_TARGET_URL`。
2. 读取 `.env.local` 并在内存中验证其值恰为 `https://www.amazon.com/gp/product/B0052TBWM4`；验证输出只显示 `ok`，不回显真实值。
3. 对 `.env.example` 执行文本检查，确认包含 `<ASIN>` 占位符，且不包含 `B0052TBWM4`、`gclid=`、`gbraid=`、`adurl=`。
4. 对 `.env.local` 执行 Git ignore 检查，确认真实环境文件不会进入普通 Git 变更集合。
5. 验收条件：两个文件的变量名一致；本地文件保存正确 Amazon 直链；示例文件不含真实商品 ID 和广告跟踪参数；除两个环境文件与本次 `plan.md`/`result.md` 外无文件变化。

## 风险与非目标

- `CrawlerSettings` 目前没有读取 `AMAZON_CRAWL_TARGET_URL`，CLI 的 `--url` 仍为必填；本次只是可靠地登记目标地址，不承诺执行 `python -m insightx.crawler` 时会自动采用该变量。
- 商品链接可能随时间失效、改版或触发 Amazon 反爬；本任务不验证真实 Amazon 抓取、登录、验证码、代理或合规性。
- 非目标：不新增配置字段、不修改 CLI、不新增测试、不重构环境配置、不提交 Git、不推送、不创建 PR。

## 审核状态

- 状态：待审核
- 创建日期：2026-09-14
- 批准信息：未批准
