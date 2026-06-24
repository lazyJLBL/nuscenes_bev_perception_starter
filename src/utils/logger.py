"""
logger.py — 日志工具
=====================
提供统一的日志格式，方便调试和查看脚本运行状态。

使用示例:
    from src.utils.logger import setup_logger
    logger = setup_logger("my_script")
    logger.info("开始处理数据...")
    logger.warning("数据量较少")
    logger.error("文件未找到")
"""

import logging
import sys


def setup_logger(name, level=logging.INFO):
    """
    创建并配置一个 logger。
    
    参数:
        name (str): logger 名称，通常使用脚本名
        level (int): 日志级别，默认 INFO
    
    返回:
        logging.Logger: 配置好的 logger 对象
    
    日志格式:
        [时间] [级别] [名称] 消息
        例如: [2024-01-15 10:30:00] [INFO] [check_env] Python 版本: 3.10.0
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 控制台输出 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def print_separator(char='=', length=70):
    """
    打印分隔线，用于美化控制台输出。
    
    参数:
        char (str): 分隔字符
        length (int): 分隔线长度
    """
    print(char * length)


def print_header(title, char='=', length=70):
    """
    打印带标题的分隔线。
    
    参数:
        title (str): 标题文字
        char (str): 分隔字符
        length (int): 分隔线长度
    
    输出示例:
        ======================================================================
        nuScenes 数据检查
        ======================================================================
    """
    print_separator(char, length)
    print(f"  {title}")
    print_separator(char, length)
