# xyz-podcast-cards

将小宇宙 FM 播客单集提取为适合社交平台分享的**图文卡片**（封面 + 多页内容图）。

## 功能

- 免登录提取公开单集元数据（标题、ShowNotes、封面、时长等）
- 自动按章节/段落拆分内容，生成多张 1080×1440 卡片
- 可选使用登录凭证拉取官方逐字稿生成卡片
- 导出 `episode.json` 元数据

## 快速开始

### 安装

```bash
git clone https://github.com/xiao-ben/xyz-podcast-cards.git
cd xyz-podcast-cards
pip install -e .
```

### 生成卡片

```bash
# 查看单集信息
xyz-cards info "https://www.xiaoyuzhoufm.com/episode/<episode_id>"

# 从 ShowNotes / 简介生成图文卡片（免登录）
xyz-cards extract "https://www.xiaoyuzhoufm.com/episode/<episode_id>" -o ./output

# 控制单卡字数
xyz-cards extract <episode_id> -o ./output --max-chars 220

# AI 摘要 + 简笔漫画风精致卡片（sketch 小人）
xyz-cards comic <episode_id> -o ./output-comic

# Ian 小黑怪诞正文配图（16:9 白底手绘，见 skills/ian-xiaohei-illustrations）
xyz-cards xiaohei <episode_id> -o ./output-xiaohei --assets ./assets/e234-xiaohei-illustrations
```

### 使用逐字稿（可选）

部分单集提供官方逐字稿，需要小宇宙 App 登录凭证。复制 `credentials.example.json` 为 `credentials.json` 并填入：

```json
{
  "access_token": "your-access-token",
  "device_id": "your-device-id"
}
```

```bash
# 仅下载逐字稿
xyz-cards transcript <episode_id> --credentials ./credentials.json -o ./output-transcript

# 一键流水线：逐字稿 → 文本摘要 → 图文卡 + 漫画卡
xyz-cards pipeline <episode_id> --credentials ./credentials.json -o ./output-pipeline --style both

# 从逐字稿生成普通图文卡
xyz-cards extract <episode_id> --source transcript --credentials ./credentials.json -o ./output
```

> 凭证获取方式可参考 [OpenCLI 小宇宙文档](https://opencli.info/docs/adapters/browser/xiaoyuzhou.html)。请勿在公开场合分享 token。

## 输出示例

```
output/
├── 00_cover.png          # 封面卡：播客封面 + 标题
├── 01_section.png        # 内容卡：按章节拆分
├── 02_section.png
└── episode.json          # 元数据
```

## 工作原理

1. 请求小宇宙公开单集页面，解析 `__NEXT_DATA__` 中的 episode JSON
2. 将 `description` / `shownotes` 转为纯文本并按 emoji 章节标记切分
3. 使用 Pillow 渲染卡片（默认小红书竖版比例 1080×1440）

## 注意事项

- 仅供个人学习与非商业分享，请尊重播客创作者版权
- 请勿高频批量抓取，避免对平台造成压力
- 逐字稿接口需要有效登录态；公开单集元数据提取无需登录

## 开发

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
