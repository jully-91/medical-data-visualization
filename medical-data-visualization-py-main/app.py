# -*- coding: utf-8 -*-
# 中文 Windows 控制台默认使用 GBK 编码，本项目日志中含有 emoji（如 ✅ / ❌），
# 直接 print 会抛 UnicodeEncodeError，导致启动中断或模型初始化残留在半成品状态。
# 这里把标准输出/错误流强制切到 UTF-8（errors="replace" 兜底，绝不因日志再抛异常）。
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from flask import Flask, request, jsonify, send_file
import os
import sys
import requests
import io
import csv
import json
from datetime import datetime
import re
from collections import Counter

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

from docx import Document
from docx.shared import Inches
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

from dotenv import load_dotenv
from openai import OpenAI

import pymysql
import pandas as pd

from utils.db_config import get_db_connection

from utils.getAllData import *
from utils.getPublicData import *
from machine.tree import *

load_dotenv()

# ================= [新增] AI 模块导入 =================
try:
    # 尝试从 machine/tree.py 导入 MedicalAI 类
    from machine.tree import MedicalAI
except ImportError as e:
    print(f"⚠️ 导入模型失败，请检查 machine/tree.py 是否存在。错误: {e}")
    MedicalAI = None

# ================= [新增] 爬虫调度模块导入 =================
try:
    spiders_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spiders')
    if spiders_dir not in sys.path:
        sys.path.append(spiders_dir)
    from crawler_scheduler import crawler_scheduler, disease_types
except ImportError as e:
    print(f"⚠️ 导入爬虫调度模块失败，请检查 spiders/crawler_scheduler.py 是否存在。错误: {e}")
    crawler_scheduler = None
    disease_types = []

app = Flask(__name__)

# ================= [新增] AI 引擎初始化 =================
ai_engine = None

# ================= [新增] 数据管理相关配置 =================

# 导入/导出模板列，与 cases 表结构对应（不含自增 id）
TEMPLATE_COLUMNS = [
    'type', 'gender', 'age', 'time', 'content',
    'docName', 'docHospital', 'department', 'detailUrl',
    'height', 'weight', 'illDuration', 'allergy'
]

REQUIRED_COLUMNS = ['type', 'gender', 'age', 'time', 'content']

CASES_COLUMN_INDEX = {
    'type': 1,
    'gender': 2,
    'age': 3,
    'time': 4,
    'content': 5,
    'docName': 6,
    'docHospital': 7,
    'department': 8,
    'detailUrl': 9,
    'height': 10,
    'weight': 11,
    'illDuration': 12,
    'allergy': 13,
}

FIELD_LABELS = {
    'type': '疾病类型',
    'gender': '性别',
    'age': '年龄',
    'time': '就诊时间',
    'content': '病情描述',
    'docName': '医生',
    'docHospital': '医院',
    'department': '科室',
    'detailUrl': '详情链接',
    'height': '身高',
    'weight': '体重',
    'illDuration': '病程',
    'allergy': '过敏史',
}


# ReportLab 中文字体配置，用于 PDF 报告避免出现方块/乱码
PDF_CHINESE_FONT_NAME = "SimSun"
PDF_CHINESE_FONT_PATHS = [
    r"C:\\Windows\\Fonts\\simsun.ttc",
    r"C:\\Windows\\Fonts\\SIMSUN.TTC",
    r"C:\\Windows\\Fonts\\msyh.ttc",
    r"C:\\Windows\\Fonts\\MSYH.TTC",
]

_pdf_font_registered = False


def _ensure_pdf_chinese_font():
    """确保为 ReportLab 注册中文字体，返回可用字体名称；若注册失败则返回 None。"""
    global _pdf_font_registered
    if _pdf_font_registered:
        return PDF_CHINESE_FONT_NAME

    for path in PDF_CHINESE_FONT_PATHS:
        try:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(PDF_CHINESE_FONT_NAME, path))
                _pdf_font_registered = True
                return PDF_CHINESE_FONT_NAME
        except Exception as e:
            print("注册 PDF 中文字体失败：", e)
            break
    return None


def _get_db_conn():
    """获取新的数据库连接，用于数据管理功能（统一从 utils.db_config 读取配置）。"""
    return get_db_connection()


