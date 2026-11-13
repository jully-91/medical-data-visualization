<template>
  <div class="pred-container">
    <!-- 左侧：智能症状输入区 -->
    <div class="left">
        <div class="title">
        <img src="../assets/logo.png" class="logo" alt="" />
           病情初步预测
        </div>

       <div class="form">
        <div class="form-group">
          <div class="form-label">症状描述</div>
          <div class="form-control">
            <!-- 智能文本输入框：支持自由描述 + 智能提示 -->
            <textarea
              v-model="formSubmit.content"
              class="symptom-input"
              placeholder="请尽量详细地描述当前症状，例如：近一周持续发热伴咳嗽、咽痛，夜间出汗明显等。"
            ></textarea>
          </div>
        </div>

        <!-- 常见症状快捷选择 -->
        <div class="form-group">
          <div class="form-label">常见症状</div>
          <div class="form-control symptom-tags">
            <span
              v-for="item in symptomSuggestions"
              :key="item"
              class="symptom-tag"
              @click="appendSymptom(item)"
            >
              {{ item }}
            </span>
          </div>
        </div>

        <!-- 根据关键字的智能建议 -->
        <div class="smart-tips" v-if="smartTips.length">
          <div class="smart-tips-title">智能建议</div>
          <ul class="smart-tips-list">
            <li v-for="(tip, index) in smartTips" :key="index">{{ tip }}</li>
          </ul>
        </div>

        <div class="form-group button">
          <button type="button" style="cursor: pointer" @click="submit">
            提交预测
          </button>
        </div>
       </div>

      <!-- 左侧下方：预测历史记录 -->
      <div class="section history-section left-history-section">
        <div class="section-header">
          <dv-decoration-11 style="width: 340px; height: 56px; font-size: 14px">
            预测历史记录
          </dv-decoration-11>
        </div>
        <dv-border-box-9 class="section-box">
          <div class="history-wrapper">
            <div class="history-list">
              <div class="history-header">
                <span class="col-time">时间</span>
                <span class="col-desc">症状摘要</span>
                <span class="col-disease">预测结果</span>
                <span class="col-confidence">置信度</span>
                <span class="col-compare">对比</span>
              </div>
              <div
                v-if="historyList.length === 0"
                class="empty-text"
                style="padding: 10px 0"
              >
                暂无历史记录，完成第一次预测后将自动生成。
              </div>
              <div
                v-for="item in historyList"
                :key="item.id"
                class="history-row"
                :class="{ 'history-row--active': compareIds.includes(item.id) }"
                @click="toggleCompare(item.id)"
              >
                <span class="col-time">{{ item.time }}</span>
                <span class="col-desc" :title="item.content">{{ item.briefContent }}</span>
                <span class="col-disease">{{ item.disease }}</span>
                <span class="col-confidence">
                  <span v-if="item.confidence !== null">
                    {{ (item.confidence * 100).toFixed(1) }}%
                  </span>
                  <span v-else>--</span>
                </span>
                <span class="col-compare">
                  <span class="compare-flag">
                    {{ compareIds.includes(item.id) ? '已选中' : '点击选择' }}
                  </span>
                </span>
              </div>
            </div>

            <!-- 简单对比分析区域 -->
            <div class="history-compare" v-if="compareItems.length >= 1">
              <div class="compare-title">结果对比分析（最多选择 2 条）</div>
              <div class="compare-content">
                <div
                  v-for="item in compareItems"
                  :key="item.id"
                  class="compare-card"
                >
                  <div class="compare-time">{{ item.time }}</div>
                  <div class="compare-disease">{{ item.disease }}</div>
                  <div class="compare-confidence">
                    置信度：
                    <span v-if="item.confidence !== null">
                      {{ (item.confidence * 100).toFixed(1) }}%
                    </span>
                    <span v-else>--</span>
                  </div>
                  <div class="compare-desc" :title="item.content">
                    {{ item.briefContent }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </dv-border-box-9>
       </div>
    </div>

    <!-- 右侧：预测结果 / 相似病例 / 历史记录 -->
    <div class="right">
      <!-- 顶部提示 -->
      <div class="top">
            <div class="content">
              <div class="title">
            <dv-decoration-11 style="width: 600px; height: 60px; font-size: 13px">
              小贴士：仅为机器预测结果，不能替代医生诊断，如有不适请及时前往正规医院就诊
            </dv-decoration-11>
          </div>
        </div>
      </div>

      <!-- 预测结果（卡片展示） -->
      <div class="section prediction-section">
        <div class="section-header">
          <dv-decoration-11 style="width: 320px; height: 56px; font-size: 14px">
            预测结果
          </dv-decoration-11>
        </div>
        <dv-border-box-9 class="section-box">
          <div class="prediction-cards">
            <div v-if="parsedPredictions.length === 0" class="empty-text">
              暂无预测结果，请先在左侧输入症状并提交。
            </div>
            <div
              v-else
              v-for="item in parsedPredictions"
              :key="item.id"
              class="prediction-card"
            >
              <div class="prediction-card-header">
                <span class="prediction-disease">{{ item.disease || '未知疾病' }}</span>
                <span v-if="item.confidence !== null" class="prediction-confidence">
                  置信度 {{ (item.confidence * 100).toFixed(1) }}%
                </span>
                <span v-else class="prediction-confidence prediction-confidence--unknown">
                  置信度待提供
                </span>
              </div>
              <div class="prediction-card-body">
                <div class="prediction-label">模型建议</div>
                <div class="prediction-advice">
                  {{ item.advice || defaultAdviceText }}
                </div>
              </div>
            </div>
          </div>
        </dv-border-box-9>
      </div>

      <!-- 相似病例推荐 -->
      <div class="section similar-section">
        <div class="section-header">
          <dv-decoration-11 style="width: 320px; height: 56px; font-size: 14px">
            相似病例推荐
          </dv-decoration-11>
        </div>
        <dv-border-box-9 class="section-box">
          <div class="similar-list">
            <div v-if="displaySimilarCases.length === 0" class="empty-text">
              暂无相似病例，将在获取到预测结果后自动推荐。
            </div>
            <div
              v-else
              v-for="item in displaySimilarCases"
              :key="item.id"
              class="similar-item"
              @click="selectCase(item)"
            >
              <div class="similar-item-main">
                <div class="similar-disease">{{ item.disease }}</div>
                <div class="similar-meta">
                  <span>年龄：{{ item.age }}</span>
                  <span>性别：{{ item.gender }}</span>
                  <span>就诊时间：{{ item.visitTime }}</span>
                </div>
              </div>
              <div class="similar-score">
                相似度
                <span class="similar-score-value">{{ (item.similarity * 100).toFixed(0) }}%</span>
              </div>
            </div>
            </div>
      
          <!-- 右侧病例详情（仅前端展示） -->
          <div v-if="selectedCase" class="case-detail">
            <div class="case-detail-header">
              <span>病例详情</span>
              <span class="case-detail-close" @click="selectedCase = null">×</span>
            </div>
            <div class="case-detail-body">
              <div class="case-row">
                <span class="case-label">疾病名称：</span>
                <span>{{ selectedCase.disease }}</span>
              </div>
              <div class="case-row">
                <span class="case-label">基本信息：</span>
                <span>{{ selectedCase.gender }}，{{ selectedCase.age }}岁</span>
              </div>
              <div class="case-row">
                <span class="case-label">就诊时间：</span>
                <span>{{ selectedCase.visitTime }}</span>
              </div>
              <div class="case-row">
                <span class="case-label">主要症状：</span>
                <span>{{ selectedCase.symptoms }}</span>
              </div>
              <div class="case-row">
                <span class="case-label">诊疗方案：</span>
                <span>{{ selectedCase.treatment }}</span>
              </div>
            </div>
          </div>
        </dv-border-box-9>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'Pred',
  data() {
    return {
      formSubmit: {
        content: '',
      },
      // 原始后端返回的结果字符串（兼容旧逻辑）
      resultData: '暂无信息',
      // 结构化的预测结果列表（前端使用）
      predictionList: [],
      // 相似病例推荐
      similarCases: [],
      // 历史记录（保存在本地 localStorage，仅前端）
      historyList: [],
      // UI 辅助状态
      selectedCase: null,
      compareIds: [],
      symptomSuggestions: [
        '发热',
        '咳嗽',
        '咽痛',
        '胸闷气短',
        '乏力',
        '头痛',
        '腹痛',
        '恶心呕吐',
        '腹泻',
        '心悸',
      ],
      keywordTipsMap: {
        发热: '如体温持续 ≥ 38.5℃ 且超过 3 天，建议尽快就医并完善血常规等检查。',
        咳嗽: '注意区分干咳或有痰咳嗽，是否伴随胸痛、呼吸困难等症状。',
        胸闷: '如胸闷伴胸痛、出冷汗、活动后加重等情况，应立即前往急诊就诊。',
        腹痛: '请描述腹痛部位（上腹/下腹/右下腹等）、性质（隐痛/绞痛）及持续时间。',
        头痛: '留意是否伴有视物模糊、肢体无力、呕吐等神经系统相关症状。',
      },
      defaultAdviceText:
        '建议结合详细病史及体格检查，由专业医生做出最终诊断和治疗方案。如症状持续或加重，请尽快就医。',
    };
  },
  computed: {
    // 根据后端返回 + 本地 predictionList，生成用于展示的列表
    parsedPredictions() {
      if (this.predictionList && this.predictionList.length) {
        return this.predictionList;
      }

      if (!this.resultData || this.resultData === '暂无信息') {
        return [];
      }

      // 兼容旧后端：仅返回一个字符串结果
      return [
        {
          id: 'single',
          disease: this.resultData,
          confidence: null,
          advice: '',
        },
      ];
    },
    // 智能建议：根据输入内容中的关键词实时给出文字提示
    smartTips() {
      const content = this.formSubmit.content || '';
      const tips = [];
      Object.keys(this.keywordTipsMap).forEach((key) => {
        if (content.includes(key)) {
          tips.push(this.keywordTipsMap[key]);
        }
      });
      // 去重 + 最多展示 3 条，避免过长
      const unique = Array.from(new Set(tips));
      return unique.slice(0, 3);
    },
    // 展示的相似病例列表：只使用接口返回的数据（不再使用前端硬编码示例）
    displaySimilarCases() {
      if (this.similarCases && this.similarCases.length) {
        return this.similarCases;
      }
      // 如果接口没有返回相似病例，则返回空数组，界面展示“暂无相似病例”
      return [];
    },
    // 历史记录中被选中的条目，用于对比展示
    compareItems() {
      if (!this.compareIds.length) return [];
      return this.historyList.filter((item) => this.compareIds.includes(item.id));
    },
  },
  created() {
    this.loadHistory();
  },
  methods: {
    // 追加常见症状到输入框
    appendSymptom(text) {
      if (!this.formSubmit.content) {
        this.formSubmit.content = text;
        return;
      }
      if (this.formSubmit.content.includes(text)) return;
      this.formSubmit.content = `${this.formSubmit.content}，${text}`;
    },

    // 提交预测（仅调用原有接口，不做任何后端改动）
    async submit() {
      if (!this.formSubmit.content) {
        this.$message && this.$message.warning && this.$message.warning('请先输入症状描述');
      }
      try {
        const res = await this.$http.post('./submitModel', this.formSubmit);
        // 兼容原有字段
        this.resultData = res.data.resultData || '暂无信息';

        // 尝试从返回值中读取结构化信息（如果后端已经提供）
        this.updatePredictionFromResponse(res.data);
        this.updateSimilarCasesFromResponse(res.data);
        this.appendHistoryFromResponse(res.data);
      } catch (e) {
        // 请求失败时，仅在前端给出提示，不修改后端逻辑
        console.error('submitModel error:', e);
        this.$message &&
          this.$message.error &&
          this.$message.error('预测失败，请稍后重试或检查网络连接');
      }
    },

    // 根据接口返回的数据更新 predictionList（前端解析，不要求后端改动）
    updatePredictionFromResponse(data = {}) {
      const list = [];

      if (Array.isArray(data.predictions)) {
        data.predictions.forEach((item, index) => {
          list.push({
            id: item.id || `api-${index}`,
            disease: item.disease || item.label || this.resultData,
            confidence:
              typeof item.confidence === 'number'
                ? item.confidence
                : typeof item.score === 'number'
                ? item.score
                : null,
            advice: item.advice || '',
          });
        });
      } else if (data.disease || data.label || this.resultData) {
        list.push({
          id: 'single-api',
          disease: data.disease || data.label || this.resultData,
          confidence:
            typeof data.confidence === 'number'
              ? data.confidence
              : typeof data.score === 'number'
              ? data.score
              : null,
          advice: data.advice || '',
        });
      }

      this.predictionList = list;
    },

    // 根据接口返回更新相似病例（若无则保持默认示例数据）
    updateSimilarCasesFromResponse(data = {}) {
      if (Array.isArray(data.similarCases) && data.similarCases.length) {
        this.similarCases = data.similarCases.map((item, index) => ({
          id: item.id || `case-${index}`,
          disease: item.disease || item.label || '未命名病例',
          age: item.age || '--',
          gender: item.gender || '--',
          visitTime: item.visitTime || item.date || '--',
          similarity:
            typeof item.similarity === 'number'
              ? item.similarity
              : typeof item.score === 'number'
              ? item.score
              : 0.7,
          symptoms: item.symptoms || item.description || '—',
          treatment: item.treatment || '—',
        }));
      }
    },

    // 将本次预测记录存入历史（本地）
    appendHistoryFromResponse(data = {}) {
      const firstPrediction =
        (this.predictionList && this.predictionList[0]) || this.parsedPredictions[0];
      if (!firstPrediction) return;

      const now = new Date();
      const timeStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(
        2,
        '0',
      )}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(
        2,
        '0',
      )}:${String(now.getMinutes()).padStart(2, '0').padStart(2, '0')}`;

      const content = this.formSubmit.content || '';
      const brief =
        content.length > 16 ? `${content.slice(0, 16).replace(/\s+/g, '')}...` : content;

      const item = {
        id: `history-${now.getTime()}`,
        time: timeStr,
        content,
        briefContent: brief || '（无症状描述）',
        disease: firstPrediction.disease || data.disease || this.resultData,
        confidence:
          typeof firstPrediction.confidence === 'number'
            ? firstPrediction.confidence
            : typeof data.confidence === 'number'
            ? data.confidence
            : null,
      };

      this.historyList.unshift(item);
      // 最多保留 20 条
      if (this.historyList.length > 20) {
        this.historyList = this.historyList.slice(0, 20);
      }
      this.saveHistory();
    },

    // 选中/关闭相似病例详情
    selectCase(item) {
      if (this.selectedCase && this.selectedCase.id === item.id) {
        this.selectedCase = null;
      } else {
        this.selectedCase = item;
      }
    },

    // 选择历史记录用于对比（最多 2 条）
    toggleCompare(id) {
      const index = this.compareIds.indexOf(id);
      if (index > -1) {
        this.compareIds.splice(index, 1);
      } else {
        if (this.compareIds.length >= 2) {
          // 替换最早选中的一条
          this.compareIds.shift();
        }
        this.compareIds.push(id);
      }
    },

    // 本地存储
    saveHistory() {
      try {
        window.localStorage.setItem('pred_history', JSON.stringify(this.historyList));
      } catch (e) {
        console.warn('saveHistory error:', e);
      }
    },
    loadHistory() {
      try {
        const raw = window.localStorage.getItem('pred_history');
        if (raw) {
          this.historyList = JSON.parse(raw) || [];
        }
      } catch (e) {
        console.warn('loadHistory error:', e);
      }
    },
  },
};
</script>

<style lang="less" scoped>
.pred-container {
  display: flex;
    width: 100%;
  height: 100vh;
  color: #ffffff;
}

.left {
  width: 720px;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 40px;

  .title {
    display: flex;
    align-items: center;
    color: #26fffd;
    font-size: 34px;
    font-weight: bold;

    .logo {
      width: 72px;
      height: 72px;
      margin-right: 16px;
    }
  }

  .form {
    margin-top: 24px;
    width: 92%;

    .form-group {
      display: flex;
      align-items: flex-start;
      margin-bottom: 16px;

      .form-label {
        min-width: 80px;
        margin-right: 18px;
        font-size: 16px;
        color: #ffffff;
        padding-top: 4px;
      }

      .form-control {
        flex: 1;
      }
    }
  }
}

.left-history-section {
  margin-top: 12px;
  width: 90%;
  /* 控制整个历史记录模块的最大高度，避免超出大屏外框，同时比之前更高一些 */
  max-height: 320px;
}

.symptom-input {
  width: 100%;
  min-height: 140px;
  border-radius: 12px;
  background: rgba(211, 220, 247, 0.1);
  border: 1px solid rgba(38, 255, 253, 0.35);
  outline: none;
  padding: 10px 12px;
  color: #ffffff;
  resize: vertical;
  font-size: 14px;
}

.symptom-tags {
    display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.symptom-tag {
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid rgba(38, 255, 253, 0.4);
  color: #26fffd;
  cursor: pointer;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.25);
  transition: all 0.2s;

  &:hover {
    background: rgba(38, 255, 253, 0.16);
  }
}

.smart-tips {
  margin: 6px 0 12px 98px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.35);
  border-left: 2px solid #26fffd;
  border-radius: 4px;
  max-width: calc(100% - 98px);

  .smart-tips-title {
    font-size: 13px;
    color: #26fffd;
    margin-bottom: 4px;
  }

  .smart-tips-list {
    padding-left: 16px;
    font-size: 12px;

    li {
      line-height: 1.5;
      margin-bottom: 2px;
    }
  }
}

.button {
    width: 100%;
  height: 36px;
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

button {
  width: 60%;
  height: 100%;
  background: linear-gradient(90deg, #26fffd, #00a6ff);
  color: rgb(0, 0, 0);
  border-radius: 18px;
  border: none;
  font-weight: bold;
  letter-spacing: 2px;
}

.right {
  flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
  padding-top: 26px;
  padding-right: 40px;
  overflow-y: auto;

  .top {
    width: 90%;

    .content {
      padding: 10px 20px 0 20px;

      .title {
        display: flex;
        justify-content: center;
        color: #ffffff;
        font-weight: bold;
        font-size: 16px;
      }
    }
  }
}

.section {
  width: 88%;
  margin-top: 26px;
}

.section + .section {
  margin-top: 100px;
}

.similar-section {
  margin-top: 52px;
}

.section-header {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 10px;
}

.section-box {
  padding: 14px 18px;
  background: rgba(3, 7, 18, 0.7);
  border-radius: 10px;
  box-sizing: border-box;
  /* 让蓝色外框与内部背景之间有明显的留白 */
  margin-top: 4px;
}

.prediction-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.prediction-card {
  background: rgba(0, 0, 0, 0.4);
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(38, 255, 253, 0.35);
}

.prediction-card-header {
          display: flex;
  justify-content: space-between;
          align-items: center;
  margin-bottom: 6px;
}

.prediction-disease {
            font-size: 18px;
  font-weight: bold;
  background: linear-gradient(to right, #26fffd, #00e9ff);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.prediction-confidence {
  font-size: 12px;
  color: #ffe066;

  &.prediction-confidence--unknown {
    color: #9fa6b2;
  }
}

.prediction-card-body {
  font-size: 13px;
}

.prediction-label {
  color: #9fa6ff;
  margin-bottom: 2px;
}

.prediction-advice {
  line-height: 1.6;
}

.similar-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.similar-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(38, 255, 253, 0.7);
    background: rgba(0, 0, 0, 0.65);
  }
}

.similar-item-main {
  .similar-disease {
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 2px;
  }

  .similar-meta {
    font-size: 12px;
    color: #9ca3af;

    span {
      margin-right: 10px;
    }
  }
}

.similar-score {
  font-size: 12px;
  color: #9ca3af;

  .similar-score-value {
    color: #22c55e;
    margin-left: 4px;
  }
}

.case-detail {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed rgba(148, 163, 184, 0.6);
  font-size: 12px;
}

.case-detail-header {
            display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;

  .case-detail-close {
    cursor: pointer;
    font-size: 14px;
  }
}

.case-detail-body {
  .case-row {
    margin-bottom: 2px;

    .case-label {
      color: #9fa6ff;
      margin-right: 4px;
    }
  }
}

.history-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-list {
  /* 提高可见高度，让列表在框内更“铺满”一些 */
  max-height: 160px;
  overflow-y: auto;
  font-size: 12px;
  padding-right: 4px;
  border-radius: 4px;
  background: rgba(15, 23, 42, 0.65);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.35);
}

.history-list::-webkit-scrollbar {
  width: 6px;
}

.history-list::-webkit-scrollbar-track {
  background: transparent;
}

.history-list::-webkit-scrollbar-thumb {
  background: rgba(37, 99, 235, 0.75);
  border-radius: 3px;
}

.history-header,
.history-row {
  display: grid;
  grid-template-columns: 140px 1.4fr 0.9fr 0.6fr 70px;
  column-gap: 6px;
  align-items: center;
}

.history-header {
  margin-bottom: 4px;
  color: #9fa6ff;
}

.history-row {
  padding: 4px 0;
  cursor: pointer;
  border-radius: 4px;

  &:nth-child(odd) {
    background: rgba(15, 23, 42, 0.4);
  }

  &:hover {
    background: rgba(15, 23, 42, 0.7);
  }
}

.history-row--active {
  outline: 1px solid rgba(38, 255, 253, 0.7);
}

.col-desc {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.col-compare {
  .compare-flag {
    font-size: 11px;
    color: #26fffd;
  }
}

.history-compare {
  border-top: 1px dashed rgba(148, 163, 184, 0.6);
  padding-top: 6px;
}

.compare-title {
  font-size: 13px;
  color: #9fa6ff;
  margin-bottom: 4px;
}

.compare-content {
  display: flex;
  gap: 8px;
}

.compare-card {
  flex: 1;
  background: rgba(15, 23, 42, 0.8);
  border-radius: 6px;
  padding: 6px 8px;
  border: 1px solid rgba(38, 255, 253, 0.4);
}

.compare-time {
  font-size: 11px;
  color: #9ca3af;
}

.compare-disease {
  font-size: 14px;
  font-weight: bold;
  margin: 2px 0;
}

.compare-confidence {
  font-size: 12px;
  margin-bottom: 2px;
}

.compare-desc {
  font-size: 12px;
  line-height: 1.5;
}

.empty-text {
  font-size: 12px;
  color: #9ca3af;
  }
</style>
