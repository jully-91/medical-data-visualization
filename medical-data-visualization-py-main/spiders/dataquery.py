from pymysql import connect
import pymysql.err
import os
from utils.db_config import get_db_config

def query_medical_data():
    # 初始化连接和游标为None
    conn = None
    cursor = None
    
    try:
        # 创建数据库连接（使用项目统一的数据库配置）
        cfg = get_db_config()
        print(f"正在尝试连接到MySQL数据库...")
        print(
            f"连接参数: 主机={cfg['host']}, 端口={cfg['port']}, 用户={cfg['user']}, 数据库={cfg['database']}"
        )
        conn = connect(**cfg)
        print("数据库连接成功！")
        
        # 创建游标
        cursor = conn.cursor()
        
        # 查询数据
        print("正在查询病例数据...")
        cursor.execute('SELECT * FROM cases')
        results = cursor.fetchall()
        
        # 打印数据
        print(f"查询到 {len(results)} 条记录")
        print("\n前5条记录：")
        for i, row in enumerate(results[:5]):
            print(f"记录 {i+1}: {row}")
        
    except pymysql.err.OperationalError as e:
        print(f"数据库连接错误: {e}")
        print("\n可能的原因：")
        print("1. MySQL服务器未启动或不在默认端口")
        print("2. 终端中的MySQL可能使用不同的配置")
        print("3. 连接参数错误")
        print("\n请检查：")
        print("- 如果使用终端中的MySQL，请确认服务器是否已启动")
        print("- 用户名和密码是否正确")
        print("- 数据库名称是否正确")
        print("- 可以尝试修改脚本中的连接参数以匹配您的MySQL配置")
    
    except pymysql.err.ProgrammingError as e:
        print(f"SQL语法错误或表不存在: {e}")
        print("请检查cases表是否存在")
    
    except Exception as e:
        print(f"发生未知错误: {e}")
    
    finally:
        # 关闭连接
        print("\n正在清理资源...")
        if cursor:
            cursor.close()
            print("游标已关闭")
        if conn:
            conn.close()
            print("数据库连接已关闭")

def main():
    print("===== 医疗数据查询工具 =====\n")
    print("注意：此工具使用项目统一的数据库配置（.env / utils.db_config）\n")
    
    query_medical_data()
    print("\n===== 查询完成 =====")

if __name__ == "__main__":
    main()