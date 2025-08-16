"""
日志管理模块
负责日志的配置、记录、轮转和清理
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import glob
from datetime import datetime, timedelta

# --- 模块级别的变量 ---
# 创建一个唯一的日志记录器实例
logger = logging.getLogger('evm_monitor')
_log_file_path = "" # 用于存储日志文件路径

def _cleanup_old_logs():
    """(内部函数) 清理超过7天的旧日志文件"""
    try:
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            return
        
        cutoff_date = datetime.now() - timedelta(days=7)
        log_files = glob.glob(os.path.join(logs_dir, 'evm_monitor_*.log*'))
        
        for log_file in log_files:
            try:
                filename = os.path.basename(log_file)
                if filename.startswith('evm_monitor_') and filename.endswith('.log'):
                    date_str = filename.replace('evm_monitor_', '').replace('.log', '')
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        os.remove(log_file)
                        # 在日志系统配置好之前，可以使用print
                        print(f"🗑️ 删除旧日志文件: {filename}")
            except Exception as e:
                print(f"⚠️ 处理日志文件 {log_file} 时出错: {e}")
    except Exception as e:
        print(f"⚠️ 清理旧日志文件时出错: {e}")

def _configure_logger():
    """(内部函数) 配置并初始化日志记录器，只在模块首次导入时运行一次"""
    global _log_file_path
    
    # 1. 清理旧日志
    _cleanup_old_logs()
    
    # 2. 确保logs目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # 3. 设置日志文件名和路径
    _log_file_path = f"logs/evm_monitor_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 4. 配置日志
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logger.setLevel(logging.INFO)
    logger.handlers.clear() # 清除已有处理器，防止重复
    logger.propagate = False # 防止日志向上传播导致重复输出
    
    # 5. 创建并添加处理器
    # 文件处理器
    file_handler = RotatingFileHandler(
        _log_file_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# --- 对外暴露的公共接口 ---

def log(message: str):
    """
    全局日志函数，供其他模块调用。
    
    用法:
    from logger import log
    log("这是一条日志信息")
    """
    logger.info(message)

def get_logger() -> logging.Logger:
    """获取配置好的日志记录器实例"""
    return logger

def get_log_file_path() -> str:
    """获取当前日志文件的路径"""
    return _log_file_path

# --- 模块初始化代码 ---
# 当这个模块首次被导入时，自动执行配置
_configure_logger()