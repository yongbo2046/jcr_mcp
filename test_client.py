#!/usr/bin/env python3
"""
JCR分区表MCP客户端测试脚本
演示如何使用MCP客户端调用JCR分区表服务器
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 服务器参数配置
server_params = StdioServerParameters(
    command="python",
    args=["jcr_mcp_server.py"],
    env=None,
)

async def test_mcp_server():
    """测试MCP服务器的各项功能"""
    
    print("🚀 连接到JCR分区表MCP服务器...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("✅ 服务器连接成功！\n")
            
            # 1. 测试工具列表
            print("📋 获取可用工具...")
            tools_response = await session.list_tools()
            print(f"发现 {len(tools_response.tools)} 个工具:")
            for tool in tools_response.tools:
                print(f"  • {tool.name}: {tool.description}")
            print()
            
            # 2. 测试资源列表
            print("📦 获取可用资源...")
            resources_response = await session.list_resources()
            print(f"发现 {len(resources_response.resources)} 个资源:")
            for resource in resources_response.resources:
                print(f"  • {resource.uri}: {resource.description}")
            print()
            
            # 3. 测试提示词模板
            print("💡 获取可用提示词...")
            prompts_response = await session.list_prompts()
            print(f"发现 {len(prompts_response.prompts)} 个提示词:")
            for prompt in prompts_response.prompts:
                print(f"  • {prompt.name}: {prompt.description}")
            print()
            
            # 4. 测试期刊搜索功能
            print("🔍 测试期刊搜索功能...")
            test_journals = ["Nature", "Science", "Cell", "PNAS"]
            
            for journal in test_journals:
                print(f"\n📚 搜索期刊: {journal}")
                try:
                    result = await session.call_tool("search_journal", {
                        "journal_name": journal
                    })
                    print(result.content[0].text)
                    print("-" * 50)
                except Exception as e:
                    print(f"❌ 搜索失败: {e}")
            
            # 5. 测试分区趋势分析
            print("\n📈 测试分区趋势分析...")
            try:
                result = await session.call_tool("get_partition_trends", {
                    "journal_name": "Nature"
                })
                print(result.content[0].text)
            except Exception as e:
                print(f"❌ 趋势分析失败: {e}")
            
            # 6. 测试预警期刊查询
            print("\n🚨 测试预警期刊查询...")
            try:
                result = await session.call_tool("check_warning_journals", {
                    "keywords": None
                })
                print(result.content[0].text[:500] + "..." if len(result.content[0].text) > 500 else result.content[0].text)
            except Exception as e:
                print(f"❌ 预警查询失败: {e}")
            
            # 7. 测试期刊对比
            print("\n📊 测试期刊对比...")
            try:
                result = await session.call_tool("compare_journals", {
                    "journal_list": "Nature,Science,Cell"
                })
                print(result.content[0].text)
            except Exception as e:
                print(f"❌ 期刊对比失败: {e}")
            
            # 8. 测试数据库信息资源
            print("\n📊 获取数据库信息...")
            try:
                content = await session.read_resource("jcr://database-info")
                print(content[1][0].text)
            except Exception as e:
                print(f"❌ 获取数据库信息失败: {e}")
            
            # 9. 测试提示词模板
            print("\n💡 测试提示词模板...")
            try:
                prompt = await session.get_prompt("journal_analysis_prompt", {
                    "journal_name": "Nature"
                })
                print("生成的提示词:")
                print(prompt.messages[0].content.text)
            except Exception as e:
                print(f"❌ 提示词生成失败: {e}")

async def interactive_mode():
    """交互模式，允许用户实时查询"""
    
    print("🔍 进入交互查询模式...")
    print("输入 'quit' 退出，输入 'help' 查看帮助")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            while True:
                try:
                    user_input = input("\n请输入期刊名称: ").strip()
                    
                    if user_input.lower() == 'quit':
                        print("👋 再见！")
                        break
                    
                    if user_input.lower() == 'help':
                        print("""
📋 可用命令:
  • 直接输入期刊名称 - 搜索期刊信息
  • compare:期刊1,期刊2,期刊3 - 对比多个期刊
  • trends:期刊名称 - 查看分区趋势
  • warning:关键词 - 查询预警期刊
  • info - 查看数据库信息
  • quit - 退出程序
                        """)
                        continue
                    
                    if not user_input:
                        continue
                    
                    # 解析用户命令
                    if user_input.startswith("compare:"):
                        journal_list = user_input[8:].strip()
                        result = await session.call_tool("compare_journals", {
                            "journal_list": journal_list
                        })
                        print(result.content[0].text)
                    
                    elif user_input.startswith("trends:"):
                        journal_name = user_input[7:].strip()
                        result = await session.call_tool("get_partition_trends", {
                            "journal_name": journal_name
                        })
                        print(result.content[0].text)
                    
                    elif user_input.startswith("warning:"):
                        keywords = user_input[8:].strip()
                        result = await session.call_tool("check_warning_journals", {
                            "keywords": keywords if keywords else None
                        })
                        print(result.content[0].text)
                    
                    elif user_input.lower() == "info":
                        content = await session.read_resource("jcr://database-info")
                        print(content[1][0].text)
                    
                    else:
                        # 默认搜索期刊
                        result = await session.call_tool("search_journal", {
                            "journal_name": user_input
                        })
                        print(result.content[0].text)
                
                except KeyboardInterrupt:
                    print("\n👋 用户中断，再见！")
                    break
                except Exception as e:
                    print(f"❌ 查询出错: {e}")

async def main():
    """主函数"""
    print("🎯 JCR分区表MCP客户端测试程序")
    print("=" * 50)
    
    mode = input("选择模式 (1-测试模式, 2-交互模式): ").strip()
    
    if mode == "1":
        await test_mcp_server()
    elif mode == "2":
        await interactive_mode()
    else:
        print("❌ 无效选择")

if __name__ == "__main__":
    asyncio.run(main()) 