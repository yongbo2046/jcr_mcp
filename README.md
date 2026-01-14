# JCR分区表MCP服务器

基于 [ShowJCR](https://github.com/hitfyd/ShowJCR) 仓库数据的 Model Context Protocol (MCP) 服务器，为大语言模型提供最新的期刊分区表查询功能。

## 🎯 功能特性

### 🔧 工具 (Tools)

| 工具名称 | 功能描述 |
|---------|---------|
| `search_journal` | 搜索期刊信息，包括影响因子、分区、预警状态等 |
| `get_partition_trends` | 获取期刊分区变化趋势分析 |
| `check_warning_journals` | 查询国际期刊预警名单 |
| `compare_journals` | 对比多个期刊的综合信息 |
| `filter_journals` | 按分区、学科、影响因子等条件筛选期刊 |
| `batch_query_journals` | 批量查询多个期刊，支持JSON导出 |
| `check_data_update` | 检查远程数据源是否有更新 |
| `sync_database` | 一键同步最新数据库 |
| `get_available_categories` | 获取可用的学科分类列表 |

### 📋 资源 (Resources)
- **`jcr://database-info`** - 数据库基本信息和统计

### 💡 提示词 (Prompts)
- **`journal_analysis_prompt`** - 期刊分析专用提示词模板

---

## 🚀 快速安装

### 1. 克隆仓库
```bash
git clone https://github.com/yongbo2046/jcr_mcp.git
cd jcr_mcp
```

### 2. 环境准备
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 获取数据库
```bash
# 方式一：使用同步工具（推荐）
python data_sync.py

# 方式二：直接下载
curl -L "https://raw.githubusercontent.com/hitfyd/ShowJCR/master/中科院分区表及JCR原始数据文件/jcr.db" -o jcr.db
```

---

## 📖 工具使用说明

### 1. search_journal - 搜索期刊

搜索单个期刊的详细信息。

**参数：**
- `journal_name` (必填): 期刊名称，支持模糊搜索
- `year` (可选): 指定年份，如 "2025"

**示例：**
```
搜索 Nature 期刊的信息
搜索 2024 年的 Science 期刊数据
```

---

### 2. filter_journals - 按条件筛选期刊

根据多种条件筛选期刊列表，适合智能选刊。

**参数：**
| 参数 | 类型 | 说明 |
|-----|------|-----|
| `partition` | string | 分区筛选：1区、2区、Q1、Q2 等 |
| `min_if` | float | 最小影响因子 |
| `max_if` | float | 最大影响因子 |
| `category` | string | 学科大类：计算机科学、医学、化学 等 |
| `is_top` | bool | 是否Top期刊 |
| `is_oa` | bool | 是否开放获取期刊 |
| `year` | string | 数据年份，默认 2025 |
| `limit` | int | 返回数量限制，默认 50 |

**示例：**
```
筛选计算机科学领域的1区Top期刊
筛选影响因子5-10之间的医学期刊
筛选所有开放获取的2区期刊
```

---

### 3. batch_query_journals - 批量查询

一次查询多个期刊，支持导出为JSON格式。

**参数：**
- `journal_names` (必填): 期刊名称列表，用逗号或换行分隔
- `output_format` (可选): 输出格式，"text" 或 "json"

**示例：**
```
批量查询 Nature, Science, Cell 三个期刊
批量查询以下期刊并导出JSON：Nature, Science, PNAS
```

---

### 4. check_data_update - 检查更新

检查ShowJCR数据源是否有新版本。

**示例：**
```
检查期刊数据是否有更新
```

---

### 5. sync_database - 同步数据

从ShowJCR下载最新数据库，自动备份旧数据。

**示例：**
```
同步最新的期刊数据库
```

---

### 6. get_available_categories - 获取学科分类

查看指定年份可用的学科大类列表。

**参数：**
- `year` (可选): 数据年份，默认 2025

**可用学科分类：**
```
计算机科学、医学、化学、物理与天体物理、生物学、
材料科学、工程技术、数学、环境科学与生态学、
地球科学、农林科学、心理学、社会学、经济学、
管理学、教育学、历史学、文学、哲学、艺术学
```

---

### 7. 其他工具

| 工具 | 示例 |
|-----|------|
| `get_partition_trends` | 查看 Nature 期刊的分区变化趋势 |
| `check_warning_journals` | 查询预警期刊名单 |
| `compare_journals` | 对比 Nature 和 Science 期刊 |

---

## 🔌 多平台集成

### Claude Desktop
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

### Claude Code
```bash
claude mcp add jcr-partition --scope user -- /绝对路径/jcr_mcp/venv/bin/python /绝对路径/jcr_mcp/jcr_mcp_server.py
```

### Cherry Studio
1. 进入 **设置** -> **MCP Servers** -> **Add Server**
2. **类型**: 选择 `stdio`
3. **命令**: 填写虚拟环境 python 的绝对路径
4. **参数**: 填写 `jcr_mcp_server.py` 的绝对路径

---

## 🛠️ 常见问题

1. **绝对路径问题**: 配置时请使用绝对路径，避免相对路径导致找不到文件
2. **数据库不存在**: 运行 `sync_database` 工具或手动下载 jcr.db
3. **编码问题**: 已自动处理 UTF-8/GBK 编码

---

## 📄 许可证

本项目基于 MIT 许可证开源。

## 🤝 贡献

欢迎提交 Issue 或 Pull Request。

Fork 自 [yosh3289/jcr_mcp](https://github.com/yosh3289/jcr_mcp)
