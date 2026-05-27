# The Bazaar DLC 折扣监控推送系统

一个基于 **GitHub Actions + Steam API + Server酱 + cron-job.org** 实现的 *The Bazaar* 游戏 DLC 价格与折扣监控系统。24 小时云端全自动运行，无需本地开机或部署服务器，一旦有折扣立即推送至个人微信，且每天深夜发送总结日报。

---

## 🛠️ 实现原理

1. **价格获取 (Steam API)**：
   - 定时请求 Steam 官方公开 API 获取游戏 *The Bazaar* (AppID: `1617400`) 的详情。
   - 动态解析游戏名下的所有 DLC 列表，自动发现未来新上架的 DLC，无需修改代码。
2. **折扣状态比对 (防止重复报警)**：
   - 脚本在本地（云端）维护一个 `discount_status.json` 文件记录上一次的打折情况。
   - 发现有新的 DLC 进入折扣或折扣幅度变大时，触发**即时报警**。
   - 运行结束后，GitHub Actions 会自动通过 Bot 账户将更新后的 `discount_status.json` **提交并推回仓库**保存，确保下一次运行状态的连续性。
3. **外部精准触发 (cron-job.org)**：
   - **为什么切换到外部触发？**：GitHub 官方的定时器（Actions Schedule）存在严重的排队拥堵，往往会延迟半小时甚至一小时触发，甚至在刚创建新仓库时会有几小时的“冷启动”不触发期。
   - **触发原理**：使用完全免费的外部定时器 `cron-job.org`，通过 GitHub REST API 远程手动触发（`workflow_dispatch`）我们的工作流，从而实现**秒级精度**的定时监控。
4. **消息推送 (Server酱)**：
   - 触发折扣或每日总结时，调用 Server酱 接口，通过微信公众号“方糖”将打折信息直接以服务号卡片的形式推送至关注者的微信上。

---

## ⏰ 运行规则

- **即时折扣监控**：每小时第 12 分钟运行。若无新增折扣，保持静默，**不浪费 Server酱 免费额度**；若有新增折扣，微信即时报警。
- **每日总结日报**：每天北京时间晚上 **23:30** 定时运行。无论是否打折，都会将所有 DLC 的当前最新价格以列表形式发送到微信。

---

## 🚀 部署与使用步骤

### 1. 获取 Server酱 SendKey
1. 扫码登录 [Server酱 官网](https://sct.ftqq.com/)。
2. 配置好通道，关注 **“方糖”** 公众号。
3. 复制您的 **SendKey**（通常以 `SCT` 开头）。

### 2. 配置 GitHub 仓库密钥 (Secrets)
为了保证密钥安全，切勿将 `SendKey` 直接写在代码中提交。
1. 进入您当前的 GitHub 仓库页面（如 `EndeRHoshI/BazaarDiscountMonitor`）。
2. 依次点击：**`Settings` -> `Secrets and variables` -> `Actions`**。
3. 点击 **`New repository secret`**。
4. 填写：
   - **Name**: `SERVERCHAN_SENDKEY`
   - **Value**: 填入您的 `SendKey`（多个人接收可以用英文逗号隔开，例如 `KEY1,KEY2`）。
5. 保存即可。

### 3. 配置 cron-job.org 外部定时器（解决 GitHub 定时延迟/不触发）

#### 第一步：生成 GitHub 个人访问令牌 (Token)
我们需要给外部定时器授予触发 GitHub 工作流的权限：
1. 登录 GitHub -> 点击右上角头像 -> **`Settings` (设置)**。
2. 滚动到最左下角，点击 **`Developer settings` (开发者设置)**。
3. 选择 **`Personal access tokens`** -> 点击 **`Tokens (classic)`**。
4. 点击 **`Generate new token (classic)`**，**`Note`** 填入 `cron-trigger`，勾选 **`workflow`** 权限。
5. 点击最下方生成按钮，**复制生成的 `ghp_xxxx` 开头的 Token**（页面关闭后将无法查看，请妥善保存）。

#### 第二步：在 cron-job.org 配置触发任务
1. 打开并注册 [cron-job.org](https://cron-job.org/)（完全免费）。
2. 点击 **`Create Cronjob`**：
   - **Title**: `Bazaar Monitor`
   - **URL**: `https://api.github.com/repos/EndeRHoshI/BazaarDiscountMonitor/actions/workflows/monitor.yml/dispatches`
   - **Request method**: 选择 **`POST`**。
   - **Schedule**: 选择 `Every hour`（每小时）或自定义具体分钟（如每小时第 12 分钟）。
3. 切换到 **`ADVANCED`** 选项卡：
   - 关闭 **`Requires HTTP authentication`** 开关（置灰状态）。
   - 在 **`Headers`** 区域，点击 **`+ ADD`** 依次添加以下 4 个 Header：
     
     | Header Key | Header Value |
     | :--- | :--- |
     | `Accept` | `application/vnd.github+json` |
     | `Authorization` | `Bearer 您的ghp_xxxxToken` *(注意 Bearer 与 Token 间有空格)* |
     | `User-Agent` | `cron-job-trigger` |
     | `Content-Type` | `application/json` |

   - 在 **`Request body`** 文本框中，输入：
     ```json
     {"ref": "main"}
     ```
4. 点击底部的 **`Create`** 保存即可。

---

## 💻 本地调试与手动运行

如果您想在本地运行或者手动在云端测试：

### 1. 本地手动运行

```bash
# 1. 安装依赖
pip3 install requests

# 2. 模拟每小时折扣监控（若没有折扣，仅在控制台输出“监控中：无新打折信息。”）
python3 monitor.py

# 3. 强制发送一次每日日报到您的微信
SERVERCHAN_SENDKEY="您的SendKey" python3 monitor.py --daily
```

### 2. 云端手动触发 (GitHub 页面)
1. 在您的 GitHub 仓库页面，点击顶部的 **`Actions`** 选项卡。
2. 在左侧列表选择 **`The Bazaar Discount Monitor`** 工作流。
3. 点击右侧淡蓝色的 **`Run workflow`** 下拉菜单，您会看到一个 **`请选择运行类型`** 的下拉菜单：
   - **`monitor`（默认）**：执行正常的每小时静默监控。如果没有新折扣，微信不会收到消息（可在 Action 运行日志中看到输出），**不消耗 Server酱 额度**。
   - **`daily`**：**强制向您的微信发送一份当前的折扣总结日报**（即使没有打折也会发送，用于测试或临时看价格，会消耗 1 次额度）。
4. 点击绿色的 **`Run workflow`** 按钮启动。
