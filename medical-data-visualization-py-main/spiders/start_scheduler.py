import logging
import os
import sys
import time
import signal
import argparse
from datetime import datetime

# 配置根日志 - 只输出到控制台
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('start_scheduler')
# 为start_scheduler单独配置控制台输出
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(message)s'))
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入各个模块
try:
    from scheduler_manager import scheduler_manager
    from crawler_scheduler import scheduled_crawl_all_diseases, scheduled_crawl_disease
    from data_sync_manager import scheduled_sync_csv_to_db, scheduled_validate_consistency
    from model_trainer import scheduled_retrain_model, scheduled_evaluate_model
    logger.info("成功导入所有模块")
except Exception as e:
    logger.error(f"导入模块失败: {e}")
    sys.exit(1)

class SchedulerSystem:
    """定时任务系统管理器"""
    
    def __init__(self):
        self.running = False
        self.tasks = []
    
    def configure_tasks(self, config=None):
        """配置所有定时任务
        
        Args:
            config: 任务配置字典，如果为None则使用默认配置
        """
        try:
            # 默认任务配置
            default_config = {
                # 爬虫任务配置
                'crawl_all_diseases': {
                    'job_id': 'crawl_all_diseases',
                    'trigger': 'cron',
                    'cron_expression': {'hour': 1, 'minute': 0},  # 每天凌晨1点执行
                    'func': scheduled_crawl_all_diseases,
                    'args': (10,),  # 每个疾病爬取10页
                    'kwargs': {},
                    'description': '爬取所有疾病数据'
                },
                # 数据同步任务配置
                'sync_csv_to_db': {
                    'job_id': 'sync_csv_to_db',
                    'trigger': 'interval',
                    'hours': 0,
                    'minutes': 30,  # 每30分钟执行一次
                    'func': scheduled_sync_csv_to_db,
                    'args': (),
                    'kwargs': {},
                    'description': '同步CSV数据到数据库'
                },
                # 数据一致性验证任务配置
                'validate_consistency': {
                    'job_id': 'validate_consistency',
                    'trigger': 'cron',
                    'cron_expression': {'hour': 2, 'minute': 0},  # 每天凌晨2点执行
                    'func': scheduled_validate_consistency,
                    'args': (),
                    'kwargs': {},
                    'description': '验证数据一致性'
                },
                # 模型重训练任务配置
                'retrain_model': {
                    'job_id': 'retrain_model',
                    'trigger': 'cron',
                    'cron_expression': {'day_of_week': 0, 'hour': 3, 'minute': 0},  # 每周日凌晨3点执行
                    'func': scheduled_retrain_model,
                    'args': (),
                    'kwargs': {},
                    'description': '自动重训练模型'
                },
                # 模型评估任务配置
                'evaluate_model': {
                    'job_id': 'evaluate_model',
                    'trigger': 'cron',
                    'cron_expression': {'hour': 4, 'minute': 0},  # 每天凌晨4点执行
                    'func': scheduled_evaluate_model,
                    'args': (),
                    'kwargs': {},
                    'description': '评估模型性能'
                }
            }
            
            # 使用传入的配置或默认配置
            task_config = config or default_config
            
            # 注册所有任务
            for task_name, task_info in task_config.items():
                if task_info['trigger'] == 'interval':
                    # 添加间隔任务
                    job = scheduler_manager.add_interval_job(
                        func=task_info['func'],
                        job_id=task_info['job_id'],
                        hours=task_info.get('hours', 0),
                        minutes=task_info.get('minutes', 0),
                        seconds=task_info.get('seconds', 0),
                        args=task_info['args'],
                        kwargs=task_info['kwargs']
                    )
                elif task_info['trigger'] == 'cron':
                    # 添加Cron任务
                    job = scheduler_manager.add_cron_job(
                        func=task_info['func'],
                        job_id=task_info['job_id'],
                        cron_expression=task_info['cron_expression'],
                        args=task_info['args'],
                        kwargs=task_info['kwargs']
                    )
                
                # 记录任务信息
                self.tasks.append({
                    'name': task_name,
                    'job_id': task_info['job_id'],
                    'description': task_info['description'],
                    'job': job
                })
                
                logger.info(f"成功注册任务: {task_info['description']} ({task_info['job_id']})")
            
            logger.info(f"共注册了{len(self.tasks)}个定时任务")
            return True
        except Exception as e:
            logger.error(f"配置任务失败: {e}")
            return False
    
    def start(self):
        """启动定时任务系统"""
        try:
            # 配置任务
            if not self.configure_tasks():
                logger.error("任务配置失败，无法启动系统")
                return False
            
            # 启动调度器
            scheduler_manager.start()
            self.running = True
            
            logger.info("定时任务系统已启动")
            logger.info("==========================================")
            logger.info("医疗疾病数据定时任务系统运行中...")
            logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("==========================================")
            
            # 列出所有任务
            self.list_tasks()
            
            return True
        except Exception as e:
            logger.error(f"启动系统失败: {e}")
            return False
    
    def stop(self):
        """停止定时任务系统"""
        try:
            if self.running:
                scheduler_manager.shutdown()
                self.running = False
                logger.info("定时任务系统已停止")
            else:
                logger.warning("系统未运行")
            
            return True
        except Exception as e:
            logger.error(f"停止系统失败: {e}")
            return False
    
    def list_tasks(self):
        """列出所有任务"""
        try:
            logger.info("当前注册的定时任务:")
            logger.info("------------------------------------------")
            
            job_list = scheduler_manager.list_jobs()
            
            for job_info in job_list:
                for task in self.tasks:
                    if task['job_id'] == job_info['id']:
                        logger.info(f"任务ID: {job_info['id']}")
                        logger.info(f"描述: {task['description']}")
                        logger.info(f"触发器: {job_info['trigger']}")
                        logger.info(f"下次执行: {job_info['next_run_time']}")
                        logger.info(f"状态: {job_info['status']}")
                        logger.info("------------------------------------------")
                        break
            
            if not job_list:
                logger.info("暂无注册的任务")
                logger.info("------------------------------------------")
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
    
    def run_job_now(self, job_id):
        """立即运行指定任务
        
        Args:
            job_id: 任务ID
        """
        try:
            logger.info(f"立即运行任务: {job_id}")
            scheduler_manager.run_job_now(job_id)
            logger.info(f"任务 {job_id} 已触发")
            return True
        except Exception as e:
            logger.error(f"触发任务失败: {e}")
            return False
    
    def pause_job(self, job_id):
        """暂停指定任务
        
        Args:
            job_id: 任务ID
        """
        try:
            scheduler_manager.pause_job(job_id)
            logger.info(f"任务 {job_id} 已暂停")
            return True
        except Exception as e:
            logger.error(f"暂停任务失败: {e}")
            return False
    
    def resume_job(self, job_id):
        """恢复指定任务
        
        Args:
            job_id: 任务ID
        """
        try:
            scheduler_manager.resume_job(job_id)
            logger.info(f"任务 {job_id} 已恢复")
            return True
        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            return False
    
    def wait_for_termination(self):
        """等待终止信号"""
        try:
            logger.info("按 Ctrl+C 停止系统...")
            
            # 等待键盘中断
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到终止信号")
        finally:
            self.stop()

