from pymysql import *
from utils.db_config import get_db_config

_DB_CONFIG = get_db_config()
conn = connect(**_DB_CONFIG)
cursor = conn.cursor()


def querys(sql,params,type='no_select'):
    params = tuple(params)
    cursor.execute(sql,params)
    if type != 'no_select':
        data_list = cursor.fetchall()
        conn.commit()
        return data_list
    else:
        conn.commit()
        return '执行成功'