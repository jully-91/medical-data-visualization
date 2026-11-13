import logging
import time
import os
import sys
import importlib.util
from datetime import datetime

# 配置日志 - 简化输出
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('crawler_scheduler')

# 疾病类型列表，用于定时爬取
disease_types = [
    '感冒',
    '高血压',
    '糖尿病',
    '冠心病',
    '肺炎',
    '胃炎',
    '肝炎',
    '肾炎',
    '抑郁症',
    '骨折',
    '肠胃炎',
    '风湿',
    '哮喘',
    '气管炎'
]

# 上次爬取时间记录
last_crawl_times = {}

class CrawlerScheduler:
    """爬虫调度器"""
    
    def __init__(self):
        self.spider_module = None
        self.spider_class = None
        self._load_spider_module()
    
    def _load_spider_module(self):
        """动态加载spiderMain.py模块"""
        try:
            # 获取当前目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            spider_main_path = os.path.join(current_dir, 'spiderMain.py')
            
            if not os.path.exists(spider_main_path):
                logger.error(f"spiderMain.py文件不存在: {spider_main_path}")
                return
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("spiderMain", spider_main_path)
            self.spider_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.spider_module)
            
            # 获取spider类
            self.spider_class = getattr(self.spider_module, 'spider', None)
            if not self.spider_class:
                logger.error("在spiderMain.py中未找到spider类")
                return
            
            logger.info("成功加载spiderMain.py模块")
        except Exception as e:
            logger.error(f"加载spiderMain.py模块失败: {e}")
    
    def crawl_disease(self, disease_name, pages=3):
        """爬取指定疾病的数据
        
        Args:
            disease_name: 疾病名称
            pages: 要爬取的页数
        """
        try:
            if not self.spider_class:
                logger.error("spider类未加载，无法执行爬取")
                self._load_spider_module()
                if not self.spider_class:
                    return False
            
            logger.info(f"开始爬取疾病: {disease_name}, 爬取页数: {pages}")
            
            # 记录开始时间
            start_time = time.time()
            
            # 创建爬虫实例
            crawler = self.spider_class()
            # 初始化爬虫（创建CSV文件等）
            crawler.init()
            
            # 执行爬取
            # 由于spiderMain.py中的main方法是递归的，我们需要修改为循环调用
            page = 1
            total_items = 0
            
            print(f"开始爬取疾病: {disease_name}, 计划爬取{pages}页")
            while page <= pages:
                print(f"正在爬取疾病: {disease_name}, 第{page}页/共{pages}页")
                logger.warning(f"正在爬取疾病: {disease_name}, 第{page}页/共{pages}页")
                # 尝试爬取当前页
                try:
                    # 调用爬虫的main方法，传入疾病名称和页码
                    items_count = crawler.main(disease_name, page)
                    total_items += items_count
                    page += 1
                    # 添加适当的延迟，避免对目标网站造成过大压力
                    time.sleep(1)  # 减少页面之间的等待时间到1秒
                except Exception as e:
                    logger.error(f"爬取第{page}页失败: {e}")
                    # 重试当前页，最多重试3次
                    retry_count = 0
                    max_retries = 3
                    while retry_count < max_retries:
                        retry_count += 1
                        logger.info(f"第{retry_count}次重试爬取第{page}页")
                        try:
                            time.sleep(1)  # 减少重试前的等待时间到1秒
                            items_count = crawler.main(disease_name, page)
                            total_items += items_count
                            page += 1
                            break
                        except Exception as e_retry:
                            logger.error(f"重试第{retry_count}次失败: {e_retry}")
                    else:
                        # 所有重试都失败，跳过当前页
                        logger.error(f"所有重试都失败，跳过第{page}页")
                        page += 1
            
            # 计算爬取耗时
            elapsed_time = time.time() - start_time
            
            # 更新上次爬取时间
            last_crawl_times[disease_name] = datetime.now()
            
            logger.info(f"疾病 {disease_name} 爬取完成，共获取 {total_items} 条数据，耗时 {elapsed_time:.2f} 秒")
            
            # 尝试调用数据库保存方法（如果存在）
            try:
                # 检查spider类中是否有save_to_sql方法
                if hasattr(crawler, 'save_to_sql'):
                    logger.info("尝试将数据保存到数据库")
                    crawler.save_to_sql()
                else:
                    logger.warning("spider类中未找到save_to_sql方法")
            except Exception as e:
                logger.error(f"保存数据到数据库失败: {e}")
            
            # 所有页面爬取完成后关闭浏览器
            if hasattr(crawler, 'close_selenium'):
                logger.info("关闭Selenium浏览器")
                crawler.close_selenium()
            
            return True
        except Exception as e:
            logger.error(f"爬取疾病 {disease_name} 时发生错误: {e}")
            # 发生错误时也关闭浏览器
            if 'crawler' in locals() and hasattr(crawler, 'close_selenium'):
                crawler.close_selenium()
            return False
    
    def crawl_all_diseases(self, pages=3):
        """爬取所有配置的疾病数据
        
        Args:
            pages: 每个疾病要爬取的页数
        """
        try:
            logger.info(f"开始爬取所有疾病数据，每种疾病爬取{pages}页")
            
            success_count = 0
            failed_count = 0
            
            for disease in disease_types:
                logger.info(f"准备爬取疾病: {disease}")
                # 执行爬取
                if self.crawl_disease(disease, pages):
                    success_count += 1
                else:
                    failed_count += 1
                
                # 爬取完一种疾病后休息一段时间
                if disease != disease_types[-1]:  # 不是最后一种疾病时
                    rest_time = 0.5  # 减少休息时间到0.5秒
                    logger.info(f"休息 {rest_time} 秒后继续爬取下一种疾病")
                    time.sleep(rest_time)
            
            logger.info(f"所有疾病爬取完成，成功: {success_count}, 失败: {failed_count}")
            return {
                'success_count': success_count,
                'failed_count': failed_count,
                'total_diseases': len(disease_types)
            }
        except Exception as e:
            logger.error(f"爬取所有疾病时发生错误: {e}")
            return None
    
    def get_last_crawl_time(self, disease_name):
        """获取指定疾病的上次爬取时间
        
        Args:
            disease_name: 疾病名称
        
        Returns:
            上次爬取时间，如果没有记录则返回None
        """
        return last_crawl_times.get(disease_name)
    
    def get_crawl_statistics(self):
        """获取爬取统计信息
        
        Returns:
            包含爬取统计信息的字典
        """
        stats = {
            'configured_diseases': len(disease_types),
            'last_crawl_times': {}
        }
        
        for disease in disease_types:
            last_time = self.get_last_crawl_time(disease)
            if last_time:
                stats['last_crawl_times'][disease] = last_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                stats['last_crawl_times'][disease] = '从未爬取'
        
        return stats

