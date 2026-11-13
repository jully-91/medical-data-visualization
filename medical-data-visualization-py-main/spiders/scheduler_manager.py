import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.cron import CronTrigger
import datetime
import os

# 配置日志 - 简化输出
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('scheduler_manager')

class SchedulerManager:
    """定时任务管理器"""
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(SchedulerManager, cls).__new__(cls)
            cls._instance._init_scheduler()
        return cls._instance
    
    def _init_scheduler(self):
        """初始化调度器"""
        # 配置执行器
        executors = {
            'default': ThreadPoolExecutor(10),
            'processpool': ProcessPoolExecutor(3)
        }
        
        # 初始化调度器
        self.scheduler = BackgroundScheduler(executors=executors)
        self.running_jobs = {}
        logger.info("调度器初始化完成")
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("调度器已启动")
        else:
            logger.warning("调度器已经在运行中")
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("调度器已关闭")
        else:
            logger.warning("调度器未运行")
    
    def add_interval_job(self, func, job_id, hours=0, minutes=0, seconds=0, args=None, kwargs=None):
        """添加间隔执行的任务
        
        Args:
            func: 要执行的函数
            job_id: 任务ID
            hours: 小时
            minutes: 分钟
            seconds: 秒
            args: 位置参数列表
            kwargs: 关键字参数字典
        """
        try:
            # 检查任务是否已存在
            if self.scheduler.get_job(job_id):
                logger.warning(f"任务ID '{job_id}' 已存在，将替换现有任务")
                self.scheduler.remove_job(job_id)
            
            # 添加任务
            job = self.scheduler.add_job(
                func=func,
                trigger='interval',
                hours=hours,
                minutes=minutes,
                seconds=seconds,
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                replace_existing=True
            )
            
            # 安全获取next_run_time
            next_run = str(job.next_run_time) if hasattr(job, 'next_run_time') else '调度器启动后确定'
            
            self.running_jobs[job_id] = {
                'job': job,
                'type': 'interval',
                'status': 'running'
            }
            
            logger.info(f"成功添加间隔任务: {job_id}, 下次执行时间: {next_run}")
            return job
        except Exception as e:
            logger.error(f"添加间隔任务失败: {e}")
            raise
    
    def add_cron_job(self, func, job_id, cron_expression, args=None, kwargs=None):
        """添加Cron表达式任务
        
        Args:
            func: 要执行的函数
            job_id: 任务ID
            cron_expression: Cron表达式字典，例如: {'hour': 8, 'minute': 0}
            args: 位置参数列表
            kwargs: 关键字参数字典
        """
        try:
            # 检查任务是否已存在
            if self.scheduler.get_job(job_id):
                logger.warning(f"任务ID '{job_id}' 已存在，将替换现有任务")
                self.scheduler.remove_job(job_id)
            
            # 添加任务
            job = self.scheduler.add_job(
                func=func,
                trigger=CronTrigger(**cron_expression),
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                replace_existing=True
            )
            
            # 安全获取next_run_time
            next_run = str(job.next_run_time) if hasattr(job, 'next_run_time') else '调度器启动后确定'
            
            self.running_jobs[job_id] = {
                'job': job,
                'type': 'cron',
                'status': 'running'
            }
            
            logger.info(f"成功添加Cron任务: {job_id}, 下次执行时间: {next_run}")
            return job
        except Exception as e:
            logger.error(f"添加Cron任务失败: {e}")
            raise
    
    def remove_job(self, job_id):
        """移除任务
        
        Args:
            job_id: 任务ID
        """
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                if job_id in self.running_jobs:
                    del self.running_jobs[job_id]
                logger.info(f"成功移除任务: {job_id}")
            else:
                logger.warning(f"任务ID '{job_id}' 不存在")
        except Exception as e:
            logger.error(f"移除任务失败: {e}")
            raise
    
    def pause_job(self, job_id):
        """暂停任务
        
        Args:
            job_id: 任务ID
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.pause_job(job_id)
                if job_id in self.running_jobs:
                    self.running_jobs[job_id]['status'] = 'paused'
                logger.info(f"成功暂停任务: {job_id}")
            else:
                logger.warning(f"任务ID '{job_id}' 不存在")
        except Exception as e:
            logger.error(f"暂停任务失败: {e}")
            raise
    
    def resume_job(self, job_id):
        """恢复任务
        
        Args:
            job_id: 任务ID
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.resume_job(job_id)
                if job_id in self.running_jobs:
                    self.running_jobs[job_id]['status'] = 'running'
                    # 安全获取next_run_time
                    if hasattr(job, 'next_run_time'):
                        self.running_jobs[job_id]['next_run_time'] = job.next_run_time
                
                # 安全获取next_run_time用于日志
                next_run = str(job.next_run_time) if hasattr(job, 'next_run_time') else '调度器启动后确定'
                logger.info(f"成功恢复任务: {job_id}, 下次执行时间: {next_run}")
            else:
                logger.warning(f"任务ID '{job_id}' 不存在")
        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            raise
    
    def list_jobs(self):
        """列出所有任务"""
        jobs = self.scheduler.get_jobs()
        job_list = []
        
        for job in jobs:
            # 安全构建任务信息
            job_info = {
                'id': job.id,
                'name': job.name,
                'trigger': str(job.trigger),
                'next_run_time': str(getattr(job, 'next_run_time', 'N/A')),
                'status': 'paused' if hasattr(job, 'paused') and job.paused else 'running'
            }
            job_list.append(job_info)
        
        return job_list
    
    def run_job_now(self, job_id):
        """立即运行指定任务
        
        Args:
            job_id: 任务ID
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                logger.info(f"立即执行任务: {job_id}")
                self.scheduler.add_job(
                    func=job.func,
                    trigger='date',
                    run_date=datetime.datetime.now(),
                    args=job.args,
                    kwargs=job.kwargs,
                    id=f"{job_id}_immediate_{datetime.datetime.now().timestamp()}"
                )
            else:
                logger.warning(f"任务ID '{job_id}' 不存在")
        except Exception as e:
            logger.error(f"立即执行任务失败: {e}")
            raise

# 创建全局调度器实例
scheduler_manager = SchedulerManager()