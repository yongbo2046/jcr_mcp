import asyncio
import sqlite3
import os
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import httpx
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context

# 配置常量 - 使用脚本所在目录的绝对路径
SCRIPT_DIR = Path(__file__).parent.absolute()
DATABASE_PATH = str(SCRIPT_DIR / "jcr.db")
DATA_UPDATE_URL = "https://raw.githubusercontent.com/hitfyd/ShowJCR/master/中科院分区表及JCR原始数据文件/"

@dataclass
class JournalInfo:
    """期刊信息数据类"""
    journal_name: str
    impact_factor: Optional[float] = None
    partition: Optional[str] = None
    category: Optional[str] = None
    warning_status: Optional[str] = None
    ccf_level: Optional[str] = None
    year: Optional[str] = None

class JCRDatabase:
    """JCR数据库管理类"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        if not os.path.exists(self.db_path):
            # 如果数据库不存在，创建基本表结构
            conn = sqlite3.connect(self.db_path)
            conn.close()
    
    def search_journal(self, journal_name: str, year: Optional[str] = None) -> List[JournalInfo]:
        """搜索期刊信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results = []
        try:
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall()]
            
            # 在各个表中搜索期刊
            for table in tables:
                try:
                    # 检查表结构
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'Journal' not in columns:
                        continue
                    
                    # 构建查询语句
                    query = f"SELECT * FROM {table} WHERE Journal LIKE ? COLLATE NOCASE"
                    cursor.execute(query, (f"%{journal_name}%",))
                    
                    rows = cursor.fetchall()
                    column_names = [description[0] for description in cursor.description]
                    
                    for row in rows:
                        row_dict = dict(zip(column_names, row))
                        journal_info = self._parse_journal_info(row_dict, table)
                        if journal_info:
                            results.append(journal_info)
                
                except sqlite3.Error:
                    continue
        
        finally:
            conn.close()
        
        return results
    
    def _parse_journal_info(self, row_dict: Dict, table_name: str) -> Optional[JournalInfo]:
        """解析数据库行为期刊信息对象"""
        try:
            journal_name = row_dict.get('Journal', '')
            
            # 根据表名判断数据类型和年份
            impact_factor = None
            partition = None
            category = None
            warning_status = None
            ccf_level = None
            year = None
            
            # 辅助函数：查找包含关键字的列
            def find_column_value(keywords):
                for key, value in row_dict.items():
                    for keyword in keywords:
                        if keyword.lower() in key.lower():
                            return value
                return None
            
            # 解析年份
            if 'JCR' in table_name and 'FQBJCR' not in table_name:
                year = table_name.replace('JCR', '')
                # 动态查找 IF 和 Quartile 列（列名可能是 IF(2022)、IF Quartile(2022) 等格式）
                impact_factor = find_column_value(['IF(', 'IF '])
                partition = find_column_value(['Quartile', '分区'])
                category = find_column_value(['Category', '类别', 'SCIE', 'SSCI'])
            
            elif 'FQBJCR' in table_name:
                year = table_name.replace('FQBJCR', '')
                partition = find_column_value(['大类分区', '分区', 'Partition'])
                category = find_column_value(['学科', 'Subject', '大类'])
                impact_factor = find_column_value(['IF', '影响因子'])
            
            elif 'GJQKYJMD' in table_name:
                year = table_name.replace('GJQKYJMD', '')
                warning_status = find_column_value(['预警等级', '预警原因', 'Warning'])
            
            elif 'CCF' in table_name:
                year = table_name.replace('CCF', '')
                ccf_level = find_column_value(['CCF推荐类型', 'CCF', '等级'])
                category = find_column_value(['领域', 'Field'])
            
            return JournalInfo(
                journal_name=journal_name,
                impact_factor=impact_factor,
                partition=partition,
                category=category,
                warning_status=warning_status,
                ccf_level=ccf_level,
                year=year
            )
        
        except Exception:
            return None

