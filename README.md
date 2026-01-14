# JCR分区表MCP服务器

基于 [ShowJCR](https://github.com/hitfyd/ShowJCR) 仓库数据的 Model Context Protocol (MCP) 服务器，为大语言模型提供最新的期刊分区表查询功能。

## 🎯 功能特性

### 🔧 工具 (Tools)
- **`search_journal`** - 搜索期刊信息，包括影响因子、分区、预警状态等
- **`get_partition_trends`** - 获取期刊分区变化趋势分析
- **`check_warning_journals`** - 查询国际期刊预警名单
- **`compare_journals`** - 对比多个期刊的综合信息

### 📋 资源 (Resources)
- **`jcr://database-info`** - 数据库基本信息和统计

### 💡 提示词 (Prompts)
- **`journal_analysis_prompt`** - 期刊分析专用提示词模板

---

## 🚀 快速安装

### 1. 环境准备
推荐使用虚拟环境：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 获取数据库
如果 `python data_sync.py` 因 GitHub 链接变更失败，请直接下载现成的数据库文件：
```bash
curl -L "https://raw.githubusercontent.com/hitfyd/ShowJCR/master/中科院分区表及JCR原始数据文件/jcr.db" -o jcr.db
```

---

## 🔌 多平台集成

### 1. Claude Desktop
在 `~/Library/Application Support/Claude/claude_desktop_config.json` 中添加：
```json
{
  "mcpServers": {
    "jcr-partition": {
      "command": "/绝对路径/jcr_mcp/venv/bin/python",
      "args": ["/绝对路径/jcr_mcp/jcr_mcp_server.py"],
      "cwd": "/绝对路径/jcr_mcp"
    }
  }
}
```

### 2. Claude Code
全局添加：
```bash
claude mcp add jcr-partition --scope user -- /绝对路径/jcr_mcp/venv/bin/python /绝对路径/jcr_mcp/jcr_mcp_server.py
```

### 3. Cherry Studio
1. 进入 **设置** -> **MCP Servers** -> **Add Server**
2. **类型**: 选择 `stdio`
3. **命令**: 填写虚拟环境 python 的绝对路径
4. **参数**: 填写 `jcr_mcp_server.py` 的绝对路径

---

## 🛠️ 已修复的常见坑 (Troubleshooting)

本项目已针对以下常见问题进行了优化：

1. **绝对路径修复**: 解决了 Cherry Studio 等客户端从非项目目录启动时无法找到 `jcr.db` 的问题。
2. **动态列名匹配**: 修复了原始代码无法识别 ShowJCR 数据库中带年份列名（如 `IF(2022)`、`IF Quartile(2022)`）的 Bug。
3. **多语言编码**: 强化了对 CSV 数据源 UTF-8/GBK 编码的自动识别。

## 许可证
本项目基于 MIT 许可证开源。

## 贡献
欢迎提交 Issue 或 Pull Request。已在原始仓库提交 [Issue #1](https://github.com/yosh3289/jcr_mcp/issues/1) 记录相关改进。
