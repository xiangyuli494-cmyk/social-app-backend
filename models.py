from supabase_client import db

# 表已在 Supabase 中通过 schema.sql 创建
# init_db() 保留用于兼容性，Supabase 模式下为空操作


def init_db():
    """Supabase 模式下表已通过 SQL Editor 创建，此函数为空操作"""
    pass


def get_db():
    """返回 Supabase 客户端"""
    return db()