# 初始化FastMCP服务器
app = FastMCP("jcr-partition-server", port=8080)
db = JCRDatabase()

@app.tool()
async def search_journal(journal_name: str, year: Optional[str] = None) -> str:
    """
    搜索期刊信息，包括影响因子、分区、预警状态等
    
    Args:
        journal_name: 期刊名称（支持模糊搜索）
        year: 指定年份（可选，如2025、2024、2023等）
    
    Returns:
        期刊的详细信息，包括各年份的分区、影响因子等数据
    """
    try:
        results = db.search_journal(journal_name, year)
        
        if not results:
            return f"未找到期刊 '{journal_name}' 的相关信息"
        
        # 按期刊名称和年份分组整理结果
        grouped_results = {}
        for result in results:
            key = result.journal_name
            if key not in grouped_results:
                grouped_results[key] = []
            grouped_results[key].append(result)
        
        output = []
        for journal, infos in grouped_results.items():
            output.append(f"\n📚 期刊名称: {journal}")
            output.append("=" * 50)
            
            # 按年份排序
            infos.sort(key=lambda x: x.year or "0000", reverse=True)
            
            for info in infos:
                year_str = f"【{info.year}年】" if info.year else "【未知年份】"
                output.append(f"\n{year_str}")
                
                if info.impact_factor:
                    output.append(f"  📊 影响因子: {info.impact_factor}")
                
                if info.partition:
                    output.append(f"  🏆 分区: {info.partition}")
                
                if info.category:
                    output.append(f"  📖 学科类别: {info.category}")
                
                if info.warning_status:
                    output.append(f"  ⚠️ 预警状态: {info.warning_status}")
                
                if info.ccf_level:
                    output.append(f"  🏅 CCF推荐等级: {info.ccf_level}")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"查询出错: {str(e)}"

@app.tool()
async def get_partition_trends(journal_name: str) -> str:
    """
    获取期刊分区变化趋势
    
    Args:
        journal_name: 期刊名称
    
    Returns:
        期刊历年分区变化趋势分析
    """
    try:
        results = db.search_journal(journal_name)
        
        if not results:
            return f"未找到期刊 '{journal_name}' 的相关信息"
        
        # 提取分区信息
        partition_data = []
        for result in results:
            if result.partition and result.year:
                partition_data.append((result.year, result.partition, result.journal_name))
        
        if not partition_data:
            return f"未找到期刊 '{journal_name}' 的分区信息"
        
        # 按年份排序
        partition_data.sort(key=lambda x: x[0])
        
        output = [f"📈 期刊分区变化趋势分析"]
        output.append("=" * 40)
        
        for year, partition, journal in partition_data:
            output.append(f"{year}年: {partition}")
        
        # 简单趋势分析
        if len(partition_data) > 1:
            output.append("\n📊 趋势分析:")
            first_partition = partition_data[0][1]
            last_partition = partition_data[-1][1]
            
            if "1区" in last_partition or "Q1" in last_partition:
                output.append("✅ 该期刊保持在顶级分区")
            elif "4区" in last_partition or "Q4" in last_partition:
                output.append("⚠️ 该期刊分区较低，发表需谨慎")
            else:
                output.append("📊 该期刊分区稳定，属于中等水平")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"分析出错: {str(e)}"

@app.tool()
async def check_warning_journals(keywords: Optional[str] = None) -> str:
    """
    查询国际期刊预警名单
    
    Args:
        keywords: 关键词（可选，用于筛选特定期刊）
    
    Returns:
        预警期刊列表及其预警原因
    """
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 获取预警表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'GJQKYJMD%'")
        warning_tables = [table[0] for table in cursor.fetchall()]
        
        if not warning_tables:
            return "未找到预警期刊数据表"
        
        output = ["🚨 国际期刊预警名单查询结果"]
        output.append("=" * 40)
        
        for table in sorted(warning_tables, reverse=True):
            year = table.replace('GJQKYJMD', '')
            output.append(f"\n📅 {year}年预警名单:")
            
            query = f"SELECT * FROM {table}"
            params = []
            
            if keywords:
                query += " WHERE Journal LIKE ? COLLATE NOCASE"
                params.append(f"%{keywords}%")
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]
            
            if rows:
                for row in rows:
                    row_dict = dict(zip(column_names, row))
                    journal_name = row_dict.get('Journal', '未知期刊')
                    warning_reason = row_dict.get('预警原因', row_dict.get('预警等级', '未知原因'))
                    output.append(f"  • {journal_name}: {warning_reason}")
            else:
                if keywords:
                    output.append(f"  无匹配 '{keywords}' 的预警期刊")
                else:
                    output.append("  该年度无预警期刊数据")
        
        conn.close()
        return "\n".join(output)
    
    except Exception as e:
        return f"查询预警期刊出错: {str(e)}"

@app.tool()
async def compare_journals(journal_list: str) -> str:
    """
    比较多个期刊的综合信息
    
    Args:
        journal_list: 期刊名称列表，用逗号分隔，如"Nature,Science,Cell"
    
    Returns:
        多个期刊的对比分析结果
    """
    try:
        journals = [j.strip() for j in journal_list.split(',')]
        
        if len(journals) < 2:
            return "请至少提供2个期刊名称进行比较"
        
        output = ["📊 期刊对比分析结果"]
        output.append("=" * 50)
        
        all_results = {}
        for journal in journals:
            results = db.search_journal(journal)
            all_results[journal] = results
        
        # 生成对比表格
        output.append(f"\n{'期刊名称':<30} {'最新影响因子':<15} {'最新分区':<15} {'预警状态':<15}")
        output.append("-" * 80)
        
        for journal, results in all_results.items():
            if not results:
                output.append(f"{journal:<30} {'无数据':<15} {'无数据':<15} {'无数据':<15}")
                continue
            
            # 获取最新数据
            latest_if = "无数据"
            latest_partition = "无数据"
            warning_status = "正常"
            
            for result in results:
                if result.impact_factor:
                    latest_if = str(result.impact_factor)
                if result.partition:
                    latest_partition = result.partition
                if result.warning_status:
                    warning_status = "⚠️预警"
                    break
            
            output.append(f"{journal:<30} {latest_if:<15} {latest_partition:<15} {warning_status:<15}")
        
        # 推荐建议
        output.append("\n💡 投稿建议:")
        for journal, results in all_results.items():
            if results:
                has_warning = any(r.warning_status for r in results)
                if has_warning:
                    output.append(f"  ❌ {journal}: 该期刊在预警名单中，不建议投稿")
                else:
                    latest_partition = None
                    for result in results:
                        if result.partition:
                            latest_partition = result.partition
                            break
                    
                    if latest_partition and ("1区" in latest_partition or "Q1" in latest_partition):
                        output.append(f"  ⭐ {journal}: 顶级期刊，强烈推荐")
                    elif latest_partition and ("2区" in latest_partition or "Q2" in latest_partition):
                        output.append(f"  ✅ {journal}: 优质期刊，推荐投稿")
                    else:
                        output.append(f"  📝 {journal}: 可考虑投稿")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"比较分析出错: {str(e)}"

