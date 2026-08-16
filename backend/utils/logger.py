#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
操作日志记录工具
"""

from flask import request, session
from functools import wraps
from datetime import datetime


def log_operation(action, target_user=None, details=None):
    """
    记录管理员操作日志
    
    Args:
        action: 操作类型 (login, password_reset, user_sync, etc.)
        target_user: 目标用户名
        details: 操作详情
    """
    try:
        from models.models import AdminLog, User, db
        
        admin_id = session.get('user_id')
        admin_username = session.get('username', 'Unknown')
        ip_address = request.remote_addr if request else 'system'
        
        log = AdminLog(
            admin_id=admin_id,
            action=(action or 'unknown')[:100],
            # 截断到列宽以内：公开入口的 target_user（邮箱）长度不可控，
            # 超长会导致 PG 插入失败且被上层 try/except 吞掉（审计静默丢失）
            target_user=(str(target_user)[:250] if target_user else None),
            details=(str(details)[:1000] if details else None),
            ip_address=(str(ip_address)[:50] if ip_address else None),
        )
        
        db.session.add(log)
        db.session.commit()
        
    except Exception as e:
        # 日志记录失败不应影响主流程
        print(f"[日志记录失败] {action}: {str(e)}")


def log_admin_action(action):
    """
    装饰器：自动记录管理员操作
    
    Args:
        action: 操作类型
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # 执行函数
            result = f(*args, **kwargs)
            
            # 记录日志
            target_user = kwargs.get('username') or kwargs.get('user_id', '')
            details = f"操作参数：{kwargs}"
            log_operation(action, str(target_user), details)
            
            return result
        return wrapped
    return decorator
