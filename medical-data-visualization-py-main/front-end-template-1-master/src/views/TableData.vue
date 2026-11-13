<template>
  <div class="tableData-container">
    <transition name="fade" mode="out-in">
      <div class="data-manage-page">
        <!-- 顶部总体统计 -->
        <dv-border-box-10 class="section section-statistics">
          <div class="section-inner">
            <div class="section-title">数据统计</div>
            <div class="stat-cards">
              <div class="stat-card">
                <div class="stat-label">数据总量</div>
                <div class="stat-value">{{ statistics.totalRecords | formatNumber }}</div>
                <div class="stat-desc">当前所有数据源记录总数</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">活跃数据源</div>
                <div class="stat-value">{{ statistics.activeSources }}</div>
                <div class="stat-desc">最近 24 小时内有更新的数据源数量</div>
              </div>
            </div>
          </div>
        </dv-border-box-10>

        <!-- 紧跟其后：数据表格（仅自动滚动，无分页），高度固定，确保边框完全包裹表格 -->
        <dv-border-box-13
          class="section section-table"
          :style="{ height: '520px' }"
        >
          <div class="section-inner section-table-inner">
            <div class="section-title">数据表格</div>
            <div class="section-subtitle">
              详细展示病例记录信息，支持自动滚动浏览
            </div>
            <transition name="fade" mode="out-in">
              <dv-loading v-if="!config.data.length">
                loading
              </dv-loading>
              <div v-else class="table-wrapper">
                <div
                  class="table-scroll-container"
                  ref="tableBody"
                  @scroll="handleTableScroll"
                >
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>序号</th>
                        <th
                          v-for="(header, hIndex) in config.header"
                          :key="hIndex"
                        >
                          {{ header }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(row, rIndex) in scrollData"
                        :key="rIndex"
                      >
                        <td>{{ rIndex + 1 }}</td>
                        <td
                          v-for="(cell, cIndex) in row"
                          :key="cIndex"
                          :class="{ 'table-link-cell': cIndex === 8 }"
                        >
                          {{ cell }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </transition>
          </div>
        </dv-border-box-13>

        <!-- 中间两列：数据源管理 + 导入导出 -->
        <div class="section-row">
          <!-- 1) 数据源管理（分页列表），高度固定，确保边框完整 -->
          <dv-border-box-12
            class="section section-source"
            :style="{ height: '280px' }"
          >
            <div class="section-inner">
              <div class="section-header">
                <div class="section-title">数据源管理</div>
                <div class="section-subtitle">
                  配置各疾病爬虫是否参与数据更新，并支持手动立即爬取；定时调度仍由后台独立进程统一管理
                </div>
              </div>

              <div class="source-table">
                <div class="source-table-header">
                  <div class="col col-index">#</div>
                  <div class="col col-name">数据源名称</div>
                  <div class="col col-type">类型</div>
                  <div class="col col-status">状态</div>
                  <div class="col col-update">最近更新时间</div>
                  <div class="col col-desc">说明</div>
                  <div class="col col-actions">操作</div>
                </div>
                <div
                  v-for="(source, index) in pagedDataSources"
                  :key="source.id"
                  class="source-table-row"
                >
                  <div class="col col-index">
                    {{ (currentPage - 1) * pageSize + index + 1 }}
                  </div>
                  <div class="col col-name">{{ source.name }}</div>
                  <div class="col col-type">{{ source.type }}</div>
                  <div class="col col-status">
                    <span
                      :class="[
                        'status-dot',
                        !source.enabled
                          ? 'error'
                          : (source.status === 'running' || isRunningSource(source))
                          ? 'warning'
                          : 'success',
                      ]"
                    ></span>
                    <span v-if="!source.enabled">已停用</span>
                    <span
                      v-else-if="source.status === 'running' || isRunningSource(source)"
                    >
                      正在运行
                    </span>
                    <span v-else>已启用</span>
                  </div>
                  <div class="col col-update">{{ source.lastUpdate }}</div>
                  <div class="col col-desc">{{ source.desc }}</div>
                  <div class="col col-actions">
                    <button
                      class="btn btn-xs"
                      :class="source.enabled ? 'btn-danger' : 'btn-primary'"
                      @click="toggleSource(source)"
                    >
                      {{ source.enabled ? '停用' : '启用' }}
                    </button>
                    <button
                      class="btn btn-xs btn-primary"
                      :disabled="!source.enabled || source.status === 'running' || isRunningSource(source)"
                      @click="confirmRunSource(source)"
                    >
                      <span v-if="!source.enabled">立即爬取</span>
                      <span
                        v-else-if="source.status === 'running' || isRunningSource(source)"
                      >
                        正在爬取...
                      </span>
                      <span v-else>立即爬取</span>
                    </button>
                  </div>
                </div>
              </div>

              <div class="pagination">
                <button class="btn btn-sm" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">
                  上一页
                </button>
                <span class="page-info">
                  第 {{ currentPage }} / {{ totalPages }} 页，
                  共 {{ dataSources.length }} 条数据源
                </span>
                <span class="page-jump">
                  跳转到
                  <input
                    v-model.number="pageInput"
                    type="number"
                    min="1"
                    :max="totalPages"
                    class="page-input"
                    @keyup.enter="goToPage"
                  />
                  页
                </span>
                <button
                  class="btn btn-sm"
                  :disabled="currentPage === totalPages"
                  @click="changePage(currentPage + 1)"
                >
                  下一页
                </button>
              </div>
            </div>
          </dv-border-box-12>

          <!-- 2) 数据导入导出 -->
          <div class="section-column-right">
            <!-- 数据导入导出，与数据源管理等高 -->
            <dv-border-box-8
              class="section section-import-export"
              :style="{ height: '280px' }"
            >
              <div class="section-inner">
                <div class="section-title">数据导入导出</div>
                <div class="section-subtitle">
                  支持多种格式的数据文件导入与导出，为不同系统间的数据交换提供统一入口
                </div>
                <div class="import-export-content">
                  <div class="import-block">
                    <div class="block-title">数据导入</div>
                    <div class="format-tags">
                      <span class="tag">CSV</span>
                      <span class="tag">Excel</span>
                    </div>
                    <div class="actions">
                      <button class="btn btn-primary btn-sm" @click="triggerImportFile">上传文件导入</button>
                      <button class="btn btn-outline btn-sm" @click="downloadImportTemplate">
                        导入模板下载
                      </button>
                      <input
                        ref="importFile"
                        type="file"
                        accept=".csv,.xls,.xlsx"
                        style="display: none"
                        @change="handleFileChange"
                      />
                    </div>
                  </div>
                  <div class="import-block">
                    <div class="block-title">数据导出</div>
                    <div class="format-tags">
                      <span
                        class="tag clickable"
                        :class="{ active: exportFormat === 'csv' }"
                        @click="exportFormat = 'csv'"
                      >
                        CSV
                      </span>
                      <span
                        class="tag clickable"
                        :class="{ active: exportFormat === 'excel' }"
                        @click="exportFormat = 'excel'"
                      >
                        Excel
                      </span>
                      <span
                        class="tag clickable"
                        :class="{ active: exportFormat === 'json' }"
                        @click="exportFormat = 'json'"
                      >
                        JSON
                      </span>
                    </div>
                    <div class="actions">
                      <button class="btn btn-primary btn-sm" @click="exportData">立即导出</button>
                    </div>
                  </div>
                </div>
              </div>
            </dv-border-box-8>
          </div>
        </div>

        <!-- 下方单独一行：数据版本管理 -->
        <dv-border-box-1 class="section section-version">
          <div class="section-inner">
            <div class="section-title">数据版本管理</div>
            <div class="section-subtitle">
              为关键数据表提供版本控制能力，可回滚到历史版本，保障分析可追溯性
            </div>
            <div class="version-timeline">
              <div
                v-for="version in pagedVersions"
                :key="version.id"
                class="version-item"
              >
                <div class="version-time">{{ version.time }}</div>
                <div class="version-dot"></div>
                <div class="version-content">
                  <div class="version-card">
                    <div class="version-header-row">
                      <div class="version-title">
                        {{ version.name }}（V{{ version.version }}）
                      </div>
                      <button
                        class="btn btn-outline btn-xs"
                        @click="rollbackVersion(version)"
                      >
                        回滚到此版本
                      </button>
                    </div>
                    <div class="version-meta-row">
                      <span>变更人：{{ version.operator }}</span>
                      <span>变更时间：{{ version.time }}</span>
                    </div>
                    <div class="version-desc-row">
                      变更说明：{{ version.desc }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div
              class="version-pagination"
              v-if="versionTotalPages > 1"
            >
              <button
                class="btn btn-xs"
                :disabled="versionPage <= 1"
                @click="changeVersionPage(versionPage - 1)"
              >
                上一页
              </button>
              <span class="page-info">
                {{ versionPage }} / {{ versionTotalPages }}
              </span>
              <button
                class="btn btn-xs"
                :disabled="versionPage >= versionTotalPages"
                @click="changeVersionPage(versionPage + 1)"
              >
                下一页
              </button>
            </div>
          </div>
        </dv-border-box-1>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  data() {
    return {
      // 原有数据表格配置（作为第 7 部分保留）
      config: {
        header: [],
        data: [],
        index: true,
        align: [],
        headerBGC: "#3077b1",
        rowNum: 9,
        waitTime: 3000,
      },
      tableList: [],

      // 表格行对应的真实 cases.id，用于显示准确序号
      rowIds: [],

      // 导出格式选择（默认 CSV）
      exportFormat: "csv",

      // 表格自动滚动控制
      autoScrollTimer: null,
      resumeTimer: null,
      isUserScrolling: false,

      // 1) 数据源管理
      dataSources: [],
      currentPage: 1,
      pageSize: 4,
      pageInput: 1,

      // 5) 数据版本管理
      dataVersions: [],
      versionPage: 1,
      versionPageSize: 5,

      // 6) 数据统计
      statistics: {
        totalRecords: 0,
        todayUpdates: 0,
        activeSources: 0,
      },

      // 手动爬取中的数据源 code 集合，用于前端显示“运行中”状态
      runningSourceCodes: [],
    };
  },
  computed: {
    totalPages() {
      return Math.max(1, Math.ceil(this.dataSources.length / this.pageSize));
    },
    pagedDataSources() {
      const start = (this.currentPage - 1) * this.pageSize;
      return this.dataSources.slice(start, start + this.pageSize);
    },
    versionTotalPages() {
      return Math.max(1, Math.ceil(this.dataVersions.length / this.versionPageSize));
    },
    pagedVersions() {
      const start = (this.versionPage - 1) * this.versionPageSize;
      return this.dataVersions.slice(start, start + this.versionPageSize);
    },
    scrollData() {
      return this.config.data || [];
    },
  },
  async created() {
    await this.delay(1500);
    await Promise.all([
      this.getTableList(),
      this.fetchStatistics(),
      this.fetchDataSources(),
      this.fetchVersions(),
    ]);
  },
  methods: {
    delay(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    },
    async getTableList() {
      const res = await this.$http.get("/tableData");
      this.tableList = res.data.resultData;
      this.rowIds = res.data.ids || [];
      this.config.header = [
        "类型",
        "性别",
        "年龄",
        "时间",
        "描述",
        "求诊医生",
        "求诊医院",
        "类型求诊科室",
        "详情链接",
        "身高",
        "体重",
        "患病时间",
        "过敏史",
      ];
      this.config.data = res.data.resultData || [];
      this.config.align = this.config.header.map(() => "center");
      this.config.align.push("center");
      this.startAutoScroll();
    },
    async fetchStatistics() {
      const res = await this.$http.get("/data/summary");
      if (res && res.data) {
        this.statistics.totalRecords = res.data.totalRecords || 0;
        this.statistics.todayUpdates = res.data.todayUpdates || 0;
        this.statistics.activeSources = res.data.activeSources || 0;
      }
    },
    async fetchDataSources() {
      const res = await this.$http.get("/data/sources");
      this.dataSources = res.data || [];
      this.currentPage = 1;
      this.pageInput = 1;
    },
    async fetchVersions() {
      const res = await this.$http.get("/data/versions");
      this.dataVersions = res.data || [];
      this.versionPage = 1;
    },
    changePage(page) {
      if (page < 1 || page > this.totalPages) return;
      this.currentPage = page;
      this.pageInput = page;
    },
    changeVersionPage(page) {
      if (page < 1 || page > this.versionTotalPages) return;
      this.versionPage = page;
    },
    async toggleSource(source) {
      if (!source || !source.code) return;
      const targetEnabled = !source.enabled;
      try {
        await this.$http.post(`/data/sources/${source.code}/toggle`, {
          enabled: targetEnabled,
        });
        await Promise.all([
          this.fetchDataSources(),
          this.fetchStatistics(),
        ]);
      } catch (e) {
        console.error("切换数据源状态失败", e);
        if (this.$message) {
          this.$message.error("切换数据源状态失败");
        }
      }
    },
    isRunningSource(source) {
      if (!source || !source.code) return false;
      return this.runningSourceCodes.indexOf(source.code) !== -1;
    },
    markSourceRunning(code) {
      if (!code) return;
      if (this.runningSourceCodes.indexOf(code) === -1) {
        this.runningSourceCodes.push(code);
      }
    },
    unmarkSourceRunning(code) {
      if (!code) return;
      const idx = this.runningSourceCodes.indexOf(code);
      if (idx !== -1) {
        this.runningSourceCodes.splice(idx, 1);
      }
    },
    async confirmRunSource(source) {
      if (!source || !source.code) return;

      // 简单确认提示
      const ok = window.confirm(
        `确定要立即启动数据源【${source.name}】的爬虫吗？` +
          "\n\n爬取过程中请勿频繁重复点击，以免造成服务器压力。"
      );
      if (!ok) return;

      await this.runSourceInternal(source);
    },
    async runSourceInternal(source) {
      if (!source || !source.code) return;
      this.markSourceRunning(source.code);
      try {
        if (this.$message) {
          this.$message.info(`已提交任务：开始爬取数据源【${source.name}】...`);
        }

        const res = await this.$http.post(
          `/data/sources/${source.code}/run`,
          { pages: 3 },
          { timeout: 0 }
        );

        // 兼容两种返回结构：
        // 1) 包装形式 { message, code, data: { success, delta, error } }
        // 2) 直接返回 data 对象 { success, delta, error }
        const raw = (res && res.data) || {};
        let wrapper = { code: 200, message: "", data: raw };
        let inner = raw;

        if (
          raw &&
          typeof raw === "object" &&
          Object.prototype.hasOwnProperty.call(raw, "data") &&
          (Object.prototype.hasOwnProperty.call(raw, "code") ||
            Object.prototype.hasOwnProperty.call(raw, "message"))
        ) {
          // 后端包装形式
          wrapper = {
            code: raw.code,
            message: raw.message,
            data: raw.data,
          };
          inner = raw.data || {};
        }

        const delta = (inner && inner.delta) || 0;
        const errorText = (inner && inner.error) || "";
        const ok = (!wrapper.code || wrapper.code === 200) && !errorText;

        if (this.$message) {
          if (ok) {
            this.$message.success(
              delta
                ? `爬虫执行完成，本次新增 ${delta} 条记录`
                : "爬虫执行完成，本次未发现新增记录"
            );
          } else {
            this.$message.error(errorText || wrapper.message || "爬虫执行失败，请稍后重试");
          }
        }

        // 爬虫完成后，刷新统计、数据表和数据源状态、版本信息，确保前端数据及时更新
        await Promise.all([
          this.fetchStatistics(),
          this.getTableList(),
          this.fetchDataSources(),
          this.fetchVersions(),
        ]);
      } catch (e) {
        console.error("手动执行爬虫失败", e);
        if (this.$message) {
          const isTimeout =
            e &&
            (e.code === "ECONNABORTED" ||
              (e.message && e.message.toString().toLowerCase().includes("timeout")));
          const msg = isTimeout
            ? "请求超时，爬虫可能仍在后台运行，请稍后在数据源列表中查看状态"
            : (e.response &&
                e.response.data &&
                e.response.data.data &&
                e.response.data.data.error) || "爬虫执行失败，请检查后端服务";
          this.$message.error(msg);
        }
      } finally {
        this.unmarkSourceRunning(source.code);
      }
    },
    async rollbackVersion(version) {
      if (!version || !version.id) return;
      try {
        await this.$http.post(`/data/versions/${version.id}/rollback`);
        if (this.$message) {
          this.$message.success("回滚成功，数据已恢复到选定版本");
        }
        await this.fetchStatistics();
        await this.getTableList();
        await this.fetchVersions();
      } catch (e) {
        console.error("回滚版本失败", e);
        if (this.$message) {
          const msg =
            (e.response && e.response.data && e.response.data.data && e.response.data.data.error) ||
            "回滚失败，请检查后端日志";
          this.$message.error(msg);
        }
      }
    },
    goToPage() {
      let target = Number(this.pageInput);
      if (!target || target < 1) target = 1;
      if (target > this.totalPages) target = this.totalPages;
      this.currentPage = target;
      this.pageInput = target;
    },
    triggerImportFile() {
      if (this.$refs.importFile) {
        this.$refs.importFile.value = "";
        this.$refs.importFile.click();
      }
    },
    async handleFileChange(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await this.$http.post("/data/import", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        if (this.$message) {
          this.$message.success(
            `导入成功，本次新增 ${
              (res.data && res.data.inserted) || 0
            } 条记录`
          );
        }
        await this.fetchStatistics();
        await this.getTableList();
        await this.fetchVersions();
      } catch (e) {
        console.error("导入数据失败", e);
        if (this.$message) {
          const msg =
            (e.response &&
              e.response.data &&
              e.response.data.data &&
              e.response.data.data.error) || "导入失败，请检查文件格式";
          this.$message.error(msg);
        }
      } finally {
        if (this.$refs.importFile) {
          this.$refs.importFile.value = "";
        }
      }
    },
    async downloadImportTemplate() {
      try {
        const res = await this.$http.get("/data/import/template", {
          responseType: "blob",
        });
        const blob = new Blob([res], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "cases_import_template.xlsx";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } catch (e) {
        console.error("下载导入模板失败", e);
        if (this.$message) {
          this.$message.error("下载导入模板失败");
        }
      }
    },
    async exportData() {
      try {
        const format = this.exportFormat || "excel";
        const res = await this.$http.get("/data/export", {
          params: { format },
          responseType: "blob",
        });

        let mimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
        let filename = "cases_export.xlsx";
        if (format === "csv") {
          mimeType = "text/csv;charset=utf-8";
          filename = "cases_export.csv";
        } else if (format === "json") {
          mimeType = "application/json;charset=utf-8";
          filename = "cases_export.json";
        }

        const blob = new Blob([res], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } catch (e) {
        console.error("导出数据失败", e);
        if (this.$message) {
          this.$message.error("导出数据失败");
        }
      }
    },
    startAutoScroll() {
      // 每次调用都重启自动滚动，确保在数据更新后仍然生效
      if (this.autoScrollTimer) {
        clearInterval(this.autoScrollTimer);
        this.autoScrollTimer = null;
      }

      const tryStart = () => {
        const container = this.$refs.tableBody;
        if (!container) {
          // DOM 还未渲染完成，稍后重试
          setTimeout(tryStart, 300);
          return;
        }

        if (!this.config.data || !this.config.data.length) {
          return;
        }

        // 按行滚动：每隔固定时间跳一整行，形成逐行翻页效果
        const firstRow = container.querySelector('tbody tr');
        if (!firstRow) return;
        const rowHeight = firstRow.offsetHeight || 0;
        if (!rowHeight) return;

        const maxScroll = container.scrollHeight - container.clientHeight;
        if (maxScroll <= 0) return;

        const interval = 1500; // 每 1.5 秒跳一行

        this.autoScrollTimer = setInterval(() => {
          if (this.isUserScrolling) return;

          const maxIndex = Math.floor(maxScroll / rowHeight) || 0;
          // 根据当前 scrollTop 计算所在行号，确保在手动滚动后从当前位置继续
          let currentIndex = Math.round(container.scrollTop / rowHeight);
          if (currentIndex >= maxIndex) {
            currentIndex = 0;
          } else {
            currentIndex += 1;
          }

          container.scrollTop = currentIndex * rowHeight;
        }, interval);
      };

      this.$nextTick(tryStart);
    },
    handleTableScroll() {
      this.isUserScrolling = true;
      if (this.resumeTimer) {
        clearTimeout(this.resumeTimer);
      }
      this.resumeTimer = setTimeout(() => {
        this.isUserScrolling = false;
      }, 3000);
    },
  },
  beforeDestroy() {
    if (this.autoScrollTimer) {
      clearInterval(this.autoScrollTimer);
      this.autoScrollTimer = null;
    }
    if (this.resumeTimer) {
      clearTimeout(this.resumeTimer);
      this.resumeTimer = null;
    }
  },
  filters: {
    formatNumber(value) {
      if (!value && value !== 0) return "";
      return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },
  },
};
</script>

<style scoped>
.tableData-container {
  width: 100%;
  color: #ffffff;
}

.data-manage-page {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding-bottom: 20px;
}

.section {
  padding: 8px;
}

.section-inner {
  padding: 10px 15px;
}

.section-title {
  color: #3f96a5;
  font-size: 18px;
  font-weight: bold;
  text-align: left;
  margin-bottom: 6px;
}

.section-subtitle {
  font-size: 12px;
  color: #b2c6de;
  margin-bottom: 10px;
}

.section-row {
  display: flex;
  gap: 15px;
}

.section-column-right,
.section-column-left {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.section-statistics .stat-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-card {
  background: rgba(9, 26, 53, 0.8);
  border: 1px solid rgba(70, 148, 230, 0.5);
  border-radius: 6px;
  padding: 10px 12px;
}

.stat-label {
  font-size: 13px;
  color: #9fb6d8;
}

.stat-value {
  font-size: 20px;
  font-weight: bold;
  margin: 6px 0;
  color: #ffffff;
}

.stat-desc {
  font-size: 11px;
  color: #6c819c;
}

.section-source {
  flex: 2;
}

.source-table {
  margin-top: 8px;
  border-radius: 4px;
  overflow: hidden;
}

.source-table-header,
.source-table-row {
  display: grid;
  grid-template-columns: 40px 130px 90px 90px 150px auto 160px;
  align-items: center;
  padding: 7px 10px;
  font-size: 12px;
}

.source-table-header {
  background: rgba(21, 61, 116, 0.9);
  font-weight: bold;
}

.source-table-row {
  background: rgba(7, 24, 49, 0.9);
  border-top: 1px solid rgba(34, 74, 129, 0.8);
}

.source-table-row:nth-child(2n) {
  background: rgba(10, 32, 63, 0.9);
}

.col {
  padding: 0 4px;
}

.col-desc {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
}

.status-dot.success {
  background: #4caf50;
}

.status-dot.warning {
  background: #ff9800;
}

.status-dot.error {
  background: #f44336;
}

.pagination {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  font-size: 12px;
  color: #b2c6de;
}

.page-info {
  white-space: nowrap;
}

.page-jump {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.page-input {
  width: 52px;
  padding: 3px 6px;
  border-radius: 12px;
  border: 1px solid #3f96a5;
  background: transparent;
  color: #ffffff;
  text-align: center;
}

.btn {
  border-radius: 20px;
  border: 1px solid transparent;
  background: #1b2d4a;
  color: #52a2e4;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:hover {
  background: #23406a;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-xs {
  font-size: 11px;
  padding: 3px 10px;
}

.btn-sm {
  font-size: 12px;
  padding: 5px 14px;
}

.btn-primary {
  background: #1c6fe9;
  color: #ffffff;
}

.btn-primary:hover {
  background: #2680ff;
}

.btn-danger {
  background: #e53935;
  color: #ffffff;
}

.btn-danger:hover {
  background: #f45151;
}

.btn-outline {
  background: transparent;
  border-color: #52a2e4;
}

.btn-outline:hover {
  background: rgba(82, 162, 228, 0.2);
}

.import-export-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.import-block {
  background: rgba(7, 24, 49, 0.9);
  border-radius: 4px;
  padding: 8px 10px;
}

.block-title {
  font-size: 14px;
  margin-bottom: 6px;
}

.format-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 6px;
}

.tag {
  padding: 2px 8px;
  border-radius: 12px;
  border: 1px solid #3f96a5;
  font-size: 11px;
}

.tag.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
}

.tag.clickable:hover {
  border-color: #52a2e4;
  box-shadow: 0 0 6px rgba(82, 162, 228, 0.6);
}

.tag.clickable.active {
  background: #52a2e4;
  color: #051231;
  border-color: #52a2e4;
  box-shadow: 0 0 8px rgba(82, 162, 228, 0.9);
}

.actions {
  display: flex;
  gap: 8px;
}
.inline {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.sync-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sync-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(7, 24, 49, 0.9);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 12px;
}

.sync-name {
  font-weight: bold;
  margin-bottom: 4px;
}

.sync-meta span {
  margin-right: 10px;
  color: #9fb6d8;
}

.sync-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.version-timeline {
  margin-top: 8px;
  border-left: 1px solid rgba(63, 150, 165, 0.5);
  padding-left: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.version-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
}

.version-time {
  font-size: 11px;
  color: #9fb6d8;
  min-width: 110px;
}

.version-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3f96a5;
  margin-top: 4px;
}

.version-content {
  flex: 1;
}

.version-title {
  font-weight: bold;
  margin-bottom: 4px;
}

.version-meta span {
  display: block;
  color: #9fb6d8;
}

.version-card {
  background: rgba(7, 24, 49, 0.9);
  border-radius: 4px;
  padding: 8px 10px;
}

.version-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.version-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #9fb6d8;
  margin-bottom: 4px;
}

