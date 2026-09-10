"""SQLAlchemy 基类。所有企业业务表携带 tenant_id，关联时同时约束租户。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
