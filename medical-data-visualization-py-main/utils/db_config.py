import os

import pymysql
from dotenv import load_dotenv


# 尝试基于项目根目录加载 .env，保证无论从哪个子目录运行脚本都能找到配置
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BASE_DIR)
_DOTENV_PATH = os.path.join(_PROJECT_ROOT, ".env")
if os.path.exists(_DOTENV_PATH):
    load_dotenv(_DOTENV_PATH)
else:
    # 回退到默认行为：从当前工作目录向上查找
    load_dotenv()


def get_db_config(**overrides):
    """统一获取 MySQL 连接配置，从环境变量中读取密码等信息。

    优先读取环境变量：
      - DB_HOST (默认 127.0.0.1)
      - DB_PORT (默认 3306)
      - DB_USER (默认 root)
      - DB_NAME (默认 medicalinfo)
      - DB_CHARSET (默认 utf8mb4)
      - DB_PASSWORD (必须提供，否则抛出异常)
    """
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    name = os.getenv("DB_NAME", "medicalinfo")
    charset = os.getenv("DB_CHARSET", "utf8mb4")
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise RuntimeError(
            "DB_PASSWORD is not set. 请在项目根目录的 .env 文件中配置数据库密码，如 DB_PASSWORD=your-password"
        )

    cfg = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": name,
        "charset": charset,
    }

    cfg.update(overrides)
    return cfg


def get_db_connection(**overrides):
    """获取一个新的 pymysql 连接，所有脚本统一通过这里创建连接。"""
    cfg = get_db_config(**overrides)
    return pymysql.connect(**cfg)


def get_sqlalchemy_url(**overrides) -> str:
    """构造 SQLAlchemy 使用的连接 URL，供 tree.py 等模块使用。"""
    cfg = get_db_config(**overrides)
    return (
        f"mysql+pymysql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}"
        f"/{cfg['database']}?charset={cfg['charset']}"
    )