.version-desc-row {
  font-size: 12px;
  color: #9fb6d8;
}

.section-version {
  padding-top: 12px;
  padding-bottom: 14px;
}

.section-version .section-inner {
  padding-top: 18px;
  padding-bottom: 16px;
}

.section-table-inner {
  padding-top: 16px;
  padding-bottom: 16px;
}

.section-table {
  padding-top: 10px;
  padding-bottom: 10px;
}

.section-table .table-wrapper {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

.table-scroll-container {
  width: 100%;
  max-height: 420px;
  overflow-y: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: fixed;
}

.data-table thead tr {
  background: rgba(21, 61, 116, 0.9);
}

.data-table th,
.data-table td {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(34, 74, 129, 0.8);
  text-align: center;
  color: #ffffff;
}

.data-table td.table-link-cell {
  /* 详情链接列：允许长 URL 在单元格内自动换行，避免挤占其他列 */
  word-break: break-all;
  overflow-wrap: break-word;
  text-align: left;
}

.data-table tbody tr:nth-child(2n) {
  background: rgba(10, 32, 63, 0.9);
}

.data-table tbody tr:nth-child(2n + 1) {
  background: rgba(7, 24, 49, 0.9);
}

.table-pagination {
  margin-top: 10px;
}

.modal-mask {
  position: fixed;
  z-index: 999;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.65);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-wrapper {
  width: 60%;
  max-width: 800px;
}

.modal-container {
  background: rgba(5, 18, 49, 0.96);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px 0 15px;
}

.modal-title {
  font-size: 16px;
  font-weight: bold;
  color: #3f96a5;
}

.modal-close {
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
}

.modal-body {
  padding: 10px 15px 15px 15px;
  font-size: 12px;
}

.import-history-header,
.import-history-item {
  display: grid;
  grid-template-columns: 30% 50% 20%;
  gap: 6px;
  align-items: center;
}

.import-history-header {
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(63, 150, 165, 0.6);
  color: #9fb6d8;
}

.import-history-list {
  max-height: 260px;
  overflow-y: auto;
  margin-top: 6px;
  scrollbar-width: none;
}

.import-history-list::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.import-history-item {
  padding: 6px 0;
  border-bottom: 1px dashed rgba(63, 150, 165, 0.3);
}

.import-history-empty {
  padding: 15px 0;
  text-align: center;
  color: #9fb6d8;
}

.ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-status {
  padding: 2px 8px;
  border-radius: 12px;
  text-align: center;
}

.history-status.success {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.history-status.warning {
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.history-status.error {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.modal-footer {
  padding: 0 15px 12px 15px;
  text-align: right;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}

.fade-enter,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 1400px) {
  .section-statistics .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .source-table-header,
  .source-table-row {
    grid-template-columns: 30px 110px 80px 80px 130px auto 150px;
  }
}
</style>