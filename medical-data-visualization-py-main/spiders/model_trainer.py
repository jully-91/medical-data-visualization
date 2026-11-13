import logging
import os
import time
import json
import pickle
import pandas as pd
import numpy as np
import pymysql
import warnings
from datetime import datetime
from utils.db_config import get_db_config
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, precision_score, recall_score, f1_score
from sklearn.exceptions import NotFittedError, UndefinedMetricWarning
from imblearn.over_sampling import SMOTE

# 配置日志 - 详细输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('model_trainer')

# 数据库配置（统一从 utils.db_config / .env 读取）
DB_CONFIG = get_db_config()

# 模型相关配置
MODEL_CONFIG = {
    'model_save_dir': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models'),
    'min_data_samples': 100,  # 最小训练样本数
    'test_size': 0.2,  # 测试集比例
    'random_state': 42,  # 随机种子
    'retrain_threshold_days': 7,  # 自动重训练阈值天数
    'performance_threshold': 0.7,  # 模型性能阈值
    'grid_search_cv': False,  # 是否启用网格搜索（会增加训练时间）
    'max_features': None,  # 最大特征数，None表示自动
}

# 确保模型保存目录存在
os.makedirs(MODEL_CONFIG['model_save_dir'], exist_ok=True)

# 模型状态文件
MODEL_STATUS_FILE = os.path.join(MODEL_CONFIG['model_save_dir'], 'model_status.json')

