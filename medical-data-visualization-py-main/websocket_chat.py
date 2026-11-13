# -*- coding: utf-8 -*-
# 中文 Windows 控制台默认使用 GBK 编码，日志中的 emoji 会触发 UnicodeEncodeError。
# 强制标准输出/错误流使用 UTF-8，避免服务因打印日志而崩溃。
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import os
from flask import Flask, request
from flask_socketio import SocketIO, emit, send
from flask_cors import CORS
from openai import OpenAI
from datetime import datetime
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化Flask应用和SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'your-deepseek-api-key-here')
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 初始化DeepSeek客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# 系统提示词
SYSTEM_PROMPT = """你是一位专业的AI医疗助手，专门为用户提供医疗健康相关的咨询和建议。
你的职责是：
1. 提供准确、专业的医疗健康信息
2. 解答用户关于疾病、症状、治疗方法的问题
3. 给出健康生活方式的建议
4. 解读基本的医疗检查报告
5. 提供用药指导和注意事项

请注意：
- 你的建议仅供参考，不能替代专业医生的诊断
- 对于紧急或严重的健康问题，建议用户及时就医
- 回答要专业、准确、易懂
- 保持友好、耐心的态度"""

# 存储会话历史
sessions = {}

@socketio.on('connect', namespace='/ws/chat')
def handle_connect():
    """处理WebSocket连接"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to AI Medical Assistant'})

@socketio.on('disconnect', namespace='/ws/chat')
def handle_disconnect():
    """处理WebSocket断开连接"""
    logger.info(f"Client disconnected: {request.sid}")
    # 清理会话数据
    if request.sid in sessions:
        del sessions[request.sid]

@socketio.on('message', namespace='/ws/chat')
def handle_message(data):
    """处理客户端发送的消息"""
    try:
        logger.info(f"Received message from {request.sid}: {data}")
        
        # 解析消息
        message_data = json.loads(data) if isinstance(data, str) else data
        user_message = message_data.get('content', '')
        
        if not user_message:
            emit('response', {
                'type': 'error',
                'message': '消息内容不能为空'
            })
            return
        
        # 获取或创建会话历史
        session_id = request.sid
        if session_id not in sessions:
            sessions[session_id] = {
                'messages': [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ],
                'created_at': datetime.now()
            }
        
        # 添加用户消息到会话历史
        sessions[session_id]['messages'].append({
            "role": "user",
            "content": user_message
        })
        
        # 调用DeepSeek API
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=sessions[session_id]['messages'],
                temperature=0.7,
                max_tokens=1000,
                stream=False
            )
            
            # 获取AI响应
            ai_response = response.choices[0].message.content
            
            # 添加AI响应到会话历史
            sessions[session_id]['messages'].append({
                "role": "assistant",
                "content": ai_response
            })
            
            # 限制会话历史长度（保留最近20条消息）
            if len(sessions[session_id]['messages']) > 21:  # 1个系统消息 + 20条对话
                sessions[session_id]['messages'] = [
                    sessions[session_id]['messages'][0]  # 保留系统消息
                ] + sessions[session_id]['messages'][-20:]  # 保留最近20条
            
            # 发送响应给客户端
            emit('response', {
                'type': 'response',
                'content': ai_response,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as api_error:
            logger.error(f"DeepSeek API error: {str(api_error)}")
            emit('response', {
                'type': 'error',
                'message': f'AI服务暂时不可用，请稍后重试。错误：{str(api_error)}'
            })
            
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        emit('response', {
            'type': 'error',
            'message': '处理消息时发生错误，请重试'
        })

@socketio.on('clear_history', namespace='/ws/chat')
def handle_clear_history():
    """清除会话历史"""
    session_id = request.sid
    if session_id in sessions:
        sessions[session_id] = {
            'messages': [
                {"role": "system", "content": SYSTEM_PROMPT}
            ],
            'created_at': datetime.now()
        }
    emit('response', {
        'type': 'info',
        'message': '会话历史已清除'
    })

if __name__ == '__main__':
    # 启动WebSocket服务器
    print("Starting WebSocket server on port 5001...")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
