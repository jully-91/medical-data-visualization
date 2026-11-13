"""
Medical Disease Prediction & Similarity Search Engine
基于 BERT 的医疗病情预测与相似病例检索系统

此模块实现了基于 bert-base-chinese 的深度学习分类模型，
并利用语义向量空间模型（Vector Space Model）实现相似病例推荐。

Author: oddish
Date: 2025-12-08
Version: 2.0.0
"""

# 中文 Windows 控制台默认使用 GBK 编码，本模块日志中的 emoji（✅ / ❌）会触发
# UnicodeEncodeError，导致模型加载中断甚至服务崩溃。这里强制输出流使用 UTF-8。
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from utils.db_config import get_sqlalchemy_url

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics.pairwise import cosine_similarity
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertModel, get_linear_schedule_with_warmup

# ================= 配置区域 (Configuration) =================
# 获取当前脚本所在的文件夹路径，确保路径在不同环境下的一致性
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 定义模型与资源的绝对路径
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, 'bert-base-chinese')
MODEL_SAVE_PATH = os.path.join(BASE_DIR, 'medical_model.pth')
CLASSES_SAVE_PATH = os.path.join(BASE_DIR, 'classes.npy')

# 自动检测环境：优先使用本地离线模型，若不存在则尝试使用国内镜像在线下载
if os.path.exists(LOCAL_MODEL_PATH) and os.path.exists(os.path.join(LOCAL_MODEL_PATH, 'config.json')):
    MODEL_NAME = LOCAL_MODEL_PATH
    os.environ["HF_HUB_OFFLINE"] = "1"  # 强制离线模式，防止联网报错
else:
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # 设置 HuggingFace 国内镜像
    MODEL_NAME = 'bert-base-chinese'

# 数据库连接配置（统一从 .env 读取，避免在代码中硬编码密码）
DB_URL = get_sqlalchemy_url()

# === 超参数设置 (Hyperparameters) ===
# 经测试，以下参数在小样本医疗文本上表现最佳
MAX_LEN = 128  # 文本最大截断长度
BATCH_SIZE = 8  # 批次大小 (较小的 Batch Size 有助于泛化)
EPOCHS = 10  # 训练轮数 (充分微调)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ==========================================================


class MedicalDataset(Dataset):
    """
    自定义 PyTorch 数据集类，用于处理医疗文本数据。
    负责将文本转换为 BERT 模型所需的 Input IDs 和 Attention Mask。
    """

    def __init__(self, texts, labels, tokenizer, max_len):
        """
        Args:
            texts (array-like): 原始症状描述文本列表
            labels (array-like): 对应的疾病标签索引
            tokenizer: BERT 分词器实例
            max_len (int): 文本最大长度
        """
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        """
        获取单条数据，并进行 Tokenization 编码
        """
        text_str = str(self.texts[item])
        # 使用 BERT 分词器进行编码，自动添加 [CLS] 和 [SEP] 标记
        encoding = self.tokenizer.encode_plus(
            text_str,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'text': text_str,
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'targets': torch.tensor(self.labels[item], dtype=torch.long)
        }


class DiseaseClassifier(nn.Module):
    """
    基于 BERT 的疾病分类模型架构。
    结构: BERT Encoder -> Dropout -> Linear Layer (Classifier)
    """

    def __init__(self, n_classes):
        super(DiseaseClassifier, self).__init__()
        # 加载预训练的 BERT 模型
        self.bert = BertModel.from_pretrained(MODEL_NAME)

        # Dropout 层，用于防止过拟合
        self.drop = nn.Dropout(p=0.3)

        # 全连接层，将 BERT 的隐藏层维度 (768) 映射到疾病类别数
        self.out = nn.Linear(self.bert.config.hidden_size, n_classes)

    def forward(self, input_ids, attention_mask):
        """
        前向传播逻辑
        Returns:
            logits: 用于分类的原始分数
            pooled_output: 用于相似度计算的句向量 ([CLS] token 的表示)
        """
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)

        # pooled_output 代表整个句子的语义向量
        pooled_output = outputs.pooler_output

        output = self.drop(pooled_output)
        logits = self.out(output)

        # 同时返回 logits (用于预测) 和 pooled_output (用于相似病例推荐)
        return logits, pooled_output