@app.tool()
async def filter_journals(
    partition: Optional[str] = None,
    min_if: Optional[float] = None,
    max_if: Optional[float] = None,
    category: Optional[str] = None,
    is_top: Optional[bool] = None,
    is_oa: Optional[bool] = None,
    year: str = "2025",
    limit: int = 50
) -> str:
    """
    按条件筛选期刊列表

    Args:
        partition: 分区筛选，如"1区"、"2区"、"Q1"、"Q2"等
        min_if: 最小影响因子
        max_if: 最大影响因子
        category: 学科大类，如"计算机科学"、"医学"、"化学"等
        is_top: 是否Top期刊（仅对中科院分区有效）
        is_oa: 是否开放获取期刊
        year: 数据年份，默认2025
        limit: 返回结果数量限制，默认50

    Returns:
        符合条件的期刊列表
    """
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 优先使用中科院分区表（FQBJCR）
        table_name = f"FQBJCR{year}"

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            # 尝试使用JCR表
            table_name = f"JCR{year}"
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                conn.close()
                return f"未找到{year}年的期刊数据表"

        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]

        # 构建查询条件
        conditions = []
        params = []

        # 分区筛选
        if partition:
            if '大类分区' in columns:
                conditions.append("大类分区 LIKE ?")
                params.append(f"%{partition}%")
            elif any('Quartile' in col for col in columns):
                quartile_col = [col for col in columns if 'Quartile' in col][0]
                conditions.append(f'"{quartile_col}" LIKE ?')
                params.append(f"%{partition}%")

        # 学科筛选
        if category:
            if '大类' in columns:
                conditions.append("大类 LIKE ?")
                params.append(f"%{category}%")
            elif 'Category' in columns:
                conditions.append("Category LIKE ?")
                params.append(f"%{category}%")

        # Top期刊筛选
        if is_top is not None and 'Top' in columns:
            if is_top:
                conditions.append("Top = '是'")
            else:
                conditions.append("(Top = '否' OR Top IS NULL)")

        # OA筛选
        if is_oa is not None and 'Open Access' in columns:
            if is_oa:
                conditions.append('"Open Access" IS NOT NULL AND "Open Access" != \'\'')
            else:
                conditions.append('("Open Access" IS NULL OR "Open Access" = \'\')')

        # 构建SQL
        query = f"SELECT * FROM {table_name}"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        if not rows:
            conn.close()
            return "未找到符合条件的期刊"

        # 影响因子筛选（后处理，因为列名动态）
        results = []
        for row in rows:
            row_dict = dict(zip(column_names, row))

            # 查找影响因子
            if_value = None
            for key, value in row_dict.items():
                if 'IF' in key and value is not None:
                    try:
                        if_value = float(value)
                        break
                    except (ValueError, TypeError):
                        continue

            # 影响因子范围筛选
            if min_if is not None and (if_value is None or if_value < min_if):
                continue
            if max_if is not None and (if_value is None or if_value > max_if):
                continue

            results.append(row_dict)

        conn.close()

        if not results:
            return "未找到符合条件的期刊"

        # 格式化输出
        output = [f"🔍 筛选结果（{year}年数据，共{len(results)}条）"]
        output.append("=" * 50)

        for i, row in enumerate(results[:limit], 1):
            journal = row.get('Journal', '未知')
            partition_val = row.get('大类分区', row.get([k for k in row.keys() if 'Quartile' in k][0] if any('Quartile' in k for k in row.keys()) else '', ''))
            category_val = row.get('大类', row.get('Category', ''))
            top_val = row.get('Top', '')

            # 查找IF
            if_val = ''
            for key, value in row.items():
                if 'IF' in key and value:
                    if_val = str(value)
                    break

            output.append(f"\n{i}. {journal}")
            if partition_val:
                output.append(f"   分区: {partition_val}")
            if if_val:
                output.append(f"   IF: {if_val}")
            if category_val:
                output.append(f"   学科: {category_val}")
            if top_val == '是':
                output.append(f"   ⭐ Top期刊")

        return "\n".join(output)

    except Exception as e:
        return f"筛选出错: {str(e)}"