class ModelTrainer:
    """模型训练器"""
    
    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.scaler = None
        self.tfidf_vectorizer = None
        self.model_status = self._load_model_status()
    
    def _load_model_status(self):
        """加载模型状态"""
        try:
            if os.path.exists(MODEL_STATUS_FILE):
                with open(MODEL_STATUS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载模型状态失败: {e}")
        
        # 返回默认状态
        return {
            'last_train_time': None,
            'last_train_status': 'none',
            'train_count': 0,
            'model_version': '0.0.0',
            'accuracy': 0.0,
            'best_params': None,
            'data_samples': 0,
            'last_error': None
        }
    
    def _save_model_status(self):
        """保存模型状态"""
        try:
            with open(MODEL_STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.model_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存模型状态失败: {e}")
    
    def _get_db_connection(self):
        """获取数据库连接"""
        try:
            connection = pymysql.connect(**DB_CONFIG)
            logger.info("成功连接到数据库")
            return connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def load_data_from_db(self):
        """从数据库加载训练数据"""
        try:
            logger.info("开始从数据库加载数据")
            
            with self._get_db_connection() as conn:
                # 查询病例数据，用于训练疾病分类模型，排除异常类别
                query = """
                SELECT `type`, gender, age, content, illDuration 
                FROM cases 
                WHERE content IS NOT NULL AND content != ''
                AND `type` NOT IN ('类型')  -- 排除异常类别
                LIMIT 10000
                """
                
                df = pd.read_sql(query, conn)
                
                logger.info(f"成功加载{len(df)}条训练数据")
                
                # 数据样本不足时，生成一些模拟数据
                if len(df) < MODEL_CONFIG['min_data_samples']:
                    logger.warning(f"数据样本不足({len(df)}条)，生成模拟数据补充")
                    synthetic_data = self._generate_synthetic_data(
                        MODEL_CONFIG['min_data_samples'] - len(df), df
                    )
                    df = pd.concat([df, synthetic_data], ignore_index=True)
                    logger.info(f"补充后共{len(df)}条训练数据")
                
                return df
        except Exception as e:
            logger.error(f"从数据库加载数据失败: {e}")
            # 生成完全模拟的数据
            logger.info("生成模拟数据用于训练")
            return self._generate_synthetic_data(MODEL_CONFIG['min_data_samples'])
    
    def _generate_synthetic_data(self, count, real_data=None):
        """生成模拟训练数据"""
        logger.info(f"生成{count}条模拟训练数据")
        
        # 基础疾病类型
        disease_types = ['感冒', '高血压', '糖尿病', '冠心病', '肺炎', '胃炎', '肝炎', '肾炎']
        
        # 基础症状描述模板
        symptom_templates = {
            '感冒': ['发热、咳嗽、流鼻涕', '头痛、喉咙痛、乏力', '打喷嚏、鼻塞、肌肉酸痛'],
            '高血压': ['头晕、头痛、耳鸣', '胸闷、心悸、视力模糊', '血压升高、疲劳、失眠'],
            '糖尿病': ['多饮、多尿、多食', '体重下降、乏力', '口渴、视力模糊、伤口愈合慢'],
            '冠心病': ['胸痛、胸闷、气短', '心悸、乏力、出汗', '呼吸困难、头晕、恶心'],
            '肺炎': ['发热、咳嗽、咳痰', '胸痛、呼吸困难', '乏力、食欲不振、肌肉酸痛']
        }
        
        # 性别和年龄分布
        genders = ['男', '女', '未知']
        ages = list(range(0, 100))
        
        # 病程分布
        durations = ['1天内', '1-3天', '3-7天', '1-2周', '2-4周', '1-3个月', '3个月以上']
        
        data = []
        for i in range(count):
            # 随机选择疾病类型
            if real_data is not None and not real_data.empty:
                # 如果有真实数据，按照其分布生成
                disease = np.random.choice(real_data['type'].values)
            else:
                disease = np.random.choice(disease_types)
            
            # 生成症状描述
            if disease in symptom_templates:
                symptoms = np.random.choice(symptom_templates[disease])
            else:
                symptoms = f"{disease}相关症状"
            
            # 生成其他特征
            gender = np.random.choice(genders)
            age = str(np.random.choice(ages))
            ill_duration = np.random.choice(durations)
            
            # 添加一些随机性
            if np.random.random() > 0.8:
                symptoms += f"，伴有其他症状"
            
            data.append({
                'type': disease,
                'gender': gender,
                'age': age,
                'content': symptoms,
                'illDuration': ill_duration
            })
        
        return pd.DataFrame(data)
    
    def preprocess_data(self, df):
        """预处理数据"""
        try:
            logger.info("开始数据预处理")
            
            # 复制数据以避免修改原始数据
            df_processed = df.copy()
            
            # 处理缺失值
            df_processed = df_processed.fillna({
                'gender': '未知',
                'age': '0',
                'illDuration': '未知'
            })
            
            # 处理年龄（转为数值）
            def clean_age(age):
                try:
                    # 尝试提取数字
                    import re
                    match = re.search(r'\d+', str(age))
                    if match:
                        return int(match.group())
                    return 0
                except:
                    return 0
            
            df_processed['age_numeric'] = df_processed['age'].apply(clean_age)
            
            # 创建年龄分组特征
            df_processed['age_group'] = pd.cut(
                df_processed['age_numeric'],
                bins=[-1, 18, 35, 50, 65, 100],
                labels=['儿童', '青年', '中年', '老年', '高龄']
            )
            
            # 编码性别
            if self.label_encoder is None:
                self.label_encoder = LabelEncoder()
                self.label_encoder.fit(['男', '女', '未知'])
            
            df_processed['gender_encoded'] = self.label_encoder.transform(df_processed['gender'])
            
            # 编码病程
            duration_mapping = {
                '未知': 0,
                '1天内': 1,
                '1-3天': 2,
                '3-7天': 3,
                '1-2周': 4,
                '2-4周': 5,
                '1-3个月': 6,
                '3个月以上': 7
            }
            
            df_processed['duration_encoded'] = df_processed['illDuration'].map(
                lambda x: duration_mapping.get(str(x), 0)
            )
            
            # TF-IDF向量化文本内容，优化参数
            if self.tfidf_vectorizer is None:
                # 加载自定义停用词
                stopwords_path = os.path.join(os.path.dirname(__file__), '../machine/stopword.txt')
                stop_words = None
                try:
                    with open(stopwords_path, 'r', encoding='utf-8') as f:
                        stop_words = [line.strip() for line in f if line.strip()]
                    logger.info(f"加载自定义停用词{len(stop_words)}个")
                except:
                    logger.warning("无法加载自定义停用词，使用默认设置")
                
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=5000,  # 设置合理的最大特征数
                    ngram_range=(1, 3),  # 考虑1-3元语法
                    min_df=3,  # 忽略出现次数少于3次的词
                    max_df=0.9,  # 忽略出现频率高于90%的词
                    stop_words=stop_words  # 使用自定义停用词
                )
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(df_processed['content'])
            else:
                tfidf_matrix = self.tfidf_vectorizer.transform(df_processed['content'])
            
            # 创建特征矩阵
            tfidf_df = pd.DataFrame(
                tfidf_matrix.toarray(),
                columns=[f'tfidf_{i}' for i in range(tfidf_matrix.shape[1])]
            )
            
            # 合并特征
            feature_df = pd.concat([
                df_processed[['gender_encoded', 'age_numeric', 'duration_encoded']].reset_index(drop=True),
                tfidf_df.reset_index(drop=True)
            ], axis=1)
            
            # 准备目标变量
            target_encoder = LabelEncoder()
            y = target_encoder.fit_transform(df_processed['type'])
            
            # 保存目标编码器
            self.target_encoder = target_encoder
            
            logger.info(f"数据预处理完成，特征维度: {feature_df.shape}, 目标类别: {len(np.unique(y))}")
            
            # 处理类别不平衡 - 使用SMOTE过采样
            class_counts = df_processed['type'].value_counts()
            logger.info(f"各类别样本数:\n{class_counts}")
            
            # 仅在少数类样本数过少时使用SMOTE
            if any(count < 100 for count in class_counts.values):
                logger.info("应用SMOTE处理类别不平衡")
                try:
                    smote = SMOTE(random_state=MODEL_CONFIG['random_state'])
                    X_resampled, y_resampled = smote.fit_resample(feature_df, y)
                    
                    logger.info(f"SMOTE后特征维度: {X_resampled.shape}, 目标类别: {len(np.unique(y_resampled))}")
                    logger.info(f"SMOTE后各类别样本数:\n{pd.Series(y_resampled).value_counts()}")
                    
                    return X_resampled, y_resampled
                except Exception as e:
                    logger.error(f"SMOTE处理失败: {e}")
                    logger.info("使用原始数据继续训练")
            
            return feature_df, y
        except Exception as e:
            logger.error(f"数据预处理失败: {e}")
            raise
    
    def train_model(self, X, y):
        """训练模型"""
        try:
            logger.info("开始模型训练")
            
            # 分割训练集和测试集
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=MODEL_CONFIG['test_size'],
                random_state=MODEL_CONFIG['random_state'],
                stratify=y if len(np.unique(y)) > 1 else None
            )
            
            logger.info(f"训练集大小: {len(X_train)}, 测试集大小: {len(X_test)}")
            
            # 标准化特征
            if self.scaler is None:
                self.scaler = StandardScaler()
                X_train_scaled = self.scaler.fit_transform(X_train)
            else:
                X_train_scaled = self.scaler.transform(X_train)
            
            X_test_scaled = self.scaler.transform(X_test)
            
            # 定义模型
            if MODEL_CONFIG['grid_search_cv']:
                # 使用网格搜索优化参数，加入class_weight
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20, 30],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4],
                    'class_weight': [None, 'balanced']  # 添加类别权重选项
                }
                
                grid_search = GridSearchCV(
                    RandomForestClassifier(random_state=MODEL_CONFIG['random_state']),
                    param_grid,
                    cv=5,
                    scoring='f1_weighted',  # 使用加权F1分数，更适合不平衡数据
                    n_jobs=-1
                )
                
                grid_search.fit(X_train_scaled, y_train)
                self.model = grid_search.best_estimator_
                best_params = grid_search.best_params_
                
                logger.info(f"网格搜索完成，最佳参数: {best_params}")
            else:
                # 使用默认参数，添加class_weight='balanced'处理类别不平衡
                self.model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=None,
                    min_samples_split=2,
                    min_samples_leaf=1,
                    random_state=MODEL_CONFIG['random_state'],
                    bootstrap=True,
                    class_weight='balanced'
                )
                self.model.fit(X_train_scaled, y_train)
                best_params = self.model.get_params()
            
            # 评估模型
            y_pred = self.model.predict(X_test_scaled)
            
            # 使用更全面的评估指标
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UndefinedMetricWarning)
                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
                recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
                f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
                
                logger.info(f"模型训练完成")
                logger.info(f"测试集准确率: {accuracy:.4f}")
                logger.info(f"加权精确率: {precision:.4f}")
                logger.info(f"加权召回率: {recall:.4f}")
                logger.info(f"加权F1分数: {f1:.4f}")
                logger.info(f"分类报告:\n{classification_report(y_test, y_pred, target_names=self.target_encoder.classes_, zero_division=0)}")
            
            # 更新模型状态
            self.model_status['last_train_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.model_status['last_train_status'] = 'success'
            self.model_status['train_count'] += 1
            self.model_status['model_version'] = f"1.0.{self.model_status['train_count']}"
            self.model_status['accuracy'] = float(accuracy)
            self.model_status['best_params'] = best_params
            self.model_status['data_samples'] = len(X)
            self.model_status['last_error'] = None
            
            # 保存模型
            self._save_model()
            self._save_model_status()
            
            return {
                'accuracy': accuracy,
                'best_params': best_params,
                'model_version': self.model_status['model_version'],
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            }
        except Exception as e:
            logger.error(f"模型训练失败: {e}")
            self.model_status['last_train_status'] = 'failed'
            self.model_status['last_error'] = str(e)
            self._save_model_status()
            raise
    
    def _save_model(self):
        """保存模型及其组件"""
        try:
            model_files = {
                'model': 'classifier_model.pkl',
                'label_encoder': 'label_encoder.pkl',
                'scaler': 'scaler.pkl',
                'tfidf_vectorizer': 'tfidf_vectorizer.pkl',
                'target_encoder': 'target_encoder.pkl'
            }
            
            for name, filename in model_files.items():
                file_path = os.path.join(MODEL_CONFIG['model_save_dir'], filename)
                with open(file_path, 'wb') as f:
                    pickle.dump(getattr(self, name, None), f)
                logger.info(f"保存{name}到{file_path}")
            
            # 保存版本信息
            version_file = os.path.join(MODEL_CONFIG['model_save_dir'], 'version.txt')
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write(f"Version: {self.model_status['model_version']}\n")
                f.write(f"Train Time: {self.model_status['last_train_time']}\n")
                f.write(f"Accuracy: {self.model_status['accuracy']:.4f}\n")
        except Exception as e:
            logger.error(f"保存模型失败: {e}")
            raise
    
    def load_model(self):
        """加载模型及其组件"""
        try:
            model_files = {
                'model': 'classifier_model.pkl',
                'label_encoder': 'label_encoder.pkl',
                'scaler': 'scaler.pkl',
                'tfidf_vectorizer': 'tfidf_vectorizer.pkl',
                'target_encoder': 'target_encoder.pkl'
            }
            
            all_loaded = True
            for name, filename in model_files.items():
                file_path = os.path.join(MODEL_CONFIG['model_save_dir'], filename)
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        setattr(self, name, pickle.load(f))
                    logger.info(f"从{file_path}加载{name}")
                else:
                    logger.warning(f"模型文件不存在: {file_path}")
                    all_loaded = False
            
            return all_loaded
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False
    
    def predict(self, symptoms_text, gender='未知', age='0', ill_duration='未知'):
        """使用模型进行预测"""
        try:
            # 检查模型是否加载
            if not self.model:
                if not self.load_model():
                    raise NotFittedError("模型未训练或加载失败")
            
            # 准备输入数据
            input_data = pd.DataFrame([{
                'gender': gender,
                'age': age,
                'content': symptoms_text,
                'illDuration': ill_duration
            }])
            
            # 预处理
            df_processed = input_data.copy()
            
            # 处理年龄
            def clean_age(age):
                try:
                    import re
                    match = re.search(r'\d+', str(age))
                    if match:
                        return int(match.group())
                    return 0
                except:
                    return 0
            
            df_processed['age_numeric'] = df_processed['age'].apply(clean_age)
            
            # 编码性别
            df_processed['gender_encoded'] = self.label_encoder.transform(df_processed['gender'])
            
            # 编码病程
            duration_mapping = {
                '未知': 0,
                '1天内': 1,
                '1-3天': 2,
                '3-7天': 3,
                '1-2周': 4,
                '2-4周': 5,
                '1-3个月': 6,
                '3个月以上': 7
            }
            
            df_processed['duration_encoded'] = df_processed['illDuration'].map(
                lambda x: duration_mapping.get(str(x), 0)
            )
            
            # TF-IDF向量化
            tfidf_matrix = self.tfidf_vectorizer.transform(df_processed['content'])
            tfidf_df = pd.DataFrame(
                tfidf_matrix.toarray(),
                columns=[f'tfidf_{i}' for i in range(tfidf_matrix.shape[1])]
            )
            
            # 合并特征
            feature_df = pd.concat([
                df_processed[['gender_encoded', 'age_numeric', 'duration_encoded']].reset_index(drop=True),
                tfidf_df.reset_index(drop=True)
            ], axis=1)
            
            # 标准化
            feature_scaled = self.scaler.transform(feature_df)
            
            # 预测
            prediction = self.model.predict(feature_scaled)
            probabilities = self.model.predict_proba(feature_scaled)
            
            # 获取预测结果
            predicted_class = self.target_encoder.inverse_transform(prediction)[0]
            
            # 获取概率最高的前3个预测结果
            top_indices = np.argsort(probabilities[0])[-3:][::-1]
            top_predictions = [
                {
                    'disease': self.target_encoder.inverse_transform([i])[0],
                    'probability': float(probabilities[0][i])
                }
                for i in top_indices
            ]
            
            return {
                'predicted_disease': predicted_class,
                'top_predictions': top_predictions,
                'model_version': self.model_status.get('model_version', 'unknown')
            }
        except Exception as e:
            logger.error(f"预测失败: {e}")
            raise
    
    def should_retrain(self):
        """判断是否需要重训练模型"""
        try:
            # 检查上次训练时间
            if not self.model_status['last_train_time']:
                logger.info("模型从未训练过，需要训练")
                return True
            
            # 检查时间间隔
            last_train = datetime.strptime(
                self.model_status['last_train_time'], 
                '%Y-%m-%d %H:%M:%S'
            )
            days_since_last_train = (datetime.now() - last_train).days
            
            if days_since_last_train >= MODEL_CONFIG['retrain_threshold_days']:
                logger.info(f"距离上次训练已超过{days_since_last_train}天，需要重训练")
                return True
            
            # 检查模型性能
            if self.model_status['accuracy'] < MODEL_CONFIG['performance_threshold']:
                logger.info(f"模型准确率({self.model_status['accuracy']:.4f})低于阈值，需要重训练")
                return True
            
            logger.info(f"模型不需要重训练，上次训练{days_since_last_train}天前，准确率{self.model_status['accuracy']:.4f}")
            return False
        except Exception as e:
            logger.error(f"判断是否重训练时发生错误: {e}")
            # 发生错误时，默认需要重训练
            return True
    
    def retrain_model(self):
        """重训练模型的主方法"""
        logger.info("开始模型重训练流程")
        
        try:
            # 检查是否需要重训练
            if not self.should_retrain():
                return {
                    'status': 'skipped',
                    'reason': '模型不需要重训练'
                }
            
            # 加载数据
            df = self.load_data_from_db()
            
            # 预处理数据
            X, y = self.preprocess_data(df)
            
            # 训练模型
            result = self.train_model(X, y)
            
            logger.info(f"模型重训练完成: {result}")
            return {
                'status': 'success',
                'result': result
            }
        except Exception as e:
            logger.error(f"模型重训练失败: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def get_model_status(self):
        """获取模型状态"""
        return self.model_status
    
    def evaluate_model(self):
        """评估模型性能"""
        try:
            # 加载最新数据
            df = self.load_data_from_db()
            
            # 预处理
            X, y = self.preprocess_data(df)
            
            # 检查模型是否加载
            if not self.model:
                if not self.load_model():
                    raise NotFittedError("模型未训练或加载失败")
            
            # 预测
            X_scaled = self.scaler.transform(X)
            y_pred = self.model.predict(X_scaled)
            
            # 计算指标，忽略UndefinedMetricWarning
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UndefinedMetricWarning)
                accuracy = accuracy_score(y, y_pred)
                precision = precision_score(y, y_pred, average='weighted', zero_division=0)
                recall = recall_score(y, y_pred, average='weighted', zero_division=0)
                f1 = f1_score(y, y_pred, average='weighted', zero_division=0)
                report = classification_report(y, y_pred, target_names=self.target_encoder.classes_, output_dict=True, zero_division=0)
                cm = confusion_matrix(y, y_pred)
            
            # 获取特征重要性
            feature_importance = []
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                indices = np.argsort(importances)[::-1]
                
                # 获取前10个重要特征
                for f in range(min(10, len(indices))):
                    feature_importance.append({
                        'feature_index': int(indices[f]),
                        'importance': float(importances[indices[f]])
                    })
            
            result = {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'classification_report': report,
                'confusion_matrix': cm.tolist(),
                'feature_importance': feature_importance,
                'eval_samples': len(X)
            }
            
            logger.info(f"模型评估完成")
            logger.info(f"准确率: {accuracy:.4f}")
            logger.info(f"加权精确率: {precision:.4f}")
            logger.info(f"加权召回率: {recall:.4f}")
            logger.info(f"加权F1分数: {f1:.4f}")
            return result
        except Exception as e:
            logger.error(f"模型评估失败: {e}")
            raise

# 创建全局模型训练器实例
model_trainer = ModelTrainer()

# 定义可被定时任务调用的函数
def scheduled_retrain_model():
    """用于定时任务的模型重训练函数"""
    logger.info("定时任务触发模型重训练")
    return model_trainer.retrain_model()

def scheduled_evaluate_model():
    """用于定时任务的模型评估函数"""
    logger.info("定时任务触发模型评估")
    try:
        return model_trainer.evaluate_model()
    except Exception as e:
        logger.error(f"模型评估失败: {e}")
        return {'status': 'failed', 'error': str(e)}

if __name__ == "__main__":
    # 测试模型训练功能
    logger.info("测试模型训练器")
    
    # 执行重训练
    result = scheduled_retrain_model()
    logger.info(f"重训练结果: {result}")
    
    # 评估模型
    try:
        evaluation = scheduled_evaluate_model()
        logger.info(f"模型评估结果: {evaluation['accuracy']:.4f}")
    except Exception as e:
        logger.error(f"模型评估失败: {e}")
    
    # 测试预测功能
    try:
        prediction = model_trainer.predict(
            symptoms_text="发热、咳嗽、流鼻涕、头痛",
            gender="男",
            age="30",
            ill_duration="1-3天"
        )
        logger.info(f"预测结果: {prediction}")
    except Exception as e:
        logger.error(f"预测测试失败: {e}")
    
    # 打印模型状态
    status = model_trainer.get_model_status()
    logger.info(f"模型状态: {status}")