# 创建全局爬虫调度器实例
crawler_scheduler = CrawlerScheduler()

# 定义可被定时任务调用的函数
def scheduled_crawl_disease(disease_name, pages=3):
    """用于定时任务的疾病爬取函数
    
    Args:
        disease_name: 疾病名称
        pages: 要爬取的页数
    """
    logger.info(f"定时任务触发爬取疾病: {disease_name}")
    return crawler_scheduler.crawl_disease(disease_name, pages)

def scheduled_crawl_all_diseases(pages=3):
    """用于定时任务的全疾病爬取函数
    
    Args:
        pages: 每个疾病要爬取的页数
    """
    logger.info(f"定时任务触发爬取所有疾病")
    return crawler_scheduler.crawl_all_diseases(pages)

if __name__ == "__main__":
    # 测试爬取功能
    logger.info("测试爬虫调度器")
    
    # 爬取单个疾病测试，只爬取1页
    # result = scheduled_crawl_disease('感冒', pages=1)
    # logger.info(f"单个疾病爬取结果: {result}")
    
    # 爬取所有疾病测试
    result = scheduled_crawl_all_diseases(pages=1)
    logger.info(f"所有疾病爬取结果: {result}")
    
    # 打印爬取统计
    stats = crawler_scheduler.get_crawl_statistics()
    logger.info(f"爬取统计: {stats}")