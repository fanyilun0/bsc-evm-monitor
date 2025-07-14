"""
日志管理模块
负责日志的配置、记录、轮转和清理
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import glob
from datetime import datetime, timedelta

class EVMLogger:
    """EVM监控器日志管理类"""
    
    def __init__(self, env='dev'):
        self.env = env.lower()
        self.is_dev = self.env == 'dev'
        self.is_prod = self.env == 'prod'
        self.logger = None
        self.setup_logging()
    
    def cleanup_old_logs(self):
        """清理超过7天的旧日志文件"""
        try:
            logs_dir = 'logs'
            if not os.path.exists(logs_dir):
                return
            
            # 计算7天前的时间
            cutoff_date = datetime.now() - timedelta(days=7)
            
            # 查找所有日志文件
            log_files = glob.glob(os.path.join(logs_dir, 'evm_monitor_*.log*'))
            
            for log_file in log_files:
                try:
                    # 从文件名中提取日期
                    filename = os.path.basename(log_file)
                    if filename.startswith('evm_monitor_') and filename.endswith('.log'):
                        date_str = filename.replace('evm_monitor_', '').replace('.log', '')
                        file_date = datetime.strptime(date_str, '%Y%m%d')
                        
                        # 如果文件超过7天，删除它
                        if file_date < cutoff_date:
                            os.remove(log_file)
                            print(f"🗑️ 删除旧日志文件: {filename}")
                except Exception as e:
                    print(f"⚠️ 处理日志文件 {log_file} 时出错: {e}")
        except Exception as e:
            print(f"⚠️ 清理旧日志文件时出错: {e}")
    
    def setup_logging(self):
        """配置日志系统"""
        # 清理旧日志文件
        self.cleanup_old_logs()
        
        # 创建logs目录
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # 生成日志文件名（按日期）
        log_filename = f"logs/evm_monitor_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 配置日志格式
        log_format = '%(asctime)s [%(levelname)s] %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # 创建日志记录器
        self.logger = logging.getLogger('evm_monitor')
        self.logger.setLevel(logging.INFO)
        
        # 清除现有的处理器
        self.logger.handlers.clear()
        
        # 文件处理器（带轮转）
        file_handler = RotatingFileHandler(
            log_filename,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,  # 保留5个备份文件
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log(self, message, level='INFO', show_in_prod=True):
        """统一的日志函数，支持时间戳和环境控制"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        env_prefix = f"[{self.env.upper()}]"
        log_message = f"{timestamp} {env_prefix} [{level}] {message}"
        
        # 在prod环境下，只显示标记为show_in_prod的日志
        if self.is_prod and not show_in_prod:
            return
        
        # 根据级别记录日志
        if level == 'ERROR':
            self.logger.error(log_message)
        elif level == 'WARNING':
            self.logger.warning(log_message)
        elif level == 'DEBUG':
            self.logger.debug(log_message)
        else:
            self.logger.info(log_message)
        
        # 同时输出到控制台（保持原有行为）
        print(log_message)
    
    def get_log_file_path(self):
        """获取当前日志文件路径"""
        return f"logs/evm_monitor_{datetime.now().strftime('%Y%m%d')}.log"
    
    def get_logger(self):
        """获取日志记录器实例"""
        return self.logger

# 全局日志实例
_evm_logger = None

def get_logger(env='dev'):
    """获取全局日志实例"""
    global _evm_logger
    if _evm_logger is None:
        _evm_logger = EVMLogger(env)
    return _evm_logger

def log(message, level='INFO', show_in_prod=True):
    """全局日志函数"""
    global _evm_logger
    if _evm_logger is None:
        _evm_logger = EVMLogger()
    _evm_logger.log(message, level, show_in_prod) 