def _ensure_data_management_tables():
    """初始化数据管理相关表，并预置爬虫数据源配置。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()

        # data_sources：数据源（爬虫）管理
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS data_sources (
              id INT NOT NULL AUTO_INCREMENT,
              code VARCHAR(64) NOT NULL,
              name VARCHAR(255) NOT NULL,
              disease VARCHAR(255) NOT NULL,
              type VARCHAR(50) NOT NULL DEFAULT '爬虫',
              description VARCHAR(512) DEFAULT NULL,
              enabled TINYINT(1) NOT NULL DEFAULT 1,
              status VARCHAR(50) NOT NULL DEFAULT 'idle',
              last_run_at DATETIME DEFAULT NULL,
              last_success_at DATETIME DEFAULT NULL,
              last_delta INT DEFAULT 0,
              total_records INT DEFAULT 0,
              last_message VARCHAR(1024) DEFAULT NULL,
              PRIMARY KEY (id),
              UNIQUE KEY uk_code (code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # data_versions：数据版本记录
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS data_versions (
              id INT NOT NULL AUTO_INCREMENT,
              name VARCHAR(255) NOT NULL,
              version_code VARCHAR(64) NOT NULL,
              operator VARCHAR(255) DEFAULT '系统',
              action VARCHAR(64) NOT NULL,
              description VARCHAR(1024) DEFAULT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              total_records INT DEFAULT 0,
              delta_records INT DEFAULT 0,
              PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # cases_snapshot：cases 表快照（用于版本回滚）
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cases_snapshot (
              id INT NOT NULL AUTO_INCREMENT,
              version_id INT NOT NULL,
              case_id INT DEFAULT NULL,
              type VARCHAR(255) DEFAULT NULL,
              gender VARCHAR(255) DEFAULT NULL,
              age VARCHAR(255) DEFAULT NULL,
              time VARCHAR(255) DEFAULT NULL,
              content VARCHAR(255) DEFAULT NULL,
              docName VARCHAR(255) DEFAULT NULL,
              docHospital VARCHAR(255) DEFAULT NULL,
              department VARCHAR(255) DEFAULT NULL,
              detailUrl VARCHAR(2555) DEFAULT NULL,
              height VARCHAR(255) DEFAULT NULL,
              weight VARCHAR(255) DEFAULT NULL,
              illDuration VARCHAR(255) DEFAULT NULL,
              allergy VARCHAR(255) DEFAULT NULL,
              PRIMARY KEY (id),
              KEY idx_version_id (version_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # 预置爬虫数据源（从 disease_types 列表生成）
        if disease_types:
            for disease in disease_types:
                code = disease  # 直接使用中文疾病名作为唯一编码
                name = f"{disease}病例爬虫"
                desc = f"自动抓取{disease}相关病例数据"
                cursor.execute(
                    """
                    INSERT INTO data_sources (code, name, disease, type, description, enabled, status)
                    VALUES (%s, %s, %s, %s, %s, 1, 'idle')
                    ON DUPLICATE KEY UPDATE
                      name = VALUES(name),
                      disease = VALUES(disease),
                      description = VALUES(description)
                    """,
                    (code, name, disease, '爬虫', desc)
                )

        conn.commit()
    except Exception as e:
        print(f"[System] 初始化数据管理表失败: {e}")
        if conn:
            conn.rollback()
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def _get_default_report_templates():
    """静态默认的统计类报告模板，用于首次初始化或数据库异常时回退。"""
    return [
        {
            "id": "tpl-stat-month",
            "name": "月度疾病统计报告",
            "type": "统计类",
            "scene": "用于展示某个月内各疾病类型、年龄段、科室就诊情况。",
            "version": "1.0",
            "status": "published",
            "updatedAt": "2025-12-01 10:20",
            "blocks": [
                {
                    "id": "b1",
                    "type": "text",
                    "config": {
                        "template": "本报告基于 {{startDate}} 至 {{endDate}} 期间的病例数据生成，仅供医疗决策与教学参考。"
                    },
                },
                {
                    "id": "b2",
                    "type": "kpi",
                    "config": {"source": "/getHomeData"},
                },
                {
                    "id": "b3",
                    "type": "chart",
                    "config": {
                        "chartType": "disease",
                        "desc": "主要疾病类型占比情况",
                    },
                },
                {
                    "id": "b4",
                    "type": "table",
                    "config": {
                        "source": "cases",
                        "fields": "type,gender,age,time,docHospital,department",
                    },
                },
            ],
            "versions": [
                {
                    "id": "v1",
                    "code": "V1.0",
                    "time": "2025-12-01",
                    "desc": "初始版本：包含概览说明、关键指标、疾病饼图与病例明细表。",
                }
            ],
        }
    ]


def _ensure_report_template_tables():
    """初始化报告模板相关表，并写入默认统计类模板。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS report_templates (
              id VARCHAR(64) NOT NULL,
              name VARCHAR(255) NOT NULL,
              type VARCHAR(50) NOT NULL,
              scene VARCHAR(255) DEFAULT NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'draft',
              version VARCHAR(20) NOT NULL DEFAULT '1.0',
              blocks_json JSON NOT NULL,
              versions_json JSON NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # 如果表为空，插入默认模板
        cursor.execute("SELECT COUNT(*) FROM report_templates")
        count = cursor.fetchone()[0] or 0
        if count == 0:
            default_templates = _get_default_report_templates()
            for tpl in default_templates:
                blocks_json = json.dumps(tpl.get("blocks") or [], ensure_ascii=False)
                versions_json = json.dumps(tpl.get("versions") or [], ensure_ascii=False)
                cursor.execute(
                    """
                    INSERT INTO report_templates
                      (id, name, type, scene, status, version, blocks_json, versions_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        tpl.get("id"),
                        tpl.get("name"),
                        tpl.get("type"),
                        tpl.get("scene"),
                        tpl.get("status", "draft"),
                        tpl.get("version", "1.0"),
                        blocks_json,
                        versions_json,
                    ),
                )

        conn.commit()
    except Exception as e:
        print("[System] 初始化报告模板表失败:", e)
        if conn:
            conn.rollback()
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def _create_version_with_snapshot(conn, action, description, operator='系统', name='病例事实表', delta_records=0):
    """在已有事务中创建版本记录并写入当前 cases 表的整表快照。"""
    cursor = conn.cursor()

    # 当前病例总数
    cursor.execute("SELECT COUNT(*) FROM cases")
    total_records = cursor.fetchone()[0] or 0

    version_code = datetime.now().strftime("%Y%m%d%H%M%S")

    cursor.execute(
        """
        INSERT INTO data_versions
          (name, version_code, operator, action, description, total_records, delta_records, created_at)
        VALUES
          (%s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        (name, version_code, operator, action, description, int(total_records), int(delta_records))
    )
    version_id = cursor.lastrowid

    # 写入 cases 快照
    cursor.execute(
        """
        INSERT INTO cases_snapshot (
          version_id, case_id, type, gender, age, time, content,
          docName, docHospital, department, detailUrl,
          height, weight, illDuration, allergy
        )
        SELECT
          %s, id, type, gender, age, time, content,
          docName, docHospital, department, detailUrl,
          height, weight, illDuration, allergy
        FROM cases
        """,
        (version_id,)
    )

    return version_id


def init_ai_model():
    """
    Flask 启动时执行：加载之前由 tree.py 训练并保存好的模型文件。
    """
    global ai_engine
    if MedicalAI:
        print("\n[System] 正在初始化 AI 服务...")
        ai_engine = MedicalAI()
        try:
            # 直接加载文件，不进行训练，实现秒开
            ai_engine.load_model()
            print("[System] ✅ AI 模型加载成功，服务已就绪！")
        except FileNotFoundError:
            print("[System] ⚠️ 未找到模型文件 (medical_model.pth)。")
            print("请务必先在 PyCharm 中右键运行 'machine/tree.py' 进行首次训练！")
        except Exception as e:
            print(f"[System] ❌ 模型加载出错: {e}")
    else:
        print("[System] 未找到 machine/tree.py，跳过 AI 初始化。")


# 启动时立即执行加载
init_ai_model()
_ensure_data_management_tables()
_ensure_report_template_tables()


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

@app.route('/getHomeData', methods=['GET', 'POST'])
def getHomeData():
    pieData = getPieData()
    configOne,wordData = getConfigOne()
    casesData = list(getAllCasesData())
    maxNum,maxType,maxDep,maxHos,maxAge,minAge = getFoundData()
    boyList,girlList,ratioData = getGenderData()
    circleData=getCircleData()
    xData,y1Data,y2Data = getBodyData()
    return jsonify({
        'message': 'success',
        'code': 200,
        'data': {
            'pieData': pieData,
            'configOne': configOne,
            'casesData': casesData,
            'maxNum': maxNum,
            'maxType': maxType,
            'maxDep': maxDep,
            'maxHos': maxHos,
            'maxAge': maxAge,
            'minAge': minAge,
            'boyList': boyList,
            'girlList': girlList,
            'ratioData': ratioData,
            'circleData': circleData,
            'wordData': wordData,
            'lastData': {
                'xData': xData,
                'y1Data': y1Data,
                'y2Data': y2Data
            }
        }
    })

@app.route('/submitModel', methods=['GET', 'POST'])
def submitModel():
    """调用优化后的预测函数，返回更详细的结果"""
    try:
        if request.method == 'POST':
            content = request.json.get('content', '')
            if not content:
                return jsonify({
                    'message': '失败',
                    'code': 400,
                    'data': {'resultData': '症状文本不能为空'}
                })

            # [修改] 1. 检查 AI 引擎是否正常启动
            if ai_engine is None:
                return jsonify({
                    'message': 'AI服务未就绪',
                    'code': 500,
                    'data': {'resultData': '后台 AI 模型未加载，请检查服务器日志'}
                })

            # [修改] 2. 调用 BERT 模型预测
            # ai_engine.predict 返回结构：{'prediction': {...}, 'similar_cases': [...]}
            ai_result = ai_engine.predict(content)

            prediction = ai_result['prediction']
            similar_cases = ai_result['similar_cases']

            return jsonify({
                'message': 'success',
                'code': 200,
                'data': {
                    'resultData': prediction['disease'],
                    # [修复] 之前这里乘了100，前端又乘了100导致变成2080%。现在只传 float，交给前端处理格式。
                    'confidence': float(prediction['confidence']),
                    'advice': prediction['advice'],
                    'similarCases': similar_cases
                }
            })
        else:
            return jsonify({
                'message': '仅支持POST请求',
                'code': 405,
                'data': {'resultData': ''}
            })
    except Exception as e:
        print(f"预测异常：{e}")
        return jsonify({
            'message': '预测失败',
            'code': 500,
            'data': {'resultData': f'错误：{str(e)}'}
        })

@app.route('/tableData', methods=['GET', 'POST'])
def tableData():
    tableDataList = getAllCasesData()
    # 按照原有逻辑，去掉 id，只保留业务字段供表格展示
    resultData = [x[1:] for x in tableDataList]
    # 同时单独返回每条记录的 id，供前端作为真实序号使用
    ids = [x[0] for x in tableDataList]
    return jsonify({
        'message': 'success',
        'code': 200,
        'data': {
            'resultData': resultData,
            'ids': ids
        }
    })

 

@app.route('/data/summary', methods=['GET'])
def data_summary():
    """数据统计：总量 / 今日更新 / 活跃数据源。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cases")
        total_records = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COALESCE(SUM(delta_records), 0) FROM data_versions WHERE DATE(created_at) = CURDATE()"
        )
        today_updates = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM data_sources WHERE enabled = 1 AND last_success_at >= NOW() - INTERVAL 1 DAY"
        )
        active_sources = cursor.fetchone()[0] or 0

        return jsonify({
            'message': 'success',
            'code': 200,
            'data': {
                'totalRecords': int(total_records),
                'todayUpdates': int(today_updates),
                'activeSources': int(active_sources)
            }
        })
    except Exception as e:
        print("数据统计接口异常：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/data/sources', methods=['GET'])
def list_data_sources():
    """列出所有数据源（主要是爬虫）。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code, name, disease, type, description, enabled, status, "
            "last_run_at, last_success_at, last_delta, total_records "
            "FROM data_sources ORDER BY id ASC"
        )
        rows = cursor.fetchall()

        def status_label(status):
            if status == 'success':
                return '运行中'
            if status == 'running':
                return '采集中'
            if status == 'error':
                return '异常'
            if status == 'idle':
                return '空闲'
            return status or '未知'

        def fmt_time(dt):
            if not dt:
                return '从未更新'
            if isinstance(dt, datetime):
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            return str(dt)

        data = []
        for r in rows:
            last_time = r[9] or r[8]
            data.append({
                'id': r[0],
                'code': r[1],
                'name': r[2],
                'disease': r[3],
                'type': r[4],
                'desc': r[5],
                'enabled': bool(r[6]),
                'status': r[7],
                'statusLabel': status_label(r[7]),
                'lastUpdate': fmt_time(last_time),
                'lastDelta': r[10],
                'totalRecords': r[11],
            })

        return jsonify({'message': 'success', 'code': 200, 'data': data})
    except Exception as e:
        print("数据源列表接口异常：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/data/sources/<code>/toggle', methods=['POST'])
def toggle_data_source(code):
    """启用/停用指定数据源。"""
    conn = None
    cursor = None
    try:
        body = request.get_json(force=True, silent=True) or {}
        target_enabled = body.get('enabled')

        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT enabled FROM data_sources WHERE code=%s", (code,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'message': 'not_found', 'code': 404, 'data': {}}), 404

        current_enabled = int(row[0]) == 1
        if target_enabled is None:
            target_enabled = not current_enabled

        cursor.execute(
            "UPDATE data_sources SET enabled=%s WHERE code=%s",
            (1 if target_enabled else 0, code)
        )
        conn.commit()

        return jsonify({
            'message': 'success',
            'code': 200,
            'data': {'code': code, 'enabled': bool(target_enabled)}
        })
    except Exception as e:
        if conn:
            conn.rollback()
        print("数据源启停接口异常：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/data/sources/<code>/run', methods=['POST'])
def run_data_source(code):
    """手动触发某个爬虫数据源执行爬取。"""
    if crawler_scheduler is None:
        return jsonify({
            'message': 'error',
            'code': 500,
            'data': {'error': '爬虫调度模块未正确加载，无法执行爬取'}
        }), 500

    conn = None
    cursor = None
    try:
        body = request.get_json(force=True, silent=True) or {}
        pages = int(body.get('pages') or 3)

        conn = _get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, disease, enabled, status FROM data_sources WHERE code=%s",
            (code,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'message': 'not_found', 'code': 404, 'data': {}}), 404

        _, disease, enabled, status = row
        if not int(enabled):
            return jsonify({
                'message': 'error',
                'code': 400,
                'data': {'error': '该数据源已停用，请先启用后再执行'}
            }), 400

        if status == 'running':
            return jsonify({
                'message': 'error',
                'code': 400,
                'data': {'error': '该数据源正在采集中，请稍后再试'}
            }), 400

        # 标记为运行中
        cursor.execute(
            "UPDATE data_sources SET status='running', last_run_at=NOW(), last_message=NULL WHERE code=%s",
            (code,)
        )
        conn.commit()

        # 采集前病例总数（按疾病类型）
        conn2 = _get_db_conn()
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM cases WHERE type=%s", (disease,))
        before_cnt = cur2.fetchone()[0] or 0
        cur2.close()
        conn2.close()

        ok = False
        error_msg = ''
        try:
            ok = bool(crawler_scheduler.crawl_disease(disease, pages=pages))
        except Exception as e:
            ok = False
            error_msg = str(e)

        # 采集完成后重新统计
        conn3 = _get_db_conn()
        cur3 = conn3.cursor()
        cur3.execute("SELECT COUNT(*) FROM cases WHERE type=%s", (disease,))
        after_cnt = cur3.fetchone()[0] or 0
        cur3.close()
        conn3.close()

        delta = int(after_cnt) - int(before_cnt)

        conn4 = _get_db_conn()
        cur4 = conn4.cursor()
        if ok:
            cur4.execute(
                "UPDATE data_sources SET status='success', last_success_at=NOW(), "
                "last_delta=%s, total_records=%s, last_message=%s WHERE code=%s",
                (delta, after_cnt, f"本次采集新增 {delta} 条记录", code)
            )
        else:
            cur4.execute(
                "UPDATE data_sources SET status='error', last_delta=%s, last_message=%s WHERE code=%s",
                (delta, error_msg or '爬虫执行失败', code)
            )

        # 记录版本与快照
        try:
            _create_version_with_snapshot(
                conn4,
                action='crawl',
                description=f"数据源 {code}（{disease}）手动爬取，新增 {delta} 条记录",
                operator='爬虫采集',
                delta_records=delta
            )
        except Exception as e:
            print("创建爬虫版本记录失败：", e)

        conn4.commit()
        cur4.close()
        conn4.close()

        return jsonify({
            'message': 'success',
            'code': 200,
            'data': {
                'code': code,
                'disease': disease,
                'delta': delta,
                'success': ok,
                'error': error_msg
            }
        })
    except Exception as e:
        print("数据源手动执行接口异常：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/data/import/template', methods=['GET'])
def download_import_template():
    """下载导入模板（支持 excel / csv），模板列只认固定结构。"""
    file_type = (request.args.get('type') or 'excel').lower()

    try:
        if file_type == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(TEMPLATE_COLUMNS)
            csv_bytes = output.getvalue().encode('utf-8-sig')
            buffer = io.BytesIO(csv_bytes)
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name='cases_import_template.csv',
                mimetype='text/csv'
            )

        # 默认为 Excel 模板
        df = pd.DataFrame(columns=TEMPLATE_COLUMNS)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='cases_template')
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='cases_import_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print("导入模板生成失败：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500


@app.route('/data/import', methods=['POST'])
def import_cases():
    """导入病例数据，支持 CSV / Excel，结构必须与模板完全一致。"""
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'message': 'error', 'code': 400, 'data': {'error': '未找到上传文件'}}), 400

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext == '.csv':
            df = pd.read_csv(file)
        elif ext in ('.xls', '.xlsx'):
            df = pd.read_excel(file, engine='openpyxl')
        else:
            return jsonify({'message': 'error', 'code': 400, 'data': {'error': '仅支持 CSV / Excel 文件导入'}}), 400

        cols = [str(c).strip() for c in df.columns]
        if cols != TEMPLATE_COLUMNS:
            return jsonify({
                'message': 'error',
                'code': 400,
                'data': {'error': '文件列结构与导入模板不一致，请先下载最新模板'}
            }), 400

        df = df.where(pd.notnull(df), None)

        invalid_rows = []
        for idx, row in df.iterrows():
            missing = []
            for col in REQUIRED_COLUMNS:
                val = row.get(col)
                if val is None or (isinstance(val, str) and not val.strip()):
                    missing.append(col)
            if missing:
                invalid_rows.append(idx + 2)  # +2: header + 1-based 行号

        if invalid_rows:
            sample = invalid_rows[:5]
            msg = f"部分行缺少必填字段（示例行号：{sample}），已终止导入。"
            return jsonify({'message': 'error', 'code': 400, 'data': {'error': msg}}), 400

        conn = _get_db_conn()
        cursor = conn.cursor()
        try:
            sql = (
                "INSERT INTO cases (type, gender, age, time, content, "
                "docName, docHospital, department, detailUrl, height, weight, illDuration, allergy) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            data = []
            for _, row in df.iterrows():
                values = []
                for col in TEMPLATE_COLUMNS:
                    v = row.get(col)
                    if isinstance(v, float) and pd.isna(v):
                        v = None
                    values.append(v if v is not None else None)
                data.append(tuple(values))

            cursor.executemany(sql, data)
            inserted = cursor.rowcount or len(data)

            # 记录版本与快照
            _create_version_with_snapshot(
                conn,
                action='import',
                description=f"文件 {filename} 导入，新增 {inserted} 条记录",
                operator='数据导入',
                delta_records=inserted
            )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

        return jsonify({
            'message': 'success',
            'code': 200,
            'data': {'inserted': inserted}
        })
    except Exception as e:
        print("导入病例数据失败：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500


@app.route('/data/export', methods=['GET'])
def export_cases():
    """导出病例数据，默认 CSV，可通过 format=excel 导出为 Excel，format=json 导出 JSON。"""
    fmt = (request.args.get('format') or 'csv').lower()
    try:
        conn = _get_db_conn()
        query = "SELECT id, " + ",".join(TEMPLATE_COLUMNS) + " FROM cases"
        df = pd.read_sql(query, conn)
        conn.close()

        if fmt == 'excel':
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='cases')
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name='cases_export.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        if fmt == 'json':
            json_str = df.to_json(orient='records', force_ascii=False)
            buffer = io.BytesIO(json_str.encode('utf-8'))
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name='cases_export.json',
                mimetype='application/json; charset=utf-8'
            )

        # 默认 CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        csv_bytes = output.getvalue().encode('utf-8-sig')
        buffer = io.BytesIO(csv_bytes)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='cases_export.csv',
            mimetype='text/csv'
        )
    except Exception as e:
        print("导出病例数据失败：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500


@app.route('/data/versions', methods=['GET'])
def list_data_versions():
    """列出最近的数据版本记录。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, version_code, operator, description, created_at, total_records, delta_records "
            "FROM data_versions ORDER BY created_at DESC LIMIT 50"
        )
        rows = cursor.fetchall()

        versions = []
        for r in rows:
            created_at = r[5]
            if isinstance(created_at, datetime):
                t = created_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                t = str(created_at)
            versions.append({
                'id': r[0],
                'name': r[1],
                'version': r[2],
                'operator': r[3],
                'desc': r[4] or '',
                'time': t,
                'totalRecords': r[6],
                'deltaRecords': r[7],
            })

        return jsonify({'message': 'success', 'code': 200, 'data': versions})
    except Exception as e:
        print("数据版本列表接口异常：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/data/versions/<int:version_id>/rollback', methods=['POST'])
def rollback_version(version_id):
    """回滚到指定版本：用该版本的 cases 快照替换当前 cases 表。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM data_versions WHERE id=%s", (version_id,))
        if not cursor.fetchone():
            return jsonify({'message': 'not_found', 'code': 404, 'data': {}}), 404

        cursor.execute("SELECT COUNT(*) FROM cases")
        before_cnt = cursor.fetchone()[0] or 0

        # 清空当前 cases
        cursor.execute("DELETE FROM cases")

        # 从快照写回
        cursor.execute(
            """
            INSERT INTO cases (
              type, gender, age, time, content,
              docName, docHospital, department, detailUrl,
              height, weight, illDuration, allergy
            )
            SELECT
              type, gender, age, time, content,
              docName, docHospital, department, detailUrl,
              height, weight, illDuration, allergy
            FROM cases_snapshot
            WHERE version_id = %s
            """,
            (version_id,)
        )

        cursor.execute("SELECT COUNT(*) FROM cases")
        after_cnt = cursor.fetchone()[0] or 0
        delta = int(after_cnt) - int(before_cnt)

        # 新增一次回滚版本记录（也会写入当前快照）
        _create_version_with_snapshot(
            conn,
            action='rollback',
            description=f'回滚到版本 {version_id}（记录数由 {before_cnt} 变为 {after_cnt}）',
            operator='系统',
            delta_records=delta
        )

        conn.commit()

        return jsonify({
            'message': 'success',
            'code': 200,
            'data': {'versionId': version_id, 'before': before_cnt, 'after': after_cnt, 'delta': delta}
        })
    except Exception as e:
        if conn:
            conn.rollback()
        print("数据版本回滚接口异常：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ================= 报告模板 & 生成 =================


def _get_report_templates():
    """从数据库 report_templates 读取模板列表；异常或空表时退回默认模板。"""
    conn = None
    cursor = None
    templates = []
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, type, scene, status, version, updated_at, blocks_json, versions_json "
            "FROM report_templates ORDER BY updated_at DESC"
        )
        rows = cursor.fetchall()
        for r in rows:
            blocks_raw = r[7]
            versions_raw = r[8]
            try:
                if isinstance(blocks_raw, str):
                    blocks = json.loads(blocks_raw)
                elif isinstance(blocks_raw, (bytes, bytearray)):
                    blocks = json.loads(blocks_raw.decode("utf-8"))
                else:
                    blocks = blocks_raw or []
            except Exception:
                blocks = []

            try:
                if isinstance(versions_raw, str):
                    versions = json.loads(versions_raw)
                elif isinstance(versions_raw, (bytes, bytearray)):
                    versions = json.loads(versions_raw.decode("utf-8"))
                else:
                    versions = versions_raw or []
            except Exception:
                versions = []

            updated_at = r[6]
            if isinstance(updated_at, datetime):
                updated_str = updated_at.strftime("%Y-%m-%d %H:%M")
            else:
                updated_str = str(updated_at) if updated_at is not None else ""

            templates.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "type": r[2],
                    "scene": r[3] or "",
                    "status": r[4],
                    "version": r[5],
                    "updatedAt": updated_str,
                    "blocks": blocks,
                    "versions": versions,
                }
            )
    except Exception as e:
        print("加载报告模板失败，将使用内置默认模板。", e)
        templates = _get_default_report_templates()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not templates:
        templates = _get_default_report_templates()

    return templates


