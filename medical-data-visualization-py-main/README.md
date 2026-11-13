# 医疗疾病数据分析大屏可视化系统

> 📖 **环境配置、启动步骤、常见问题排查**详见 **[docs/运行手册.md](docs/运行手册.md)**

## 项目简介

本项目是一个基于Python和Vue.js的医疗疾病数据分析可视化系统，集成了数据分析、机器学习预测、报告生成和AI智能对话等功能。系统采用深蓝色科技风格UI设计，提供直观的数据可视化展示和智能的医疗咨询服务。

## 核心功能

### 1. 数据可视化大屏
- 实时展示医疗数据统计信息
- 疾病分布地图可视化
- 多维度数据图表展示（饼图、柱状图、折线图等）
- 动态数据更新和交互

### 2. 疾病预测分析
- 基于机器学习的疾病预测模型
- 支持多种算法（随机森林、SVM、神经网络等）
- 预测结果可视化展示
- 模型性能评估指标

### 3. 数据管理
- 医疗数据表格展示
- 数据筛选和排序功能
- 数据导入导出
- 数据统计分析

### 4. 报告生成
- 自动生成数据分析报告
- 支持多种报告格式
- 可定制报告模板
- 报告下载和打印

### 5. AI医疗助手
- **多对话管理**：支持创建、切换、重命名、删除多个对话
- **智能问答**：基于DeepSeek大模型的医疗咨询服务
- **快速咨询**：提供常见医疗问题快速入口
- **Markdown支持**：AI回复支持富文本格式显示
- **数据持久化**：对话历史自动保存，支持30天内查看

## 技术栈

### 后端技术
- **Python 3.8+**
- **Flask**: Web框架
- **Flask-SocketIO**: WebSocket通信
- **SQLAlchemy**: ORM数据库操作
- **Pandas**: 数据处理和分析
- **Scikit-learn**: 机器学习算法
- **OpenAI SDK**: 集成DeepSeek API
- **NumPy**: 数值计算

### 前端技术
- **Vue.js 2.x**: 前端框架
- **Vue Router**: 路由管理
- **Element UI**: UI组件库
- **ECharts**: 数据可视化图表
- **Socket.IO Client**: WebSocket客户端
- **Marked**: Markdown解析
- **Axios**: HTTP请求

### 数据库
- **MySQL 5.7+ / 8.0+**：作为病例数据和爬虫数据的主存储（`medicalinfo` 数据库）
- **SQLite (`data/data.db`)**：历史示例 / 轻量级测试（可选，不再作为主数据源）

## 项目结构

```
基于python医疗疾病数据分析大屏可视化系统/
│
├── app.py                       # Flask 主应用入口（REST API、数据管理、报告生成等）
├── websocket_chat.py            # WebSocket 服务（AI 医疗助手，对接 DeepSeek）
├── requirements.txt             # Python 依赖包
├── .env                         # 环境配置文件（DeepSeek & 数据库等）
├── medicalinfo.sql              # MySQL 初始化脚本（病例数据表结构和示例数据）
├── start_ai_chat.bat           # Windows 启动脚本（可选）
│
├── spiders/                     # 爬虫与定时任务模块
│   ├── spiderMain.py            # 爬虫主程序（按疾病爬取病例）
│   ├── spiderDetail.py          # 详情页解析
│   ├── data_sync_manager.py     # CSV -> MySQL 数据同步
│   ├── model_trainer.py         # 定时训练 / 评估模型
│   ├── start_scheduler.py       # 定时任务统一入口（APScheduler）
│   └── ...
│
├── utils/                       # 工具模块
│   ├── __init__.py
│   ├── db_config.py             # 统一数据库配置（从 .env 读取 DB_*）
│   ├── query.py                 # 通用 MySQL 查询封装
│   └── ...
│
├── machine/                     # 机器学习 / AI 模块
│   ├── __init__.py
│   ├── tree.py                  # BERT 模型与相似病例检索（MedicalAI）
│   └── ...
│
└── front-end-template-1-master/  # Vue前端项目
    ├── package.json              # 前端依赖配置
    ├── vue.config.js            # Vue配置
    │
    ├── public/                  # 静态资源
    │   └── index.html
    │
    └── src/                     # 源代码
        ├── main.js              # 入口文件
        ├── App.vue              # 根组件
        │
        ├── router/              # 路由配置
        │   └── index.js
        │
        ├── views/               # 页面组件
        │   ├── Index.vue        # 首页大屏
        │   ├── Pred.vue         # 疾病预测
        │   ├── TableData.vue    # 数据管理
        │   ├── Report.vue       # 报告生成
        │   └── AiChat.vue       # AI医疗助手
        │
        ├── components/          # 公共组件
        │   ├── Header.vue       # 导航栏
        │   └── ...
        │
        └── assets/              # 静态资源
            ├── css/
            ├── images/
            └── ...
```