@app.tool()
async def batch_query_journals(journal_names: str, output_format: str = "text") -> str:
    """
    批量查询多个期刊信息，支持导出为JSON格式

    Args:
        journal_names: 期刊名称列表，用逗号或换行分隔
        output_format: 输出格式，"text"为文本格式，"json"为JSON格式（方便导出）

    Returns:
        批量查询结果
    """
    try:
        # 解析期刊名称列表
        names = []
        for name in journal_names.replace('\n', ',').split(','):
            name = name.strip()
            if name:
                names.append(name)

        if not names:
            return "请提供至少一个期刊名称"

        results_data = []

        for name in names:
            journal_results = db.search_journal(name)

            if journal_results:
                # 获取最新数据
                latest_info = {
                    "query": name,
                    "found": True,
                    "journal_name": journal_results[0].journal_name,
                    "impact_factor": None,
                    "partition": None,
                    "category": None,
                    "warning": False,
                    "years_data": []
                }

                for r in journal_results:
                    year_data = {"year": r.year}
                    if r.impact_factor:
                        year_data["if"] = r.impact_factor
                        if latest_info["impact_factor"] is None:
                            latest_info["impact_factor"] = r.impact_factor
                    if r.partition:
                        year_data["partition"] = r.partition
                        if latest_info["partition"] is None:
                            latest_info["partition"] = r.partition
                    if r.category:
                        year_data["category"] = r.category
                        if latest_info["category"] is None:
                            latest_info["category"] = r.category
                    if r.warning_status:
                        year_data["warning"] = r.warning_status
                        latest_info["warning"] = True

                    latest_info["years_data"].append(year_data)

                results_data.append(latest_info)
            else:
                results_data.append({
                    "query": name,
                    "found": False
                })

        # 输出格式
        if output_format.lower() == "json":
            return json.dumps(results_data, ensure_ascii=False, indent=2)

        # 文本格式输出
        output = [f"📋 批量查询结果（共{len(names)}个期刊）"]
        output.append("=" * 50)

        for data in results_data:
            if data["found"]:
                output.append(f"\n✅ {data['journal_name']}")
                if data["impact_factor"]:
                    output.append(f"   IF: {data['impact_factor']}")
                if data["partition"]:
                    output.append(f"   分区: {data['partition']}")
                if data["category"]:
                    output.append(f"   学科: {data['category']}")
                if data["warning"]:
                    output.append(f"   ⚠️ 存在预警记录")
            else:
                output.append(f"\n❌ {data['query']} - 未找到")

        output.append("\n" + "=" * 50)
        output.append("💡 提示: 使用 output_format='json' 可获取JSON格式，方便导出到Excel")

        return "\n".join(output)

    except Exception as e:
        return f"批量查询出错: {str(e)}"


