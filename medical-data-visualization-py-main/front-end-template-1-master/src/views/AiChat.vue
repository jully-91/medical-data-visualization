<template>
  <div class="ai-chat-modern">
    <!-- 左侧对话列表 -->
    <div class="sidebar-conversations" :class="{ hidden: !sidebarVisible }">
      <div class="sidebar-header">
        <h3>对话历史</h3>
        <button @click="createNewChat" class="new-chat-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 5v14M5 12h14" stroke-width="2" stroke-linecap="round"/>
          </svg>
          新建对话
        </button>
      </div>
      
      <div class="conversations-list">
        <div v-for="conv in conversations" 
             :key="conv.id"
             :class="['conversation-item', { active: currentConversationId === conv.id }]"
             @click="switchConversation(conv.id)">
          
          <div class="conv-info">
            <div v-if="editingId === conv.id" class="conv-edit">
              <input v-model="editingTitle" 
                     @keyup.enter="saveTitle(conv.id)"
                     @keyup.esc="cancelEdit"
                     @blur="saveTitle(conv.id)"
                     class="edit-input"
                     ref="editInput"/>
            </div>
            <div v-else class="conv-title">{{ conv.title }}</div>
            <div class="conv-time">{{ formatDate(conv.updatedAt) }}</div>
          </div>
          
          <div class="conv-actions">
            <button @click.stop="startEdit(conv)" class="action-btn" title="重命名">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" stroke-width="2"/>
                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke-width="2"/>
              </svg>
            </button>
            <button @click.stop="deleteConversation(conv.id)" class="action-btn delete" title="删除">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z" stroke-width="2"/>
              </svg>
            </button>
          </div>
        </div>
        
        <div v-if="conversations.length === 0" class="no-conversations">
          暂无对话记录
        </div>
      </div>
    </div>

    <!-- 主聊天区域 -->
    <div class="main-chat-area">
      <div class="chat-header">
        <button @click="toggleSidebar" class="sidebar-toggle">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M3 12h18M3 6h18M3 18h18" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
        <div class="header-info">
          <h2>{{ currentConversation ? currentConversation.title : 'AI医疗助手' }}</h2>
          <span class="header-subtitle">基于DeepSeek的智能医疗咨询服务</span>
        </div>
        <div class="header-actions">
          <span :class="['connection-status', wsConnected ? 'connected' : 'disconnected']">
            <span class="status-dot"></span>
            {{ wsConnected ? '已连接' : '未连接' }}
          </span>
        </div>
      </div>

      <div class="chat-content">
        <!-- 欢迎界面 -->
        <div v-if="!currentMessages.length" class="welcome-screen">
          <div class="welcome-icon">
            <img src="../assets/doctor-avatar.svg" alt="AI助手" @error="handleImageError">
          </div>
          <h3>您好，我是AI医疗助手</h3>
          <p>我可以为您提供医疗健康咨询、症状分析、用药指导等服务</p>
          
          <div class="quick-prompts">
            <h4>快速开始</h4>
            <div class="prompt-grid">
              <div class="prompt-card" @click="quickStart('最近感冒了，该如何治疗？')">
                <span class="prompt-icon">🤧</span>
                <span>感冒治疗</span>
              </div>
              <div class="prompt-card" @click="quickStart('高血压患者日常饮食注意事项')">
                <span class="prompt-icon">🩺</span>
                <span>高血压饮食</span>
              </div>
              <div class="prompt-card" @click="quickStart('如何看懂体检报告？')">
                <span class="prompt-icon">📋</span>
                <span>体检报告解读</span>
              </div>
              <div class="prompt-card" @click="quickStart('儿童发烧应急处理方法')">
                <span class="prompt-icon">👶</span>
                <span>儿童发烧</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-else class="messages-container" ref="messagesContainer">
          <div v-for="(message, index) in currentMessages" :key="index" class="message-wrapper">
            <div :class="['message-row', message.role]">
              <div class="message-avatar">
                <img v-if="message.role === 'assistant'" src="../assets/doctor-avatar.svg" alt="助手" @error="handleImageError">
                <div v-else class="user-icon">用</div>
              </div>
              <div class="message-body">
                <div class="message-header">
                  <span class="message-author">{{ message.role === 'assistant' ? 'AI医疗助手' : '您' }}</span>
                  <span class="message-time">{{ message.time }}</span>
                </div>
                <div class="message-content" v-html="formatMessage(message.content)"></div>
              </div>
            </div>
          </div>

          <!-- 加载中 -->
          <div v-if="isLoading" class="message-wrapper">
            <div class="message-row assistant">
              <div class="message-avatar">
                <img src="../assets/doctor-avatar.svg" alt="助手" @error="handleImageError">
              </div>
              <div class="message-body">
                <div class="message-header">
                  <span class="message-author">AI医疗助手</span>
                </div>
                <div class="typing-animation">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input-area">
        <div class="input-container">
          <textarea 
            v-model="inputMessage"
            @keydown.enter.prevent="handleEnterKey"
            placeholder="输入您的问题..."
            class="chat-input"
            :disabled="isLoading"
            rows="1"
            ref="chatInput"
          ></textarea>
          <button @click="sendMessage" 
                  :disabled="!inputMessage.trim() || isLoading" 
                  class="send-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M22 2L11 13M22 2L15 22L11 13L2 9L22 2Z" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
        <div class="input-tips">
          <span>Shift + Enter 换行 | Enter 发送</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import io from 'socket.io-client';