## 模型权重获取（首次运行必做）

`machine/medical_model.pth`（390.22 MB）与 `machine/bert-base-chinese/pytorch_model.bin`（392.51 MB）
体积较大，**未纳入 git 仓库**（避免占用 LFS 配额、拖慢克隆），从
[v1.0-weights Release](https://github.com/jully-91/medical-data-visualization/releases/tag/v1.0-weights) 下载。

### 方式一：一键下载脚本（推荐）

在项目根目录（与 `app.py` 同级）执行：

```bash
python download_weights.py
```

脚本会自动下载两个权重、放到正确目录，并校验文件大小。

### 方式二：手动下载

| 文件 | 下载地址 | 放置路径 |
|---|---|---|
| `medical_model.pth` | [点击下载](https://github.com/jully-91/medical-data-visualization/releases/download/v1.0-weights/medical_model.pth) | `machine/medical_model.pth` |
| `pytorch_model.bin` | [点击下载](https://github.com/jully-91/medical-data-visualization/releases/download/v1.0-weights/pytorch_model.bin) | `machine/bert-base-chinese/pytorch_model.bin` |

也可用命令行下载（Windows PowerShell）：

```powershell
curl.exe -L -o machine/medical_model.pth "https://github.com/jully-91/medical-data-visualization/releases/download/v1.0-weights/medical_model.pth"
curl.exe -L -o machine/bert-base-chinese/pytorch_model.bin "https://github.com/jully-91/medical-data-visualization/releases/download/v1.0-weights/pytorch_model.bin"
```

校验文件大小：

| 文件 | 期望字节数 |
|---|---|
| `medical_model.pth` | 409,170,336 |
| `pytorch_model.bin` | 411,577,189 |

> **未放置权重时**：大屏可视化、数据管理、报告生成等功能均可正常使用，
> 仅「数据预测」页面会提示「模型尚未加载」。

### 方式三：自行重新训练

若无法下载，也可基于数据库中的病例数据重新训练（需先完成下方数据库初始化）：

```bash
python -m machine.tree
```

默认 10 个 epoch，28 核 CPU 约 9 分钟。脚本会自动生成
`machine/medical_model.pth` 与 `machine/classes.npy`。

## 安装部署

### 环境要求

#### Python版本
- **最低要求**：Python 3.8
- **推荐版本**：Python 3.8 - 3.10
- **测试版本**：Python 3.8.10, 3.9.13, 3.10.11

**版本说明**：
- Python 3.7及以下：不支持（Flask 2.3、NumPy 1.23、Pandas 1.4等核心依赖需要3.8+）
- Python 3.8-3.10：完全兼容，推荐使用
- Python 3.11+：可能存在部分依赖兼容性问题，需要调整依赖版本

#### Node.js版本
- **最低要求**：Node.js 14.x
- **推荐版本**：Node.js 16.x 或 18.x LTS
- npm 6.x 或更高版本（或使用 yarn）

### 1. 克隆项目
```bash
git clone [项目地址]
cd 基于python医疗疾病数据分析大屏可视化系统
```

### 2. 后端安装

#### 创建Python虚拟环境（推荐）
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 安装Python依赖
```bash
pip install -r requirements.txt
```

#### 配置环境变量
在项目根目录创建或编辑 `.env` 文件，至少配置以下内容（生产环境务必使用安全值）：
```env
# DeepSeek API 配置（请替换为你自己的密钥）
DEEPSEEK_API_KEY=your-deepseek-api-key-here

# Flask 配置
FLASK_SECRET_KEY=your-flask-secret-key-here

# 数据库配置（统一从这里读取，供 Flask / 爬虫 / AI 模块 共用）
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_NAME=medicalinfo
DB_CHARSET=utf8mb4
DB_PASSWORD=your-db-password-here
```

### 3. 前端安装

```bash
cd front-end-template-1-master
npm install
```

### 4. 启动项目

#### 4.1 准备数据库（第一次运行必须执行）

1. 确保本机已安装并启动 MySQL，记住主机、端口、用户名和密码。
2. 根据上一节修改 `.env` 中的 `DB_*` 配置，保证能够连接到目标 MySQL。
3. 在项目根目录导入数据库结构（任选一种方式）：

   **方式 A：使用脚本一键导入（推荐）**
   ```bash
   # 在项目根目录，已激活虚拟环境
   python -m spiders.import_database
   ```

   **方式 B：使用 MySQL 客户端导入 SQL 文件**
   ```bash
   # 登录 MySQL 后执行
   SOURCE /path/to/medicalinfo.sql;
   ```

#### 4.2 启动后端服务

打开两个终端（都在项目根目录，且虚拟环境已激活）：

```bash
# 终端 1：启动 WebSocket 服务（AI 医疗助手，对接 DeepSeek）
python websocket_chat.py

# 终端 2：启动 Flask 主服务（REST API + 数据管理 + 报告生成等）
python app.py
```

#### 4.3 启动前端服务

```bash
cd front-end-template-1-master
npm run serve
```

#### 4.4 （可选）启动定时任务 / 爬虫调度

如果希望定时自动爬取数据、同步 CSV 到数据库并周期性重训练模型，可以额外启动定时任务系统：

```bash
# 在项目根目录
python -m spiders.start_scheduler --action start
```

常用命令：
```bash
# 查看当前已注册的任务
python -m spiders.start_scheduler --action list

# 立即运行某个任务（例如：crawl_all_diseases）
python -m spiders.start_scheduler --action run --job crawl_all_diseases
```

#### 4.5 停止服务

| 启动方式 | 停止方法 |
|---|---|
| 双击 `start-*.bat` | 直接**关闭对应标题的窗口**（`Flask-5000` / `SocketIO-5001` / `Vue-8080`）；或在窗口内按 `Ctrl+C`，出现“终止批处理操作吗(Y/N)?”时按 `Y` |
| 手动开终端 | 在对应终端按 `Ctrl+C` |

窗口找不到了、端口被占用、或进程卡死时，**按端口强制结束**：

```powershell
5000,5001,8080 | ForEach-Object {
    Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
}
```

确认是否已全部停止（**无输出**即表示三个端口都已释放）：

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 5000,5001,8080 }
```

> 💡 `websocket_chat.py` 使用 Flask debug 模式（reloader），实际是**三层进程**
> （终端 → venv 启动器 → 真实 python）。按端口杀往往只命中一层，残留进程会立刻重新占端口。
> 若复查发现端口仍被占用，用命令定向清理：
>
> ```powershell
> Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
>     Where-Object { $_.CommandLine -match 'websocket_chat|app\.py' } |
>     ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
> ```

> ⚠️ 不建议随手执行 `Get-Process -Name python,node | Stop-Process -Force`，
> 会连**其他项目**的 Python / Node 进程一起杀掉。

### 5. 访问系统
- 前端地址：http://localhost:8080
- Flask API：http://localhost:5000
- WebSocket：http://localhost:5001

## 使用说明

### 系统导航
1. **首页** - 数据可视化大屏，展示关键医疗数据指标
2. **数据预测** - 使用机器学习模型进行疾病预测分析
3. **数据管理** - 查看和管理医疗数据记录
4. **报告生成** - 生成数据分析报告
5. **AI医疗助手** - 智能医疗咨询对话

### AI医疗助手使用指南

#### 基本操作
- **新建对话**：点击左侧"新建对话"按钮开始新的咨询
- **切换对话**：点击左侧对话列表切换历史对话
- **发送消息**：输入问题后按Enter发送，Shift+Enter换行
- **快速提问**：点击快速问题卡片直接开始对话

#### 对话管理
- **重命名**：鼠标悬停在对话上，点击编辑图标修改标题
- **删除**：点击删除图标移除不需要的对话
- **自动保存**：所有对话自动保存30天

#### 支持的咨询类型
- 症状分析和初步诊断建议
- 用药指导和注意事项
- 体检报告解读
- 疾病预防和健康管理
- 医疗常识科普

## 配置说明

### 数据库配置
当前项目 **默认使用 MySQL 数据库 `medicalinfo`** 作为病例与爬虫数据的主存储，所有 Python 代码通过 `utils/db_config.py` 统一读取 `.env` 中的 `DB_*` 配置。

推荐流程：

1. 在 MySQL 中创建 `medicalinfo` 数据库，并通过 `medicalinfo.sql` 或 `python -m spiders.import_database` 导入表结构与基础数据。
2. 在 `.env` 中正确配置 `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME/DB_CHARSET`。
3. 确保 MySQL 服务启动后，再运行 `python app.py`、爬虫脚本或 AI 模型训练脚本。

### AI模型配置
1. 注册DeepSeek账号获取API Key
2. 在 `.env` 文件中配置 `DEEPSEEK_API_KEY`
3. 可在 `websocket_chat.py` 中调整模型参数

### 端口配置
- Flask主服务：5000（app.py）
- WebSocket服务：5001（websocket_chat.py）
- Vue前端：8080（vue.config.js）

## 常见问题

### Q1: AI助手连接失败？
- 检查WebSocket服务是否正常启动（端口5001）
- 确认DeepSeek API Key配置正确
- 检查网络连接是否正常

### Q2: 依赖安装失败？

#### Python依赖安装问题

**1. 版本要求**
- **必须**：Python >= 3.8（推荐3.8-3.10）
- 检查版本：`python --version` 或 `python3 --version`
- 如版本过低，请从 [Python官网](https://www.python.org/) 下载合适版本
- **注意**：Python 3.11+ 可能需要调整部分依赖版本

**2. 使用国内镜像源**
```bash
# 清华大学镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 阿里云镜像源
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 豆瓣镜像源
pip install -r requirements.txt -i https://pypi.douban.com/simple/
```

**3. 常见依赖问题解决**
```bash
# httpx版本冲突（OpenAI SDK相关）
pip install httpx==0.24.1 anyio==3.7.1 httpcore==0.17.3 --force-reinstall

# Flask-SocketIO安装失败
pip install python-socketio==5.9.0 python-engineio==4.7.1 eventlet==0.33.3

# 机器学习库安装失败（scikit-learn）
pip install numpy scipy scikit-learn --upgrade
```

**4. Windows特定问题**
- 如遇到编译错误，安装Visual C++ Build Tools
- 某些包可能需要管理员权限：以管理员身份运行CMD
- 使用Anaconda环境可避免大部分依赖问题

#### Node.js依赖安装问题

**1. 版本要求**
- Node.js >= 14.x
- npm >= 6.x
- 检查版本：`node -v` 和 `npm -v`

**2. 使用国内镜像**
```bash
# 临时使用
npm install --registry https://registry.npmmirror.com

# 永久设置（推荐）
npm config set registry https://registry.npmmirror.com
npm install

# 使用cnpm（需先安装）
npm install -g cnpm --registry=https://registry.npmmirror.com
cnpm install
```

**3. 常见前端依赖问题**
```bash
# 清理缓存
npm cache clean --force

# 删除node_modules后重装
rm -rf node_modules package-lock.json
npm install

# 特定包版本问题
npm install marked@4.3.0 --save
npm install socket.io-client@4.5.4 --save
```

**4. 权限和网络问题**
- Linux/Mac：使用 `sudo npm install` 解决权限问题
- 代理环境：配置npm代理 `npm config set proxy http://proxy.example.com:8080`
- 防火墙：临时关闭防火墙或添加npm到白名单

### Q3: 数据可视化不显示？
- 检查后端API服务是否正常（端口5000）
- 查看浏览器控制台是否有错误信息
- 确认数据库中有数据

### Q4: 聊天记录丢失？
- 聊天记录保存在浏览器localStorage中
- 清除浏览器数据会导致记录丢失
- 系统自动保留30天内的对话

## 开发说明

### 添加新功能
1. 后端API：在 `app.py` 中添加新路由
2. 前端页面：在 `src/views/` 下创建Vue组件
3. 路由配置：在 `src/router/index.js` 中添加路由

### 数据格式
- API响应格式：JSON
- 时间格式：ISO 8601
- 编码：UTF-8

### 代码规范
- Python: PEP 8
- JavaScript: ESLint
- Vue: Vue Style Guide

## 注意事项

1. **数据安全**：生产环境部署时请更换所有默认密钥
2. **API限制**：DeepSeek API有调用频率限制，请合理使用
3. **浏览器兼容**：建议使用Chrome、Firefox、Edge等现代浏览器
4. **数据备份**：定期备份数据库和重要配置文件

## 许可证

本项目仅供学习和研究使用，不得用于商业目的。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issues
- 邮箱：[联系邮箱]

## 更新日志

### v1.0.0 (2024-12)
- ✅ 基础功能实现
- ✅ 数据可视化大屏
- ✅ 机器学习预测模块
- ✅ AI医疗助手集成
- ✅ 多对话管理功能
- ✅ Markdown渲染支持
- ✅ 响应式设计优化

---

**声明**：本系统提供的医疗建议仅供参考，不能替代专业医生的诊断和治疗。如有健康问题，请及时就医。