def setup_signal_handlers(scheduler_system):
    """设置信号处理器
    
    Args:
        scheduler_system: SchedulerSystem实例
    """
    def signal_handler(sig, frame):
        logger.info(f"收到信号 {sig}，准备停止系统")
        scheduler_system.stop()
        sys.exit(0)
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill命令

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='医疗疾病数据定时任务系统')
    parser.add_argument('--action', '-a', choices=['start', 'stop', 'list', 'run', 'pause', 'resume'], 
                        default='start', help='操作: start(启动), stop(停止), list(列出), run(运行), pause(暂停), resume(恢复)')
    parser.add_argument('--job', '-j', help='任务ID，用于run/pause/resume操作')
    parser.add_argument('--daemon', '-d', action='store_true', help='以守护进程方式运行')
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 创建定时任务系统实例
        scheduler_system = SchedulerSystem()
        
        # 设置信号处理
        setup_signal_handlers(scheduler_system)
        
        # 根据命令执行操作
        if args.action == 'start':
            logger.info("启动医疗疾病数据定时任务系统...")
            
            if scheduler_system.start():
                # 运行示例：立即执行一次数据爬取任务进行测试
                logger.info("系统启动成功，执行一次测试任务")
                scheduler_system.run_job_now('crawl_all_diseases')
                
                if args.daemon:
                    # 守护进程模式
                    logger.info("以守护进程模式运行")
                    scheduler_system.wait_for_termination()
                else:
                    # 前台运行
                    scheduler_system.wait_for_termination()
        
        elif args.action == 'stop':
            logger.info("停止医疗疾病数据定时任务系统...")
            scheduler_system.stop()
        
        elif args.action == 'list':
            logger.info("列出所有定时任务...")
            # 启动调度器（如果未启动）
            try:
                scheduler_manager.start()
            except:
                pass
            scheduler_system.list_tasks()
            # 停止调度器
            scheduler_manager.shutdown()
        
        elif args.action == 'run':
            if args.job:
                logger.info(f"立即运行任务: {args.job}")
                # 启动调度器（如果未启动）
                try:
                    scheduler_manager.start()
                except:
                    pass
                scheduler_system.run_job_now(args.job)
                # 停止调度器
                scheduler_manager.shutdown()
            else:
                logger.error("请指定要运行的任务ID")
                sys.exit(1)
        
        elif args.action == 'pause':
            if args.job:
                logger.info(f"暂停任务: {args.job}")
                # 启动调度器（如果未启动）
                try:
                    scheduler_manager.start()
                except:
                    pass
                scheduler_system.pause_job(args.job)
                # 停止调度器
                scheduler_manager.shutdown()
            else:
                logger.error("请指定要暂停的任务ID")
                sys.exit(1)
        
        elif args.action == 'resume':
            if args.job:
                logger.info(f"恢复任务: {args.job}")
                # 启动调度器（如果未启动）
                try:
                    scheduler_manager.start()
                except:
                    pass
                scheduler_system.resume_job(args.job)
                # 停止调度器
                scheduler_manager.shutdown()
            else:
                logger.error("请指定要恢复的任务ID")
                sys.exit(1)
        
    except Exception as e:
        logger.error(f"系统运行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()