@app.route('/templates', methods=['GET'])
def get_templates():
    templates = _get_report_templates()

    return jsonify({
        'message': 'success',
        'code': 200,
        'data': templates
    })


@app.route('/templates/save', methods=['POST'])
def save_template():
    """新建或更新报告模板（统计类），支持前端传入完整 blocks / versions 结构进行持久化。"""
    data = request.get_json(force=True) or {}

    template_id = data.get('id') or data.get('templateId')
    if not template_id:
        return jsonify({'message': 'error', 'code': 400, 'data': {'error': '缺少模板 id'}}), 400

    name = data.get('name') or '未命名模板'
    tpl_type = data.get('type') or '统计类'
    scene = data.get('scene') or ''
    status = data.get('status') or 'draft'
    version = data.get('version') or '1.0'
    blocks = data.get('blocks') or []
    versions = data.get('versions') or []

    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()

        blocks_json = json.dumps(blocks, ensure_ascii=False)
        versions_json = json.dumps(versions, ensure_ascii=False)

        cursor.execute(
            """
            INSERT INTO report_templates
              (id, name, type, scene, status, version, blocks_json, versions_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              name = VALUES(name),
              type = VALUES(type),
              scene = VALUES(scene),
              status = VALUES(status),
              version = VALUES(version),
              blocks_json = VALUES(blocks_json),
              versions_json = VALUES(versions_json)
            """,
            (template_id, name, tpl_type, scene, status, version, blocks_json, versions_json),
        )
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print("保存报告模板失败：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # 返回最新的该模板数据
    templates = _get_report_templates()
    tpl = None
    for item in templates:
        if item.get('id') == template_id:
            tpl = item
            break

    return jsonify({'message': 'success', 'code': 200, 'data': tpl or {}})


@app.route('/templates/<template_id>/offline', methods=['POST'])
def offline_template(template_id):
    """将指定模板状态置为 offline（下架）。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE report_templates SET status='offline' WHERE id=%s",
            (template_id,),
        )
        if cursor.rowcount == 0:
            return jsonify({'message': 'not_found', 'code': 404, 'data': {}}), 404
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print("下架报告模板失败：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    templates = _get_report_templates()
    tpl = None
    for item in templates:
        if item.get('id') == template_id:
            tpl = item
            break

    return jsonify({'message': 'success', 'code': 200, 'data': tpl or {}})


@app.route('/templates/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """物理删除指定模板记录。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM report_templates WHERE id=%s", (template_id,))
        if cursor.rowcount == 0:
            return jsonify({'message': 'not_found', 'code': 404, 'data': {}}), 404
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print("删除报告模板失败：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return jsonify({'message': 'success', 'code': 200, 'data': {}})


@app.route('/templates/<template_id>/publish', methods=['POST'])
def publish_template(template_id):
    """将指定模板状态置为 published。"""
    conn = None
    cursor = None
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE report_templates SET status='published' WHERE id=%s",
            (template_id,),
        )
        if cursor.rowcount == 0:
            return jsonify({'message': 'not_found', 'code': 404, 'data': {}}), 404
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print("发布报告模板失败：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    templates = _get_report_templates()
    tpl = None
    for item in templates:
        if item.get('id') == template_id:
            tpl = item
            break

    return jsonify({'message': 'success', 'code': 200, 'data': tpl or {}})


def _parse_filter_date(date_str):
    """将前端 startDate / endDate（YYYY-MM-DD）转换为统一的月份-日期基准（年固定为 2000）。"""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(str(date_str), "%Y-%m-%d")
        return datetime(2000, dt.month, dt.day)
    except Exception:
        return None


def _parse_case_date(value):
    """解析 cases.time 字段，支持 'MM.DD' 或 'YYYY-MM-DD' 两种形式。"""
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m.%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return datetime(2000, dt.month, dt.day)
        except Exception:
            continue
    return None


def _filter_cases(cases, params):
    """根据前端传入的 params 中的 caseFilter 与时间范围进行过滤。

    cases: 来自 medicalinfo.cases 的记录（id,type,gender,age,time,...）
    """
    case_filter = params.get('caseFilter') or {}
    disease = case_filter.get('disease') or ''
    gender = case_filter.get('gender') or ''
    hospital = case_filter.get('hospital') or ''

    # 时间范围：前端使用 YYYY-MM-DD，这里统一转换成 2000 年的日期，只比较月日
    start_dt = _parse_filter_date(params.get('startDate') or '')
    end_dt = _parse_filter_date(params.get('endDate') or '')

    result = []
    for row in cases:
        # row 结构见 medicalinfo.sql：id,type,gender,age,time,content,docName,docHospital,department,...
        r_type = row[1]
        r_gender = row[2]
        r_hospital = row[7]
        r_time_raw = row[4]
        r_date = _parse_case_date(r_time_raw)

        if disease and r_type != disease:
            continue
        if gender and r_gender != gender:
            continue
        if hospital and r_hospital != hospital:
            continue
        if start_dt and (not r_date or r_date < start_dt):
            continue
        if end_dt and (not r_date or r_date > end_dt):
            continue

        result.append(row)
    return result


def _build_kpi(cases):
    total = len(cases)
    ages = []
    for r in cases:
        try:
            ages.append(float(r[3]))
        except Exception:
            continue
    avg_age = round(sum(ages) / len(ages), 1) if ages else None

    disease_count = {}
    for r in cases:
        t = r[1]
        disease_count[t] = disease_count.get(t, 0) + 1
    top_disease = None
    if disease_count:
        top_disease = max(disease_count.items(), key=lambda x: x[1])[0]

    return [
        {
            "key": "total",
            "label": "病例总数",
            "value": total,
            "desc": "筛选条件下的病例总量。"
        },
        {
            "key": "avgAge",
            "label": "平均年龄",
            "value": avg_age,
            "desc": "按病例年龄字段计算得到。"
        },
        {
            "key": "topDisease",
            "label": "最多疾病类型",
            "value": top_disease,
            "desc": "在筛选范围内出现次数最高的疾病。"
        }
    ]


def _build_top_disease_chart_bytes(filtered_cases):
    """生成疾病分布 Top5 柱状图的 PNG 字节，用于 PDF / Word 报告导出。"""
    if not filtered_cases:
        return None

    counts = Counter()
    for r in filtered_cases:
        if len(r) > 1:
            t = r[1] or "未知"
            counts[t] += 1

    if not counts:
        return None

    top_items = counts.most_common(5)
    labels = [item[0] for item in top_items]
    values = [item[1] for item in top_items]

    try:
        plt.rcParams["font.sans-serif"] = ["SimSun", "Microsoft YaHei", "Arial Unicode MS"]
        plt.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(figsize=(4, 3), dpi=120)
        ax.bar(labels, values, color="#4e79a7")
        ax.set_title("疾病分布 Top5")
        ax.set_ylabel("病例数")
        ax.set_xlabel("疾病类型")
        for i, v in enumerate(values):
            ax.text(i, v, str(v), ha="center", va="bottom", fontsize=9)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        print("生成疾病分布图失败：", e)
        return None


def _build_dimension_chart_for_export(filtered_cases, params):
    """根据前端选择的维度（age / gender / department）生成一组统计图。

    返回列表 charts：[{"title": ..., "bytes": ...}, ...]
    - 如果未选择维度或都没有数据，则退回到一张“疾病分布（Top 5）”。
    """
    dims = []
    try:
        dims = params.get('dimensions') or []
        if not isinstance(dims, list):
            dims = []
    except Exception:
        dims = []

    charts = []

    def _build_bar(labels, values, title, xlabel):
        try:
            plt.rcParams["font.sans-serif"] = ["SimSun", "Microsoft YaHei", "Arial Unicode MS"]
            plt.rcParams["axes.unicode_minus"] = False
            fig, ax = plt.subplots(figsize=(4, 3), dpi=120)
            ax.bar(labels, values, color="#4e79a7")
            ax.set_title(title)
            ax.set_ylabel("病例数")
            ax.set_xlabel(xlabel)
            for i, v in enumerate(values):
                ax.text(i, v, str(v), ha="center", va="bottom", fontsize=9)
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()
        except Exception as e:
            print("生成维度统计图失败：", e)
            return None

    # 年龄段维度（优先）
    if 'age' in dims:
        bins = {
            "<18": 0,
            "18-30": 0,
            "31-45": 0,
            "46-60": 0,
            ">60": 0,
        }
        for r in filtered_cases:
            if len(r) > 3:
                try:
                    age = float(r[3])
                except Exception:
                    continue
                if age < 18:
                    bins["<18"] += 1
                elif age <= 30:
                    bins["18-30"] += 1
                elif age <= 45:
                    bins["31-45"] += 1
                elif age <= 60:
                    bins["46-60"] += 1
                else:
                    bins[">60"] += 1
        labels = [k for k, v in bins.items() if v > 0]
        values = [v for v in bins.values() if v > 0]
        if labels:
            img_bytes = _build_bar(labels, values, "按年龄段分布", "年龄段")
            if img_bytes:
                charts.append({"title": "按年龄段分布", "bytes": img_bytes})

    # 性别维度（其次）
    if 'gender' in dims:
        counts = Counter()
        for r in filtered_cases:
            if len(r) > 2:
                g = (r[2] or "未知").strip() or "未知"
                counts[g] += 1
        if counts:
            labels = list(counts.keys())
            values = [counts[k] for k in labels]
            img_bytes = _build_bar(labels, values, "按性别分布", "性别")
            if img_bytes:
                charts.append({"title": "按性别分布", "bytes": img_bytes})

    # 科室维度（最后）
    if 'department' in dims:
        counts = Counter()
        for r in filtered_cases:
            if len(r) > 8:
                d = (r[8] or "未知").strip() or "未知"
                counts[d] += 1
        if counts:
            top_items = counts.most_common(5)
            labels = [item[0] for item in top_items]
            values = [item[1] for item in top_items]
            img_bytes = _build_bar(labels, values, "按科室分布 Top5", "科室")
            if img_bytes:
                charts.append({"title": "按科室分布（Top 5）", "bytes": img_bytes})

    # 如果完全没有选择维度或都没有数据，则退回疾病分布 Top5
    if not charts:
        fallback = _build_top_disease_chart_bytes(filtered_cases)
        if fallback:
            charts.append({"title": "疾病分布（Top 5）", "bytes": fallback})

    return charts


def _section_no_to_cn(no):
    """将章节序号转换为中文数字，用于“二、三、四”这样的标题。"""
    mapping = {
        1: "一",
        2: "二",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
        10: "十",
    }
    return mapping.get(no, str(no))


def _apply_variables_to_text(template_str, var_map):
    if not template_str:
        return ""

    def replace(match):
        key = match.group(1).strip()
        value = var_map.get(key)
        if value is None or value == "":
            return match.group(0)
        return str(value)

    return re.sub(r"{{(.*?)}}", replace, template_str)


def _build_sections_from_template(template, filtered_cases, kpi, params):
    sections = []
    blocks = template.get('blocks') or []

    case_filter = params.get('caseFilter') or {}

    top_disease_value = None
    for item in kpi:
        if item.get('key') == 'topDisease':
            top_disease_value = item.get('value')
            break

    var_map = {
        'startDate': params.get('startDate') or '',
        'endDate': params.get('endDate') or '',
        'disease': case_filter.get('disease') or '',
        'gender': case_filter.get('gender') or '',
        'hospital': case_filter.get('hospital') or '',
        'total_cases': len(filtered_cases),
        'top_disease': top_disease_value or '',
        'query': params.get('query') or case_filter.get('disease') or '',
    }

    for blk in blocks:
        blk_type = blk.get('type')
        cfg = blk.get('config') or {}
        blk_id = blk.get('id')

        if blk_type == 'text':
            tpl_str = cfg.get('template') or ''
            content = _apply_variables_to_text(tpl_str, var_map)
            sections.append({
                "id": blk_id,
                "type": "text",
                "typeLabel": "文本说明",
                "title": "诊断说明 / 报告概述",
                "runtimeContent": content,
            })
        elif blk_type == 'kpi':
            sections.append({
                "id": blk_id,
                "type": "kpi",
                "typeLabel": "关键指标",
                "title": "关键统计指标",
                "runtimeKpi": kpi,
            })
        elif blk_type == 'chart':
            sections.append({
                "id": blk_id,
                "type": "chart",
                "typeLabel": "统计图表",
                "title": "统计图表",
                "chartDesc": cfg.get('desc') or "",
                "chartType": cfg.get('chartType') or "",
                "data": {},
            })
        elif blk_type == 'table':
            source = cfg.get('source') or ''
            if source == 'cases':
                rows_source = filtered_cases
            elif source == 'similar_cases':
                rows_source = filtered_cases
            else:
                continue
            fields_str = cfg.get('fields') or ''
            field_names = [f.strip() for f in fields_str.split(',') if f.strip()]
            if not field_names:
                continue

            header = [FIELD_LABELS.get(f, f) for f in field_names]
            rows = []
            for r in rows_source[:10]:
                row_vals = []
                for fname in field_names:
                    idx = CASES_COLUMN_INDEX.get(fname)
                    if idx is None or idx >= len(r):
                        row_vals.append("")
                    else:
                        row_vals.append(r[idx])
                rows.append(row_vals)

            sections.append({
                "id": blk_id,
                "type": "table",
                "typeLabel": "病例表格",
                "title": "部分病例明细（Top 10）",
                "runtimeHeader": header,
                "runtimeRows": rows,
            })

    return sections


@app.route('/reports/generate', methods=['POST'])
def generate_report():
    """
    报告生成 demo：
    - 从 cases 数据中做简单过滤与统计
    - 返回 docs/backend_api_report.md 中定义的 sections 结构
    """
    data = request.get_json(force=True) or {}
    template_id = data.get('templateId')
    params = data.get('params') or {}

    all_cases = list(getAllCasesData())
    filtered_cases = _filter_cases(all_cases, params)
    kpi = _build_kpi(filtered_cases)

    sections = []

    # 1）优先使用前端本次请求中附带的模板结构，
    # 确保在未持久化到数据库前，模板管理页面的编辑结果也能生效。
    tpl = data.get('template') or None

    # 2）如未提供 template 或结构不完整，则退回到后端内置模板集合，
    # 按 templateId 进行匹配查找。
    if not tpl or not tpl.get('blocks'):
        templates = _get_report_templates()
        if template_id:
            for item in templates:
                if item.get('id') == template_id:
                    tpl = item
                    break

    if tpl and tpl.get('blocks'):
        sections = _build_sections_from_template(tpl, filtered_cases, kpi, params)

    if not sections:
        text_section = {
            "id": "text-1",
            "type": "text",
            "typeLabel": "文本说明",
            "title": "诊断说明 / 报告概述",
            "runtimeContent": f"本报告基于模板 {template_id or '（未指定模板）'}，共筛选出 {len(filtered_cases)} 条病例。"
        }

        kpi_section = {
            "id": "kpi-1",
            "type": "kpi",
            "typeLabel": "关键指标",
            "title": "关键统计指标",
            "runtimeKpi": kpi
        }

        header = ["疾病类型", "性别", "年龄", "就诊时间", "医生", "医院", "科室"]
        rows = []
        for r in filtered_cases[:10]:
            rows.append([r[1], r[2], r[3], r[4], r[6], r[7], r[8]])

        table_section = {
            "id": "table-1",
            "type": "table",
            "typeLabel": "病例表格",
            "title": "部分病例明细（Top 10）",
            "runtimeHeader": header,
            "runtimeRows": rows
        }

        sections = [text_section, kpi_section, table_section]

    return jsonify({
        "message": "success",
        "code": 200,
        "data": {
            "sections": sections
        }
    })


@app.route('/reports/export', methods=['POST'])
def export_report():
    """根据当前筛选条件与模板导出报告数据，默认 Excel，可选 CSV。"""
    data = request.get_json(force=True) or {}
    template_id = data.get('templateId')
    params = data.get('params') or {}
    fmt = (data.get('format') or 'excel').lower()
    sections_from_client = data.get('sections') or []

    all_cases = list(getAllCasesData())
    filtered_cases = _filter_cases(all_cases, params)
    kpi = _build_kpi(filtered_cases)

    tpl = data.get('template') or None
    if not tpl or not tpl.get('blocks'):
        templates = _get_report_templates()
        if template_id:
            for item in templates:
                if item.get('id') == template_id:
                    tpl = item
                    break

    if tpl and tpl.get('blocks'):
        has_chart_block = any(b.get('type') == 'chart' for b in (tpl.get('blocks') or []))
    else:
        has_chart_block = False

    # sections：导出时优先使用前端传来的 previewSections，保证与预览一致；
    # 若前端未传，则退回到按模板生成的 sections。
    if sections_from_client:
        sections = sections_from_client
    elif tpl and tpl.get('blocks'):
        sections = _build_sections_from_template(tpl, filtered_cases, kpi, params)
    else:
        sections = []

    # 构造摘要 DataFrame
    summary_rows = []
    title = params.get('title') or '医疗数据分析报告'
    case_filter = params.get('caseFilter') or {}
    summary_rows.append({'类别': '报告参数', '键': '标题', '值': title})
    summary_rows.append({'类别': '报告参数', '键': '起始日期', '值': params.get('startDate') or ''})
    summary_rows.append({'类别': '报告参数', '键': '结束日期', '值': params.get('endDate') or ''})
    summary_rows.append({'类别': '报告参数', '键': '疾病筛选', '值': case_filter.get('disease') or '全部'})
    summary_rows.append({'类别': '报告参数', '键': '性别筛选', '值': case_filter.get('gender') or '全部'})
    summary_rows.append({'类别': '报告参数', '键': '医院筛选', '值': case_filter.get('hospital') or '全部'})
    summary_rows.append({'类别': '报告参数', '键': '病例条数', '值': len(filtered_cases)})

    for item in kpi:
        summary_rows.append({
            '类别': '关键指标',
            '键': item.get('label'),
            '值': item.get('value'),
            '说明': item.get('desc'),
        })

    # DeepSeek 智能诊断：优先从 sections 中的“智能诊断”文本模块获取；
    # 若不存在且前端勾选了 useLLM，则调用 _build_llm_summary 补充生成。
    llm_summary = None
    try:
        for sec in sections:
            if sec.get('type') != 'text':
                continue
            sec_title = (sec.get('title') or '')
            type_label = (sec.get('typeLabel') or '')
            sec_id = sec.get('id') or ''
            if (
                sec_id == 'llm-summary'
                or '智能诊断' in sec_title
                or '智能诊断' in type_label
            ):
                content = sec.get('runtimeContent') or ''
                if content:
                    llm_summary = str(content).strip()
                    break
    except Exception:
        llm_summary = None

    if not llm_summary and params.get('useLLM'):
        try:
            llm_summary = _build_llm_summary(title, kpi, params)
        except Exception as e:
            print("生成智能诊断说明失败：", e)
            llm_summary = None

    if llm_summary:
        summary_rows.append({
            '类别': '智能诊断',
            '键': '智能诊断说明',
            '值': llm_summary,
        })

    summary_df = pd.DataFrame(summary_rows)

    # 构造病例明细 DataFrame（按当前筛选条件）
    case_dicts = []
    for r in filtered_cases:
        row = {'id': r[0]}
        for col in TEMPLATE_COLUMNS:
            idx = CASES_COLUMN_INDEX.get(col)
            if idx is not None and idx < len(r):
                row[col] = r[idx]
            else:
                row[col] = None
        case_dicts.append(row)

    cases_df = pd.DataFrame(case_dicts)

    # 维度图表列表（仅当模板中存在图表模块时才生成；否则不生成图表）
    if has_chart_block:
        charts = _build_dimension_chart_for_export(filtered_cases, params)
    else:
        charts = []

    try:
        if fmt == 'csv':
            # 仅导出病例表为 CSV，摘要可在 Excel / Word / PDF 中查看
            output = io.StringIO()
            cases_df.to_csv(output, index=False)
            csv_bytes = output.getvalue().encode('utf-8-sig')
            buffer = io.BytesIO(csv_bytes)
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name='report_export.csv',
                mimetype='text/csv'
            )

        if fmt == 'word':
            # 生成 Word 报告：
            # 1）按模板 / 预览中的文本模块顺序输出各节（包含用户手动编辑内容和 LLM 文本）；
            # 2）随后输出“报告参数”“关键指标”“图表”“病例明细”等结构化内容。
            buffer = io.BytesIO()
            doc = Document()

            doc.add_heading(title, level=1)

            section_no = 0

            # 一、二、...：文本模块（按 sections 顺序）
            text_sections = [s for s in sections if s.get('type') == 'text']
            for sec in text_sections:
                section_no += 1
                sec_title = sec.get('title') or '文本说明'
                doc.add_heading(f"{_section_no_to_cn(section_no)}、{sec_title}", level=2)
                content = sec.get('runtimeContent') or ''
                if content:
                    for line in str(content).splitlines():
                        doc.add_paragraph(line)

            # 后续一节：报告参数
            section_no += 1
            doc.add_heading(f"{_section_no_to_cn(section_no)}、报告参数", level=2)
            for row in summary_rows:
                if row['类别'] == '报告参数':
                    key = row.get('键', '')
                    value = row.get('值', '')
                    doc.add_paragraph(f"{key}：{value}")

            # 再下一节：关键指标
            kpi_items = [r for r in summary_rows if r['类别'] == '关键指标']
            if kpi_items:
                section_no += 1
                doc.add_heading(f"{_section_no_to_cn(section_no)}、关键指标", level=2)
                table = doc.add_table(rows=1, cols=3)
                hdr_cells = table.rows[0].cells
                hdr_cells[0].text = '指标'
                hdr_cells[1].text = '数值'
                hdr_cells[2].text = '说明'
                for item in kpi_items:
                    row_cells = table.add_row().cells
                    row_cells[0].text = str(item.get('键', ''))
                    row_cells[1].text = str(item.get('值', ''))
                    row_cells[2].text = str(item.get('说明', ''))

            # 继续：维度统计图
            for ch in charts:
                if not ch or not ch.get('bytes'):
                    continue
                section_no += 1
                title_text = ch.get('title') or '维度统计'
                doc.add_heading(f"{_section_no_to_cn(section_no)}、{title_text}", level=2)
                chart_stream = io.BytesIO(ch['bytes'])
                doc.add_picture(chart_stream, width=Inches(4.5))

            # 最后一节：部分病例明细（前 50 条）
            if filtered_cases:
                section_no += 1
                heading_text = f"{_section_no_to_cn(section_no)}、部分病例明细（前 50 条）"
                doc.add_heading(heading_text, level=2)
                display_cols = [
                    ('type', '疾病类型'),
                    ('gender', '性别'),
                    ('age', '年龄'),
                    ('time', '就诊时间'),
                    ('docHospital', '医院'),
                    ('department', '科室'),
                ]
                table = doc.add_table(rows=1, cols=len(display_cols))
                hdr_cells = table.rows[0].cells
                for i, (_, label) in enumerate(display_cols):
                    hdr_cells[i].text = label

                for r in filtered_cases[:50]:
                    row_cells = table.add_row().cells
                    row_cells[0].text = '' if r[1] is None else str(r[1])
                    row_cells[1].text = '' if r[2] is None else str(r[2])
                    row_cells[2].text = '' if r[3] is None else str(r[3])
                    row_cells[3].text = '' if r[4] is None else str(r[4])
                    row_cells[4].text = '' if r[7] is None else str(r[7])
                    row_cells[5].text = '' if r[8] is None else str(r[8])

            doc.add_page_break()
            doc.save(buffer)
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name='report_export.docx',
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

        if fmt == 'pdf':
            # 生成 PDF 报告：以文本形式展示模板文本、摘要与部分病例
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            y = height - 40

            # 为 PDF 设置中文字体，避免中文显示为方块/乱码
            font_name = _ensure_pdf_chinese_font()
            if font_name:
                c.setFont(font_name, 11)
            else:
                c.setFont("Helvetica", 11)

            def draw_line(text):
                """在当前行绘制一段文本，自动按页面宽度换行，并处理分页。"""
                nonlocal y
                if text is None:
                    text = ""
                text = str(text)
                max_width = width - 80  # 左右各留 40 边距
                font_used = font_name or "Helvetica"

                # 支持显式换行符：逐行处理
                for raw_line in text.split("\n"):
                    line = raw_line
                    # 空行：仅向下移动一行
                    if line == "":
                        y -= 14
                        if y < 40:
                            c.showPage()
                            y = height - 40
                            if font_name:
                                c.setFont(font_name, 11)
                            else:
                                c.setFont("Helvetica", 11)
                        continue

                    while line:
                        # 若整行宽度已在可用范围内，直接输出
                        if pdfmetrics.stringWidth(line, font_used, 11) <= max_width:
                            c.drawString(40, y, line)
                            y -= 14
                            if y < 40:
                                c.showPage()
                                y = height - 40
                                if font_name:
                                    c.setFont(font_name, 11)
                                else:
                                    c.setFont("Helvetica", 11)
                            break

                        # 否则从后往前裁剪到合适长度
                        cut = len(line)
                        while cut > 0 and pdfmetrics.stringWidth(line[:cut], font_used, 11) > max_width:
                            cut -= 1
                        if cut <= 0:
                            # 防御性退出，避免死循环
                            break
                        part = line[:cut]
                        c.drawString(40, y, part)
                        y -= 14
                        if y < 40:
                            c.showPage()
                            y = height - 40
                            if font_name:
                                c.setFont(font_name, 11)
                            else:
                                c.setFont("Helvetica", 11)
                        line = line[cut:]

            draw_line(title)
            draw_line("")

            section_no = 0

            # 一、二、...：文本模块（按 sections 顺序）
            text_sections = [s for s in sections if s.get('type') == 'text']
            for sec in text_sections:
                section_no += 1
                sec_title = sec.get('title') or '文本说明'
                draw_line(f"{_section_no_to_cn(section_no)}、{sec_title}")
                content = sec.get('runtimeContent') or ''
                if content:
                    for line in str(content).splitlines():
                        draw_line(line)
                draw_line("")

            # 后续一节：报告参数
            section_no += 1
            draw_line(f"{_section_no_to_cn(section_no)}、报告参数")
            for row in summary_rows:
                if row['类别'] == '报告参数':
                    key = row.get('键', '')
                    value = row.get('值', '')
                    draw_line(f"- {key}：{value}")

            kpi_items = [r for r in summary_rows if r['类别'] == '关键指标']
            if kpi_items:
                draw_line("")
                section_no += 1
                draw_line(f"{_section_no_to_cn(section_no)}、关键指标")
                for item in kpi_items:
                    label = item.get('键', '')
                    value = item.get('值', '')
                    desc = item.get('说明', '')
                    draw_line(f"- {label}：{value}")
                    if desc:
                        draw_line(f"  说明：{desc}")
            # 三、四、五...：维度统计图
            for ch in charts:
                if not ch or not ch.get('bytes'):
                    continue
                draw_line("")
                section_no += 1
                draw_line(f"{_section_no_to_cn(section_no)}、{ch.get('title') or '维度统计'}")
                img = ImageReader(io.BytesIO(ch['bytes']))
                img_width, img_height = img.getSize()
                max_width = width - 80
                max_height = 240
                scale = min(max_width / img_width, max_height / img_height)
                w = img_width * scale
                h = img_height * scale
                if y - h < 40:
                    c.showPage()
                    y = height - 40
                    if font_name:
                        c.setFont(font_name, 11)
                    else:
                        c.setFont("Helvetica", 11)
                c.drawImage(img, 40, y - h, width=w, height=h)
                y -= h + 20

            if case_dicts:
                draw_line("")
                section_no += 1
                title_text = f"{_section_no_to_cn(section_no)}、部分病例明细（前 50 条）"
                draw_line(title_text)
                for row in case_dicts[:50]:
                    line = f"病例ID={row.get('id')}, 疾病={row.get('type')}, 性别={row.get('gender')}, 年龄={row.get('age')}, 医院={row.get('docHospital')}, 科室={row.get('department')}"
                    draw_line(line)

            c.save()
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name='report_export.pdf',
                mimetype='application/pdf'
            )

        # 默认导出为 Excel：包含“摘要”和“病例明细”两个工作表
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            summary_df.to_excel(writer, index=False, sheet_name='summary')
            cases_df.to_excel(writer, index=False, sheet_name='cases')
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='report_export.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print("导出报告失败：", e)
        return jsonify({'message': 'error', 'code': 500, 'data': {'error': str(e)}}), 500


