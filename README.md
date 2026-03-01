# 微信读书 → Notion 自动同步工具

自动将微信读书的划线笔记和想法同步到 Notion 数据库，并用 AI 自动生成主题标签。通过 GitHub Actions 每天自动运行。

## 功能

- **增量同步**：只同步新增内容，不会覆盖已有笔记
- **按章节组织**：划线和想法按书籍章节结构排列
- **AI 主题标签**：自动为每本书生成主题标签（如"思维方式""认知科学"）
- **Notion AI 检索**：同步到 Notion 后可用 Notion AI 语义搜索

## 设置步骤

### 1. 创建 Notion Integration

1. 打开 https://www.notion.so/my-integrations
2. 点击 "New integration"
3. 名称填 `WeRead Sync`，选择你的 workspace
4. 创建后复制 **Internal Integration Secret**（以 `ntn_` 开头）→ 这就是 `NOTION_TOKEN`

### 2. 创建 Notion 数据库

在 Notion 中创建一个新的 **Database（Full page）**，添加以下属性：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| 书名 | Title | 默认已有 |
| 作者 | Text | 新建 |
| 分类 | Select | 新建 |
| 主题标签 | Multi-select | 新建 |
| 笔记数量 | Number | 新建 |
| 最后同步 | Date | 新建 |
| BookId | Text | 新建 |

然后：
1. 点击数据库右上角 `···` → `Connections` → 添加你刚创建的 `WeRead Sync` integration
2. 复制数据库的 URL，格式为 `https://www.notion.so/xxx?v=yyy`，其中 `xxx` 就是 `NOTION_DATABASE_ID`

### 3. 获取微信读书 Cookie

1. 在浏览器中打开 https://weread.qq.com/ 并登录
2. 按 F12 打开开发者工具 → 切换到 Network 标签
3. 刷新页面，点击任意一个请求到 `i.weread.qq.com` 的请求
4. 在 Request Headers 中找到 `Cookie` 字段，复制完整内容 → 这就是 `WEREAD_COOKIE`

> ⚠️ Cookie 大约 1-2 周会过期，过期后需要重新获取并更新 GitHub Secret。

### 4. 获取 Anthropic API Key（可选，用于 AI 标签）

1. 打开 https://console.anthropic.com/
2. 创建 API Key → 这就是 `ANTHROPIC_API_KEY`

> 不配置也能用，只是不会自动打标签。

### 5. 配置 GitHub

1. Fork 或 clone 本仓库到你的 GitHub
2. 进入仓库 Settings → Secrets and variables → Actions
3. 添加以下 Secrets：
   - `WEREAD_COOKIE` — 微信读书 cookie
   - `NOTION_TOKEN` — Notion integration token
   - `NOTION_DATABASE_ID` — Notion 数据库 ID
   - `ANTHROPIC_API_KEY` — Anthropic API key（可选）

### 6. 运行

- **自动运行**：每天北京时间 8:00 自动同步
- **手动运行**：进入 Actions 标签 → WeRead to Notion Sync → Run workflow

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export WEREAD_COOKIE="你的cookie"
export NOTION_TOKEN="你的token"
export NOTION_DATABASE_ID="你的数据库id"
export ANTHROPIC_API_KEY="你的apikey"  # 可选

# 运行
cd src
python main.py
```

## Cookie 过期怎么办？

当 GitHub Actions 运行失败，日志中出现 "cookie 已过期" 提示时：

1. 重新登录 https://weread.qq.com/
2. 按上面第 3 步获取新 cookie
3. 更新 GitHub Secret 中的 `WEREAD_COOKIE`
4. 手动触发一次 workflow 验证
