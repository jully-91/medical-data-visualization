from pymysql import connect
import pymysql.err
import os
import time
from utils.db_config import get_db_config

def import_sql_file():
    # 数据库连接参数统一从 utils.db_config / .env 中读取
    cfg = get_db_config()
    host = cfg["host"]
    user = cfg["user"]
    password = cfg["password"]
    database = cfg["database"]
    port = cfg["port"]
    charset = cfg.get("charset", "utf8mb4")
    
    # SQL文件路径
    sql_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'medicalinfo.sql')
    
    conn = None
    cursor = None
    
    try:
        # 首先连接到MySQL（不指定数据库）
        print(f"正在连接到MySQL服务器...")
        conn = connect(host=host, user=user, password=password, port=port, charset=charset)
        cursor = conn.cursor()
        
        # 创建数据库（如果不存在）
        print(f"检查并创建数据库 {database}...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        cursor.execute(f"USE {database}")
        print(f"数据库 {database} 已准备就绪")
        
        # 读取SQL文件
        print(f"正在读取SQL文件: {sql_file_path}")
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_commands = f.read().split(';')
        
        # 执行SQL命令
        print("开始执行SQL命令...")
        executed_count = 0
        for command in sql_commands:
            command = command.strip()
            if command and not command.startswith('--') and not command.startswith('/*'):
                try:
                    cursor.execute(command)
                    executed_count += 1
                except Exception as e:
                    print(f"执行命令时出错: {e}")
                    print(f"出错的命令: {command[:100]}...")
        
        # 提交更改
        conn.commit()
        print(f"\n成功执行 {executed_count} 条SQL命令")
        print("数据库初始化完成！")
        
        # 验证表是否创建成功
        cursor.execute("SHOW TABLES LIKE 'cases'")
        result = cursor.fetchone()
        if result:
            print("✓ cases表创建成功")
            # 检查数据量
            cursor.execute("SELECT COUNT(*) FROM cases")
            count = cursor.fetchone()[0]
            print(f"✓ 表中共有 {count} 条记录")
        else:
            print("✗ cases表创建失败")
            
    except pymysql.err.OperationalError as e:
        print(f"数据库连接错误: {e}")
    except Exception as e:
        print(f"执行SQL文件时出错: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("\n数据库连接已关闭")

if __name__ == "__main__":
    print("===== 数据库初始化工具 =====")
    print("此工具将导入medicalinfo.sql文件到MySQL数据库")
    print("================================\n")
    import_sql_file()
    print("\n===== 操作完成 =====")