# ================= DeepSeek 智能诊断（demo 实现） =================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

deepseek_client = None
if DEEPSEEK_API_KEY:
    try:
        deepseek_client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    except Exception as e:
        print("初始化 DeepSeek 客户端失败：", e)
        deepseek_client = None


def _build_llm_summary(title, kpi, filters):
    """生成一段智能诊断说明，供 /ai/report 接口与导出报告复用。"""
    kpi_text = "\n".join(
        [f"- {item.get('label')}: {item.get('value')}" for item in (kpi or [])]
    )
    prompt = (
        f"你是一名医疗数据分析师，请根据以下指标与筛选条件，用中文生成一段不超过 200 字的诊断与趋势说明，"
        f"要求专业、客观，避免给出具体用药建议。\n\n"
        f"报告标题：{title}\n\n"
        f"关键指标：\n{kpi_text}\n\n"
        f"筛选条件（JSON）：{filters}\n"
    )

    if not DEEPSEEK_API_KEY or deepseek_client is None:
        return "【Demo】当前未配置 DeepSeek API Key，这里返回的是示例说明：病例总量和高发疾病类型可为管理者提供决策参考，详细分析请在正式环境中查看。"

    try:
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是一名严谨的医疗数据分析专家。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        if response and response.choices:
            return response.choices[0].message.content.strip()
        return "【Fallback】智能诊断结果为空，请稍后重试。"
    except Exception as e:
        print("DeepSeek 调用失败：", e)
        return "【Fallback】智能诊断生成失败，请稍后重试或检查 DeepSeek 配置。"


@app.route('/ai/report', methods=['POST'])
def ai_report():
    """调用 DeepSeek 生成简要诊断说明，给前端预览使用。"""
    data = request.get_json(force=True) or {}
    title = data.get("title") or "医疗数据分析报告"
    kpi = data.get("kpi") or []
    filters = data.get("filters") or {}

    summary = _build_llm_summary(title, kpi, filters)

    return jsonify({
        "message": "success",
        "code": 200,
        "data": {
            "summary": summary
        }
    })


if __name__ == '__main__':
    app.run()
