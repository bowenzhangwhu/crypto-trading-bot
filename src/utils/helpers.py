"""
辅助工具函数
"""
import json
import re
import time
import functools
from typing import Any, Callable, Optional, TypeVar
from src.utils.logger import get_logger

logger = get_logger(__name__)
T = TypeVar('T')


def safe_json_parse(json_str: str) -> Optional[Any]:
    """
    安全解析JSON字符串
    
    Args:
        json_str: JSON字符串
    
    Returns:
        解析后的对象，失败返回None
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # 修复常见的JSON格式问题
            json_str = json_str.replace("'", '"')
            json_str = re.sub(r'(\w+):', r'"\1":', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.debug(f"原始内容: {json_str[:200]}...")
            return None


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
) -> Callable:
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 需要捕获的异常类型
        on_retry: 重试时的回调函数
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 第{attempt + 1}次尝试失败: {e}，"
                            f"{delay}秒后重试..."
                        )
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} 重试{max_retries}次后仍失败")
            
            raise last_exception
        
        return wrapper
    return decorator


def wait_for_next_period(period_minutes: int = 15) -> int:
    """
    计算等待到下一个周期整点的秒数
    
    Args:
        period_minutes: 周期分钟数（默认15分钟）
    
    Returns:
        需要等待的秒数
    """
    from datetime import datetime
    
    now = datetime.now()
    current_minute = now.minute
    current_second = now.second
    
    # 计算下一个整点时间
    next_period_minute = ((current_minute // period_minutes) + 1) * period_minutes
    
    if next_period_minute >= 60:
        next_period_minute = 0
    
    # 计算需要等待的总秒数
    if next_period_minute > current_minute:
        minutes_to_wait = next_period_minute - current_minute
    else:
        minutes_to_wait = 60 - current_minute + next_period_minute
    
    seconds_to_wait = minutes_to_wait * 60 - current_second
    
    # 显示友好的等待时间
    display_minutes = minutes_to_wait - 1 if current_second > 0 else minutes_to_wait
    display_seconds = 60 - current_second if current_second > 0 else 0
    
    if display_minutes > 0:
        logger.info(f"等待 {display_minutes} 分 {display_seconds} 秒到整点...")
    else:
        logger.info(f"等待 {display_seconds} 秒到整点...")
    
    return seconds_to_wait


def format_number(num: float, decimal_places: int = 2) -> str:
    """格式化数字"""
    return f"{num:,.{decimal_places}f}"


def format_percentage(num: float, decimal_places: int = 2) -> str:
    """格式化百分比"""
    sign = "+" if num >= 0 else ""
    return f"{sign}{num:.{decimal_places}f}%"


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断字符串"""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix
