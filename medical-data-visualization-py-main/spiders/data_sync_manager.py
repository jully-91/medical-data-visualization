import logging
import os
import time
import csv
import pymysql
import json
from datetime import datetime
from hashlib import md5
from utils.db_config import get_db_config

# 配置日志 - 显示INFO级别的详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('data_sync_manager')

# 数据库配置（统一从 utils.db_config / .env 读取）
DB_CONFIG = get_db_config()

# CSV文件路径
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp2.csv')

# 同步状态记录文件
SYNC_STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync_status.json')

## 数据同步配置
SYNC_CONFIG = {
    'batch_size': 20,  # 更小的批次大小，减少锁持有时间
    'check_interval': 60,  # 文件监控检查间隔（秒）
    'sync_timeout': 300,  # 同步超时时间（秒）
    'max_retries': 3  # 最大重试次数
}

class DataSyncManager:
    """数据同步管理器"""
    
    def __init__(self):
        self.sync_status = self._load_sync_status()
        self.last_csv_modify_time = None
        self.last_csv_hash = None
    
    def _load_sync_status(self):
        """加载同步状态"""
        try:
            if os.path.exists(SYNC_STATUS_FILE):
                with open(SYNC_STATUS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载同步状态失败: {e}")
        
        # 返回默认状态
        return {
            'last_sync_time': None,
            'last_sync_status': 'none',
            'sync_count': 0,
            'failed_count': 0,
            'success_count': 0,
            'last_error': None,
            'csv_record_count': 0,
            'db_record_count': 0
        }
    
    def _save_sync_status(self):
        """保存同步状态"""
        try:
            with open(SYNC_STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.sync_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存同步状态失败: {e}")
    
    def _get_db_connection(self):
        """获取数据库连接"""
        try:
            connection = pymysql.connect(**DB_CONFIG)
            logger.info("成功连接到数据库")
            return connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def _calculate_csv_hash(self):
        """计算CSV文件的哈希值，用于检测文件变化"""
        try:
            if not os.path.exists(CSV_FILE_PATH):
                return None
            
            hasher = md5()
            with open(CSV_FILE_PATH, 'rb') as f:
                # 跳过表头行
                f.readline()
                # 计算其余内容的哈希
                while True:
                    data = f.read(65536)  # 64KB chunks
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"计算CSV哈希值失败: {e}")
            return None
    
    def _read_csv_data(self):
        """读取CSV文件数据"""
        try:
            if not os.path.exists(CSV_FILE_PATH):
                logger.warning(f"CSV文件不存在: {CSV_FILE_PATH}")
                return [], 0
            
            data = []
            with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 确保所有必需的字段都存在
                    # 从spiderMain.py的表头可以看到需要的字段
                    required_fields = ['type', 'gender', 'age', 'time', 'content', 'docName', 'docHospital', 'department', 'detailUrl']
                    for field in required_fields:
                        if field not in row:
                            row[field] = ''
                    
                    # 添加可选字段
                    optional_fields = ['height', 'weight', 'illDuration', 'allergy']
                    for field in optional_fields:
                        if field not in row:
                            row[field] = ''
                    
                    data.append(row)
            
            record_count = len(data)
            logger.info(f"成功读取CSV文件，共{record_count}条记录")
            return data, record_count
        except Exception as e:
            logger.error(f"读取CSV文件失败: {e}")
            return [], 0
    
    def _get_db_record_count(self):
        """获取数据库中的记录数"""
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM cases")
                    count = cursor.fetchone()[0]
                    return count
        except Exception as e:
            logger.error(f"获取数据库记录数失败: {e}")
            return -1
    
    def _sync_data_to_db(self, csv_data):
        """将CSV数据同步到数据库"""
        retry_count = 0
        max_retries = SYNC_CONFIG['max_retries']
        
        # 总的同步结果
        total_inserted = 0
        total_updated = 0
        
        # 遍历所有数据，使用更小的批次
        for i in range(0, len(csv_data), SYNC_CONFIG['batch_size']):
            batch = csv_data[i:i + SYNC_CONFIG['batch_size']]
            
            # 对每个批次单独处理，包括重试逻辑
            batch_retry = 0
            batch_success = False
            
            while not batch_success and batch_retry <= max_retries:
                try:
                    # 为每个批次创建新的连接和游标
                    with self._get_db_connection() as conn:
                        with conn.cursor() as cursor:
                            # 准备插入SQL
                            insert_sql = """
                            INSERT INTO cases (`type`, gender, age, `time`, content, docName, docHospital, department, detailUrl, 
                                             height, weight, illDuration, allergy)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                content = VALUES(content),
                                docName = VALUES(docName),
                                docHospital = VALUES(docHospital),
                                department = VALUES(department),
                                height = VALUES(height),
                                weight = VALUES(weight),
                                illDuration = VALUES(illDuration),
                                allergy = VALUES(allergy)
                            """
                            
                            values = []
                            for row in batch:
                                value_tuple = (
                                    row.get('type', ''),
                                    row.get('gender', ''),
                                    row.get('age', ''),
                                    row.get('time', ''),
                                    row.get('content', ''),
                                    row.get('docName', ''),
                                    row.get('docHospital', ''),
                                    row.get('department', ''),
                                    row.get('detailUrl', ''),
                                    row.get('height', ''),
                                    row.get('weight', ''),
                                    row.get('illDuration', ''),
                                    row.get('allergy', '')
                                )
                                values.append(value_tuple)
                            
                            # 执行批量插入
                            affected_rows = cursor.executemany(insert_sql, values)
                            
                            # 计算插入和更新的记录数
                            if affected_rows == len(batch):
                                insert_count = len(batch)
                                update_count = 0
                            elif affected_rows == len(batch) * 2:
                                insert_count = 0
                                update_count = len(batch)
                            else:
                                update_count = affected_rows - len(batch)
                                insert_count = len(batch) - update_count
                            
                            total_inserted += insert_count
                            total_updated += update_count
                            
                            # 提交批次
                            conn.commit()
                            logger.info(f"批次 {i//SYNC_CONFIG['batch_size']+1} 同步完成，插入: {insert_count}, 更新: {update_count}")
                            
                            batch_success = True
                except Exception as e:
                    logger.error(f"批次 {i//SYNC_CONFIG['batch_size']+1} 同步失败 (第{batch_retry+1}/{max_retries+1}次尝试): {e}")
                    
                    # 如果是锁超时错误，重试
                    if 'Lock wait timeout' in str(e) and batch_retry < max_retries:
                        batch_retry += 1
                        wait_time = batch_retry * 3  # 指数退避
                        logger.info(f"遇到锁超时，{wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"批次 {i//SYNC_CONFIG['batch_size']+1} 同步失败，跳过该批次")
                        break
            
            # 批次之间短暂休息，让数据库有时间释放锁
            time.sleep(1)
        
        if total_inserted + total_updated > 0:
            logger.info(f"数据同步完成，总计插入: {total_inserted}, 更新: {total_updated}")
            return True, total_inserted, total_updated
        else:
            logger.error("所有批次同步失败")
            return False, 0, 0
    
    def _cleanup_duplicate_records(self):
        """清理数据库中的重复记录 - 暂时禁用以避免锁超时"""
        logger.info("重复记录清理功能已暂时禁用，以避免锁超时问题")
        return 0
    
    def sync_csv_to_db(self):
        """将CSV数据同步到数据库的主方法"""
        logger.info("开始执行CSV到数据库的同步")
        
        # 更新同步状态
        self.sync_status['last_sync_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # 读取CSV数据
            csv_data, csv_record_count = self._read_csv_data()
            if not csv_data:
                logger.warning("没有要同步的数据")
                self.sync_status['last_sync_status'] = 'failed'
                self.sync_status['last_error'] = '没有要同步的数据'
                self.sync_status['failed_count'] += 1
                self._save_sync_status()
                return False
            
            # 执行同步
            success, inserted, updated = self._sync_data_to_db(csv_data)
            
            if success:
                # 清理重复记录
                deleted_duplicates = self._cleanup_duplicate_records()
                
                # 更新同步状态
                self.sync_status['last_sync_status'] = 'success'
                self.sync_status['sync_count'] += 1
                self.sync_status['success_count'] += 1
                self.sync_status['last_error'] = None
                self.sync_status['csv_record_count'] = csv_record_count
                self.sync_status['db_record_count'] = self._get_db_record_count()
                
                logger.info(f"同步成功: 插入{inserted}条，更新{updated}条，清理重复{deleted_duplicates}条")
            else:
                self.sync_status['last_sync_status'] = 'failed'
                self.sync_status['failed_count'] += 1
                logger.error("同步失败")
            
            # 保存同步状态
            self._save_sync_status()
            
            return success
        except Exception as e:
            logger.error(f"同步过程中发生错误: {e}")
            self.sync_status['last_sync_status'] = 'failed'
            self.sync_status['last_error'] = str(e)
            self.sync_status['failed_count'] += 1
            self._save_sync_status()
            return False
    
    def check_csv_changes(self):
        """检查CSV文件是否有变化"""
        try:
            if not os.path.exists(CSV_FILE_PATH):
                logger.warning(f"CSV文件不存在: {CSV_FILE_PATH}")
                return False
            
            # 获取文件修改时间
            current_modify_time = os.path.getmtime(CSV_FILE_PATH)
            
            # 计算文件哈希
            current_hash = self._calculate_csv_hash()
            
            # 检查是否有变化
            has_changed = False
            
            if self.last_csv_modify_time != current_modify_time:
                has_changed = True
                logger.info(f"CSV文件修改时间变化: {self.last_csv_modify_time} -> {current_modify_time}")
            
            if self.last_csv_hash != current_hash:
                has_changed = True
                # 安全地打印哈希值，避免NoneType错误
                old_hash_str = f"{self.last_csv_hash[:8]}..." if self.last_csv_hash else "None"
                new_hash_str = f"{current_hash[:8]}..." if current_hash else "None"
                logger.info(f"CSV文件内容变化: {old_hash_str} -> {new_hash_str}")
            
            # 更新记录
            self.last_csv_modify_time = current_modify_time
            self.last_csv_hash = current_hash
            
            return has_changed
        except Exception as e:
            logger.error(f"检查CSV文件变化失败: {e}")
            return False
    
    def monitor_and_sync(self):
        """监控CSV文件变化并自动同步"""
        logger.info("monitor_and_sync - 开始")
        
        try:
            logger.info(f"monitor_and_sync - 检查CSV文件: {CSV_FILE_PATH}")
            # 检查CSV文件是否存在
            if not os.path.exists(CSV_FILE_PATH):
                logger.warning(f"monitor_and_sync - CSV文件不存在: {CSV_FILE_PATH}")
                return False
            
            logger.info("monitor_and_sync - 检查CSV文件变化")
            if self.check_csv_changes():
                logger.info("monitor_and_sync - 检测到CSV文件变化，触发同步")
                return self.sync_csv_to_db()
            else:
                logger.info("monitor_and_sync - CSV文件未发生变化，无需同步")
                return True
        except Exception as e:
            logger.error(f"monitor_and_sync - 异常: {e}")
            import traceback
            logger.error(f"monitor_and_sync - 异常堆栈信息: {traceback.format_exc()}")
            # 更新同步状态
            self.sync_status['last_sync_status'] = 'failed'
            self.sync_status['last_error'] = str(e)
            self.sync_status['failed_count'] += 1
            self._save_sync_status()
            return False
    
    def force_sync(self):
        """强制执行同步，不管文件是否有变化"""
        logger.info("执行强制同步")
        return self.sync_csv_to_db()
    
    def get_sync_status(self):
        """获取同步状态信息"""
        # 更新数据库记录数
        db_count = self._get_db_record_count()
        if db_count >= 0:
            self.sync_status['db_record_count'] = db_count
        
        return self.sync_status
    
    def validate_data_consistency(self):
        """验证数据一致性"""
        logger.info("开始验证数据一致性")
        
        try:
            # 获取CSV记录数
            _, csv_count = self._read_csv_data()
            
            # 获取数据库记录数
            db_count = self._get_db_record_count()
            
            # 计算差异
            diff = abs(csv_count - db_count)
            consistency_ratio = 0
            if csv_count > 0:
                consistency_ratio = (min(csv_count, db_count) / max(csv_count, db_count)) * 100
            
            result = {
                'csv_record_count': csv_count,
                'db_record_count': db_count,
                'difference': diff,
                'consistency_ratio': round(consistency_ratio, 2),
                'is_consistent': diff == 0
            }
            
            logger.info(f"数据一致性验证结果: {result}")
            return result
        except Exception as e:
            logger.error(f"数据一致性验证失败: {e}")
            return None

# 创建全局数据同步管理器实例
data_sync_manager = DataSyncManager()

# 定义可被定时任务调用的函数
def scheduled_sync_csv_to_db():
    """用于定时任务的数据同步函数"""
    logger.info("定时任务触发数据同步 - 开始")
    try:
        result = data_sync_manager.monitor_and_sync()
        logger.info(f"定时任务触发数据同步 - 完成，结果: {result}")
        return result
    except Exception as e:
        logger.error(f"定时任务触发数据同步 - 异常: {e}")
        import traceback
        logger.error(f"异常堆栈信息: {traceback.format_exc()}")
        return False

def scheduled_validate_consistency():
    """用于定时任务的数据一致性验证函数"""
    logger.info("定时任务触发数据一致性验证")
    return data_sync_manager.validate_data_consistency()

if __name__ == "__main__":
    # 测试数据同步功能
    logger.info("测试数据同步管理器")
    
    # 执行同步
    result = scheduled_sync_csv_to_db()
    logger.info(f"同步结果: {result}")
    
    # 验证一致性
    consistency = scheduled_validate_consistency()
    logger.info(f"一致性验证结果: {consistency}")
    
    # 打印同步状态
    status = data_sync_manager.get_sync_status()
    logger.info(f"同步状态: {status}")