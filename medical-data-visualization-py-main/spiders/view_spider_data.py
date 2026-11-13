import pandas as pd
import os
from pymysql import connect
import pymysql.err
from utils.db_config import get_db_config

def view_csv_data():
    """查看CSV文件中的爬虫数据"""
    csv_path = os.path.join(os.path.dirname(__file__), 'temp2.csv')
    
    if not os.path.exists(csv_path):
        print("\n❌ CSV数据文件不存在！爬虫可能还未运行或保存路径有问题")
        return None
    
    try:
        print(f"\n📊 正在读取CSV文件: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"✅ 成功读取CSV数据，共 {len(df)} 条记录")
        print("\n📋 CSV数据前5行预览:")
        print(df.head())
        return df
    except Exception as e:
        print(f"❌ 读取CSV文件失败: {e}")
        return None

def view_database_data():
    """查看MySQL数据库中的爬虫数据"""
    conn = None
    cursor = None
    
    try:
        print("\n📂 正在连接到数据库...")
        cfg = get_db_config()
        conn = connect(**cfg)
        cursor = conn.cursor()
        
        # 查询病例表中的记录数
        cursor.execute("SELECT COUNT(*) FROM cases")
        count = cursor.fetchone()[0]
        print(f"✅ 数据库中共有 {count} 条病例记录")
        
        # 查询前5条记录进行预览
        print("\n📋 数据库中前5条记录预览:")
        cursor.execute("SELECT * FROM cases LIMIT 5")
        results = cursor.fetchall()
        
        # 获取列名
        cursor.execute("SHOW COLUMNS FROM cases")
        columns = [col[0] for col in cursor.fetchall()]
        
        # 打印列名和数据
        print(" | ".join(columns))
        print("-" * 80)
        for row in results:
            print(" | ".join(str(val)[:20] for val in row))  # 限制每个值的长度为20
            
        return count
    except pymysql.err.OperationalError as e:
        print(f"❌ 数据库连接错误: {e}")
        return None
    except pymysql.err.ProgrammingError as e:
        print(f"❌ 数据库表不存在或查询错误: {e}")
        return None
    except Exception as e:
        print(f"❌ 读取数据库失败: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def view_spider_status():
    """分析爬虫运行状态"""
    csv_data = view_csv_data()
    db_count = view_database_data()
    
    print("\n📈 爬虫数据状态分析:")
    print("-" * 60)
    
    if csv_data is not None:
        # 统计不同疾病类型
        print("\n📊 CSV数据按疾病类型统计:")
        if 'type' in csv_data.columns:
            type_counts = csv_data['type'].value_counts()
            for disease_type, count in type_counts.items():
                print(f"  {disease_type}: {count} 条")
        else:
            print("  CSV文件中没有'type'列")
    
    print("\n💡 提示:")
    print("1. 爬虫数据首先保存到temp2.csv文件中")
    print("2. 如需将CSV数据导入数据库，请取消spiderMain.py中'spiderObj.save_to_sql()'这一行的注释")
    print("3. 数据库连接参数已通过项目根目录 .env / utils.db_config 统一配置")

def main():
    print("========== 医疗爬虫数据查看工具 ==========")
    print("此工具可以查看爬虫爬取的数据，包括CSV文件和数据库中的数据")
    print("====================================\n")
    
    view_spider_status()
    
    print("\n========== 操作完成 ==========")

if __name__ == "__main__":
    main()