class MedicalAI:
    """
    医疗 AI 引擎核心类 (Facade Pattern)。
    封装了数据加载、模型训练、模型保存/加载、推理预测及相似度检索的所有逻辑。
    """

    def __init__(self):
        print("正在初始化 AI 引擎...")
        try:
            self.tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
        except Exception as e:
            print(f"❌ 分词器加载失败: {e}")
            raise e

        self.label_encoder = LabelEncoder()
        self.model = None
        self.engine = create_engine(DB_URL)

        # 内存缓存，用于存储向量库，实现快速检索
        self.case_database = []
        self.case_vectors = None

    def load_data(self):
        """从 MySQL 数据库加载病例数据"""
        try:
            query = text('select * from cases')
            df = pd.read_sql(query, con=self.engine)
            # 数据清洗：填充缺失值
            df['content'] = df['content'].fillna('')
            df['type'] = df['type'].fillna('未知')
            return df
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            raise e

    def train(self):
        """
        执行完整的模型训练流程 (Fine-tuning)。
        流程: 加载数据 -> 编码 -> 训练 -> 保存模型 -> 构建向量库
        """
        print(f"=== 开始高精度训练 (Device: {DEVICE}) ===")
        print(f"配置: Epochs={EPOCHS}, Batch={BATCH_SIZE}, MaxLen={MAX_LEN}")

        df = self.load_data()

        # 打印数据分布，辅助分析样本不平衡问题
        print("--- 数据库样本分布 ---")
        print(df['type'].value_counts())
        print("----------------------")

        # 标签编码 (String -> Int)
        df['label_id'] = self.label_encoder.fit_transform(df['type'])
        num_classes = len(self.label_encoder.classes_)
        print(f"识别到的疾病类别 ({num_classes}种): {self.label_encoder.classes_}")

        # 【重要】保存类别名称，确保预测时的标签映射一致性
        np.save(CLASSES_SAVE_PATH, self.label_encoder.classes_)

        # 划分训练集和验证集
        df_train, df_test = train_test_split(df, test_size=0.1, random_state=42)

        train_dataset = MedicalDataset(
            texts=df_train.content.to_numpy(),
            labels=df_train.label_id.to_numpy(),
            tokenizer=self.tokenizer,
            max_len=MAX_LEN
        )
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)

        self.model = DiseaseClassifier(num_classes).to(DEVICE)

        # 使用 AdamW 优化器，学习率设为 2e-5 (BERT 微调的标准参数)
        optimizer = optim.AdamW(self.model.parameters(), lr=2e-5)
        loss_fn = nn.CrossEntropyLoss().to(DEVICE)

        # === 训练循环 ===
        self.model.train()
        total_steps = len(train_loader) * EPOCHS
        scheduler = get_linear_schedule_with_warmup(optimizer, 0, total_steps)

        for epoch in range(EPOCHS):
            print(f'\nEpoch {epoch + 1}/{EPOCHS} 开始...')
            total_loss = 0
            for i, d in enumerate(train_loader):
                input_ids = d["input_ids"].to(DEVICE)
                attention_mask = d["attention_mask"].to(DEVICE)
                targets = d["targets"].to(DEVICE)

                outputs, _ = self.model(input_ids, attention_mask)
                loss = loss_fn(outputs, targets)

                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)  # 梯度裁剪
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

                total_loss += loss.item()

                if i % 10 == 0:
                    print(f" -> Step {i}, Loss: {loss.item():.4f}")

            avg_loss = total_loss / len(train_loader)
            print(f"Epoch {epoch + 1} 结束，平均 Loss: {avg_loss:.4f}")

        print("✅ 训练完成，正在保存模型...")
        # 保存模型权重字典
        torch.save(self.model.state_dict(), MODEL_SAVE_PATH)
        print(f"模型已保存至: {MODEL_SAVE_PATH}")

        # 训练完成后，立即重建向量库
        self.update_vector_database(df)

    def load_model(self):
        """
        加载已训练的模型权重和配置。
        此方法用于 Web 服务启动时，避免每次重启都需要重新训练。
        """
        if not os.path.exists(MODEL_SAVE_PATH) or not os.path.exists(CLASSES_SAVE_PATH):
            raise FileNotFoundError("找不到模型文件，请先运行 tree.py 进行训练！")

        print(f"正在加载本地模型: {MODEL_SAVE_PATH} ...")

        # 1. 恢复标签编码器
        self.label_encoder.classes_ = np.load(CLASSES_SAVE_PATH, allow_pickle=True)
        num_classes = len(self.label_encoder.classes_)

        # 2. 初始化模型架构
        self.model = DiseaseClassifier(num_classes).to(DEVICE)

        # 3. 加载权重参数
        self.model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=DEVICE))
        self.model.eval()  # 切换到评估模式
        print("✅ 模型权重加载成功！")

        print("正在重建向量库...")
        df = self.load_data()
        self.update_vector_database(df)

    def update_vector_database(self, df):
        """
        构建相似病例向量库。
        原理: 将所有历史病例输入 BERT，获取其 [CLS] 语义向量并缓存。
        """
        self.model.eval()
        vectors = []
        records = []

        print("正在计算历史病例特征向量...")
        with torch.no_grad():
            for _, row in df.iterrows():
                # 编码文本
                encoded = self.tokenizer.encode_plus(
                    str(row['content']),
                    max_length=MAX_LEN,
                    padding='max_length',
                    truncation=True,
                    return_tensors='pt'
                )
                input_ids = encoded['input_ids'].to(DEVICE)
                mask = encoded['attention_mask'].to(DEVICE)

                # 获取语义向量 (pooled_output)
                _, pooled = self.model(input_ids, mask)

                # 归一化向量 (L2 Norm)，便于后续计算余弦相似度
                vec = pooled.cpu().numpy()[0]
                norm_vec = vec / (np.linalg.norm(vec) + 1e-9)
                vectors.append(norm_vec)

                # 缓存该向量对应的原始数据
                records.append({
                    'id': row.get('id', 0),
                    'disease': row['type'],
                    'gender': row.get('gender', '-'),
                    'age': row.get('age', '-'),
                    'visitTime': str(row.get('time', '-')),
                    'symptoms': str(row['content'])[:60] + '...'  # 仅存储摘要
                })

        self.case_database = records
        self.case_vectors = np.array(vectors) if vectors else None
        print(f"✅ 向量库构建完成，共 {len(records)} 条病例")

    def predict(self, text_content):
        """
        对外预测接口。
        Args:
            text_content: 用户输入的症状描述
        Returns:
            dict: 包含预测疾病、置信度、建议以及相似病例列表
        """
        if not self.model:
            raise Exception("❌ 模型尚未加载")

        # === 防线 1: 简单规则过滤 ===
        # 如果输入太短（比如少于 2 个字），或者是纯标点，直接拒识
        if len(text_content.strip()) < 2:
            return {
                'prediction': {
                    'disease': "无法判断",
                    'confidence': 0.0,
                    'advice': "您输入的描述太短，AI 无法提取有效特征。请尝试输入更详细的症状（例如：头痛伴随恶心，持续了两天）。"
                },
                'similar_cases': []
            }

        self.model.eval()
        encoded = self.tokenizer.encode_plus(
            text_content, max_length=MAX_LEN, padding='max_length',
            truncation=True, return_tensors='pt'
        )
        input_ids = encoded['input_ids'].to(DEVICE)
        mask = encoded['attention_mask'].to(DEVICE)

        with torch.no_grad():
            logits, pooled = self.model(input_ids, mask)

            # --- 任务1: 疾病分类 ---
            probs = torch.nn.functional.softmax(logits, dim=1)
            conf, pred_idx = torch.max(probs, dim=1)

            # 获取具体的置信度数值 (float)
            confidence_val = float(conf.cpu().numpy()[0])

            # === 防线 2: 置信度阈值截断 (Confidence Threshold) ===
            # 设定一个“及格线”，通常设为 0.4 或 0.5。
            # 如果最高概率都低于这个线，说明模型在瞎猜。
            THRESHOLD = 0.45

            if confidence_val < THRESHOLD:
                disease = "特征不明显 / 未知"
                # 虽然被拒识，但置信度还是要传回去，让用户知道“AI只有20%的把握”
                # 或者你也可以强制设为 0，看前端展示需求
                advice = "根据当前的描述，AI 难以做出可信的判断（置信度过低）。建议您补充更多细节，如发病诱因、疼痛性质、持续时间等。"
            else:
                # 只有“及格”了，才把预测的病名放出来
                disease = self.label_encoder.inverse_transform(pred_idx.cpu().numpy())[0]
                advice = f"AI分析认为最可能的诊断是【{disease}】，建议完善相关检查。"

            # --- 任务2: 相似病例推荐 ---
            similar_cases = []
            if self.case_vectors is not None and len(self.case_vectors) > 0:
                q_vec = pooled.cpu().numpy()[0]
                q_vec = q_vec / (np.linalg.norm(q_vec) + 1e-9)

                sims = cosine_similarity([q_vec], self.case_vectors)[0]
                top_idxs = sims.argsort()[-4:][::-1]
                for idx in top_idxs:
                    # 阈值过滤: 相似度太低的不推荐
                    if sims[idx] > 0.05:
                        similar_cases.append({
                            **self.case_database[idx],
                            'similarity': float(sims[idx])
                        })
                    if len(similar_cases) >= 3: break

        return {
            'prediction': {
                'disease': disease,
                'confidence': confidence_val,  # 返回原始置信度
                'advice': advice
            },
            'similar_cases': similar_cases
        }


if __name__ == '__main__':
    # 模块入口：直接运行时执行训练流程
    ai = MedicalAI()
    ai.train()