# wechat-news-publisher

基于多轮微信公众号文章写作、改稿、配图、封面及 GitHub 归档反馈，提炼的可复用 Agent Skill（兼容 Agent Skills 标准）。

## 适用范围

- 从新闻截图、X 帖、官方博客、GitHub 项目研究并写成公众号文章。
- 标题有吸引力但不过分浮夸，正文必须兑现标题并进行深入分析。
- 真实正文配图；无文字、2.35:1、**不嵌入正文**的独立封面。
- 按日期及文章编号维护 GitHub 仓库 `dericklau3/global-insights`。
- 对既有文章做标题优化、全文重写和规范性删除。

## 在本仓库中使用

本 Skill 已放在 `.agents/skills/wechat-news-publisher/`，适合在仓库根目录使用 Codex 时加载。可在项目中直接请求：

```text
使用 wechat-news-publisher skill，研究这条新闻，把文章和独立封面写入 global-insights 的当天目录。
```

如果要在任意项目中复用，可在 macOS 中将该目录复制或软链接到 `~/.agents/skills/wechat-news-publisher/`，然后开启新的 Codex 会话。

## 安装到 Codex（macOS）

下载 `wechat-news-publisher.zip`，在 ZIP 所在目录的终端执行：

```bash
mkdir -p ~/.agents/skills
unzip -o wechat-news-publisher.zip -d ~/.agents/skills/
```

正确路径应为：

```text
~/.agents/skills/wechat-news-publisher/SKILL.md
```

新开 Codex 会话；如果技能列表暂未刷新，重启 Codex。

另一种用法是将整个 `wechat-news-publisher/` 文件夹放进你当前 Codex 工作环境支持的项目级 skills 目录。其他支持 Agent Skills 的客户端参照其本地 skills 目录设置。

**注意：下载 Skill 并不等于已经安装到你的 Mac。** Skill 只是写作和执行规范，联网研究、GitHub 提交及图片生成仍取决于代理实际可使用的工具和授权。

## 示例指令

```text
使用 wechat-news-publisher skill，研究这条 X post，写一篇适合公众号发布的深度文章，并制作一张无文字封面。
```

```text
使用 wechat-news-publisher skill，把这 3 条新闻整理到 global-insights 的今天日期目录下，每篇一个序号文件，正文含真实图片，封面独立存放，完成后提交 GitHub。
```

```text
按 wechat-news-publisher 的规范，重新打磨这篇文章标题，并根据新标题完整重写正文。不要在文章末尾写资料来源。
```

## 文件说明

```text
wechat-news-publisher/
├── SKILL.md                         # 核心触发描述与必守规则
├── README.md                        # 本文件：安装及调用
├── references/
│   ├── editorial-guide.md           # 标题、正文、深度与微信排版
│   ├── image-guide.md               # 官方素材、无字封面、正文配图
│   └── research-and-github.md       # 事实核查与 GitHub 提交
├── assets/
│   ├── article-template.md          # 可复用稿件骨架
│   └── research-notes-template.md   # 内部研究底稿（不得放正文）
└── scripts/
    └── check_article.py            # Markdown 静态检查工具
```

## 文章自检

```bash
python3 ~/.agents/skills/wechat-news-publisher/scripts/check_article.py \
  /path/to/global-insights/10-14/01_example.md
```

返回码为 `0` 表示通过静态规则；并不表示事实已经被核实或图片可以合法使用。