import { marked } from 'marked';

export default {
  name: 'AiChat',
  data() {
    return {
      conversations: [],
      currentConversationId: null,
      inputMessage: '',
      isLoading: false,
      socket: null,
      wsConnected: false,
      editingId: null,
      editingTitle: '',
      sidebarVisible: true
    }
  },
  
  computed: {
    currentConversation() {
      return this.conversations.find(c => c.id === this.currentConversationId);
    },
    currentMessages() {
      return this.currentConversation ? this.currentConversation.messages : [];
    }
  },
  
  mounted() {
    this.loadConversations();
    this.connectWebSocket();
    
    // 如果没有对话，创建一个新的
    if (this.conversations.length === 0) {
      this.createNewChat();
    }
  },
  
  beforeDestroy() {
    if (this.socket) {
      this.socket.disconnect();
    }
  },
  
  methods: {
    // 生成唯一ID
    generateId() {
      return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },
    
    // 创建新对话
    createNewChat() {
      const newConversation = {
        id: this.generateId(),
        title: '新对话',
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      this.conversations.unshift(newConversation);
      this.currentConversationId = newConversation.id;
      this.saveConversations();
      
      // 聚焦到输入框
      this.$nextTick(() => {
        if (this.$refs.chatInput) {
          this.$refs.chatInput.focus();
        }
      });
    },
    
    // 切换对话
    switchConversation(id) {
      this.currentConversationId = id;
      this.$nextTick(() => {
        this.scrollToBottom();
      });
    },
    
    // 删除对话
    deleteConversation(id) {
      if (confirm('确定要删除这个对话吗？')) {
        const index = this.conversations.findIndex(c => c.id === id);
        if (index > -1) {
          this.conversations.splice(index, 1);
          
          // 如果删除的是当前对话，切换到第一个对话或创建新对话
          if (this.currentConversationId === id) {
            if (this.conversations.length > 0) {
              this.currentConversationId = this.conversations[0].id;
            } else {
              this.createNewChat();
            }
          }
          
          this.saveConversations();
        }
      }
    },
    
    // 开始编辑标题
    startEdit(conversation) {
      this.editingId = conversation.id;
      this.editingTitle = conversation.title;
      this.$nextTick(() => {
        if (this.$refs.editInput) {
          this.$refs.editInput[0].focus();
          this.$refs.editInput[0].select();
        }
      });
    },
    
    // 保存标题
    saveTitle(id) {
      const conversation = this.conversations.find(c => c.id === id);
      if (conversation && this.editingTitle.trim()) {
        conversation.title = this.editingTitle.trim();
        conversation.updatedAt = new Date().toISOString();
        this.saveConversations();
      }
      this.cancelEdit();
    },
    
    // 取消编辑
    cancelEdit() {
      this.editingId = null;
      this.editingTitle = '';
    },
    
    // 切换侧边栏
    toggleSidebar() {
      this.sidebarVisible = !this.sidebarVisible;
    },
    
    // WebSocket连接
    connectWebSocket() {
      const socketUrl = `http://${window.location.hostname}:5001`;
      
      this.socket = io(socketUrl, {
        path: '/socket.io/',
        transports: ['websocket', 'polling']
      });
      
      this.socket = io(`${socketUrl}/ws/chat`);
      
      this.socket.on('connect', () => {
        console.log('Socket.IO连接已建立');
        this.wsConnected = true;
      });
      
      this.socket.on('response', (data) => {
        if (data.type === 'response') {
          this.isLoading = false;
          this.addMessage('assistant', data.content);
        } else if (data.type === 'error') {
          this.isLoading = false;
          this.$message?.error(data.message || '发生错误，请重试');
        }
      });
      
      this.socket.on('disconnect', () => {
        console.log('Socket.IO连接已断开');
        this.wsConnected = false;
      });
    },
    
    // 发送消息
    sendMessage() {
      if (!this.inputMessage.trim() || this.isLoading) return;
      
      if (!this.wsConnected) {
        if (this.$message) {
          this.$message.warning('连接未建立，请稍后重试');
        }
        return;
      }
      
      // 添加用户消息
      this.addMessage('user', this.inputMessage);
      
      // 发送到服务器
      this.socket.emit('message', JSON.stringify({
        type: 'message',
        content: this.inputMessage
      }));
      
      this.inputMessage = '';
      this.isLoading = true;
    },
    
    // 添加消息
    addMessage(role, content) {
      if (!this.currentConversation) return;
      
      const message = {
        role,
        content,
        time: this.getCurrentTime()
      };
      
      this.currentConversation.messages.push(message);
      this.currentConversation.updatedAt = new Date().toISOString();
      
      // 自动生成对话标题（第一条用户消息）
      if (role === 'user' && this.currentConversation.messages.length === 1) {
        this.currentConversation.title = content.substring(0, 30) + (content.length > 30 ? '...' : '');
      }
      
      this.saveConversations();
      this.$nextTick(() => {
        this.scrollToBottom();
      });
    },
    
    // 快速开始
    quickStart(prompt) {
      this.inputMessage = prompt;
      this.sendMessage();
    },
    
    // 处理回车键
    handleEnterKey(event) {
      if (!event.shiftKey) {
        this.sendMessage();
      } else {
        // Shift+Enter 换行
        const start = event.target.selectionStart;
        const end = event.target.selectionEnd;
        const value = event.target.value;
        this.inputMessage = value.substring(0, start) + '\n' + value.substring(end);
        this.$nextTick(() => {
          event.target.selectionStart = event.target.selectionEnd = start + 1;
        });
      }
    },
    
    // 格式化消息
    formatMessage(content) {
      try {
        marked.setOptions({
          breaks: true,
          gfm: true,
          headerIds: false,
          mangle: false
        });
        
        let html = marked.parse(content);
        html = html.replace(/<a /g, '<a target="_blank" ');
        return html;
      } catch (error) {
        console.error('Markdown解析失败:', error);
        return content.replace(/\n/g, '<br>');
      }
    },
    
    // 保存对话到localStorage
    saveConversations() {
      try {
        // 限制每个对话最多100条消息，最多保存20个对话
        const conversationsToSave = this.conversations.slice(0, 20).map(conv => ({
          ...conv,
          messages: conv.messages.slice(-100)
        }));
        
        localStorage.setItem('ai_chat_conversations', JSON.stringify(conversationsToSave));
        localStorage.setItem('ai_chat_current_id', this.currentConversationId);
      } catch (error) {
        console.error('保存对话失败:', error);
      }
    },
    
    // 加载对话
    loadConversations() {
      try {
        const saved = localStorage.getItem('ai_chat_conversations');
        const currentId = localStorage.getItem('ai_chat_current_id');
        
        if (saved) {
          this.conversations = JSON.parse(saved);
          
          // 清理超过30天的对话
          const thirtyDaysAgo = new Date();
          thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
          
          this.conversations = this.conversations.filter(conv => {
            return new Date(conv.updatedAt) > thirtyDaysAgo;
          });
          
          if (currentId && this.conversations.find(c => c.id === currentId)) {
            this.currentConversationId = currentId;
          } else if (this.conversations.length > 0) {
            this.currentConversationId = this.conversations[0].id;
          }
        }
      } catch (error) {
        console.error('加载对话失败:', error);
        this.conversations = [];
      }
    },
    
    // 工具方法
    getCurrentTime() {
      const now = new Date();
      return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    },
    
    formatDate(dateStr) {
      const date = new Date(dateStr);
      const now = new Date();
      const diff = now - date;
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      
      if (days === 0) {
        return '今天 ' + this.getCurrentTime();
      } else if (days === 1) {
        return '昨天';
      } else if (days < 7) {
        return `${days}天前`;
      } else {
        return `${date.getMonth() + 1}/${date.getDate()}`;
      }
    },
    
    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },
    
    handleImageError(event) {
      event.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iNDAiIGZpbGw9IiM2MzY3ZjEiLz4KPHBhdGggZD0iTTQwIDI1QzQ0Ljk3MDYgMjUgNDkgMjkuMDI5NCA0OSAzNEM0OSAzOC45NzA2IDQ0Ljk3MDYgNDMgNDAgNDNDMzUuMDI5NCA0MyAzMSAzOC45NzA2IDMxIDM0QzMxIDI5LjAyOTQgMzUuMDI5NCAyNSA0MCAyNVoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik0yNSA1NUMyNSA0OS40NzcyIDI5LjQ3NzIgNDUgMzUgNDVINDVDNTAuNTIyOCA0NSA1NSA0OS40NzcyIDU1IDU1VjYwSDI1VjU1WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+';
    }
  }
}
</script>

<style scoped>
@import './AiChatModern.css';
</style>