@app.tool()
async def check_data_update() -> str:
    """
    检查ShowJCR数据源是否有更新

    Returns:
        数据源更新状态信息
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 检查远程数据库文件
            db_url = "https://raw.githubusercontent.com/hitfyd/ShowJCR/master/中科院分区表及JCR原始数据文件/jcr.db"

            response = await client.head(db_url, follow_redirects=True)

            if response.status_code == 200:
                remote_size = int(response.headers.get('content-length', 0))
                remote_modified = response.headers.get('last-modified', '未知')

                # 获取本地文件信息
                local_size = 0
                local_modified = "未知"
                if os.path.exists(DATABASE_PATH):
                    local_size = os.path.getsize(DATABASE_PATH)
                    local_modified = os.path.getmtime(DATABASE_PATH)
                    from datetime import datetime
                    local_modified = datetime.fromtimestamp(local_modified).strftime('%Y-%m-%d %H:%M:%S')

                output = ["🔄 数据更新检查"]
                output.append("=" * 40)
                output.append(f"\n📡 远程数据源:")
                output.append(f"   大小: {remote_size / 1024 / 1024:.2f} MB")
                output.append(f"   更新时间: {remote_modified}")
                output.append(f"\n💾 本地数据库:")
                output.append(f"   大小: {local_size / 1024 / 1024:.2f} MB")
                output.append(f"   更新时间: {local_modified}")

                if remote_size != local_size:
                    output.append(f"\n⚠️ 检测到数据可能有更新！")
                    output.append(f"💡 使用 sync_database 工具下载最新数据")
                else:
                    output.append(f"\n✅ 本地数据已是最新")

                return "\n".join(output)
            else:
                return f"无法连接数据源，状态码: {response.status_code}"

    except Exception as e:
        return f"检查更新出错: {str(e)}"


@app.tool()
async def sync_database() -> str:
    """
    从ShowJCR下载最新数据库文件

    Returns:
        同步结果
    """
    try:
        db_url = "https://raw.githubusercontent.com/hitfyd/ShowJCR/master/中科院分区表及JCR原始数据文件/jcr.db"

        output = ["🔄 开始同步数据库..."]

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(db_url, follow_redirects=True)

            if response.status_code == 200:
                # 备份旧数据库
                backup_path = DATABASE_PATH + ".backup"
                if os.path.exists(DATABASE_PATH):
                    import shutil
                    shutil.copy2(DATABASE_PATH, backup_path)
                    output.append("📦 已备份旧数据库")

                # 写入新数据库
                with open(DATABASE_PATH, 'wb') as f:
                    f.write(response.content)

                new_size = len(response.content) / 1024 / 1024
                output.append(f"✅ 下载完成，大小: {new_size:.2f} MB")

                # 验证数据库
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()

                output.append(f"📊 数据表数量: {len(tables)}")
                output.append("\n✅ 数据库同步成功！")

                return "\n".join(output)
            else:
                return f"下载失败，状态码: {response.status_code}"

    except Exception as e:
        return f"同步出错: {str(e)}"


@app.tool()
async def get_available_categories(year: str = "2025") -> str:
    """
    获取可用的学科分类列表

    Args:
        year: 数据年份，默认2025

    Returns:
        可用的学科大类列表
    """
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        table_name = f"FQBJCR{year}"
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))

        if not cursor.fetchone():
            conn.close()
            return f"未找到{year}年的数据"

        cursor.execute(f"SELECT DISTINCT 大类 FROM {table_name} WHERE 大类 IS NOT NULL ORDER BY 大类")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()

        output = [f"📚 可用学科分类（{year}年）"]
        output.append("=" * 30)
        for i, cat in enumerate(categories, 1):
            output.append(f"{i}. {cat}")

        return "\n".join(output)

    except Exception as e:
        return f"获取分类出错: {str(e)}"


@app.resource("jcr://database-info")
async def get_database_info() -> str:
    """获取数据库基本信息"""
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        
        info = ["📊 JCR分区表数据库信息"]
        info.append("=" * 30)
        info.append(f"数据库路径: {db.db_path}")
        info.append(f"数据表数量: {len(tables)}")
        info.append("\n📋 可用数据表:")
        
        for table in sorted(tables):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            info.append(f"  • {table}: {count} 条记录")
        
        conn.close()
        return "\n".join(info)
    
    except Exception as e:
        return f"获取数据库信息出错: {str(e)}"

@app.prompt()
async def journal_analysis_prompt(journal_name: str) -> str:
    """期刊分析专用提示词模板"""
    return f"""
你是一个专业的学术期刊分析专家。请基于提供的期刊数据，对期刊 {journal_name} 进行全面分析，包括：

1. 期刊基本信息分析
2. 影响因子变化趋势
3. 分区变化情况
4. 预警状态评估
5. 投稿建议

请用专业、客观的语言进行分析，并给出具体的投稿建议。
"""

if __name__ == "__main__":
    # 运行MCP服务器
    print("🚀 启动JCR分区表MCP服务器...")
    print(f"📊 数据库路径: {DATABASE_PATH}")
    print("🔧 可用工具:")
    print("  • search_journal - 搜索期刊信息")
    print("  • get_partition_trends - 获取分区趋势")
    print("  • check_warning_journals - 查询预警期刊")
    print("  • compare_journals - 对比期刊")
    print("  • filter_journals - 按条件筛选期刊 [新增]")
    print("  • batch_query_journals - 批量查询导出 [新增]")
    print("  • check_data_update - 检查数据更新 [新增]")
    print("  • sync_database - 同步最新数据 [新增]")
    print("  • get_available_categories - 获取学科分类 [新增]")
    print("💡 提示词模板: journal_analysis_prompt")
    print("📋 资源: jcr://database-info")
    print("\n⚡ 服务器启动中...")

    app.run(transport="stdio") 