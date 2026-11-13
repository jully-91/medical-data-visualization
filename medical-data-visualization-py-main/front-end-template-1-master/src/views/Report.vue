<template>
  <div class="report-container">
    <!-- 将外层边框由 10 改为 13，减少底部高光带来的“露白”感 -->
    <dv-border-box-13 class="report-wrapper">
      <div class="report-header">
        <div class="tabs">
          <div
            :class="['tab-item', activeTab === 'generate' ? 'active' : '']"
            @click="activeTab = 'generate'"
          >
            报告生成
          </div>
          <div
            :class="['tab-item', activeTab === 'template' ? 'active' : '']"
            @click="activeTab = 'template'"
          >
            报告模板管理
          </div>
        </div>
        <button
          v-if="activeTab === 'template'"
          class="help-btn"
          @click="showHelp = true"
        >
          操作与数据源说明
        </button>
      </div>

      <!-- 报告生成：三步向导 + 预览 -->
      <div v-if="activeTab === 'generate'" class="report-content">
        <!-- 左侧：步骤条 + 表单 -->
        <div class="left-panel">
          <div class="step-header">
            <div
              v-for="s in steps"
              :key="s.id"
              :class="[
                'step-item',
                currentStep === s.id ? 'active' : '',
                currentStep > s.id ? 'done' : '',
              ]"
              @click="goStep(s.id)"
            >
              <span class="step-index">{{ s.id }}</span>
              <span class="step-label">{{ s.label }}</span>
            </div>
          </div>

          <!-- 第一步：选择模板 -->
          <div v-if="currentStep === 1" class="step-body">
            <div class="panel-title">第一步：选择模板</div>
            <div class="form-group">
              <label>模板类型</label>
              <select v-model="generateForm.filterType">
                <option value="">全部类型</option>
                <option v-for="t in templateTypes" :key="t" :value="t">
                  {{ t }}
                </option>
              </select>
            </div>
            <div class="template-select-list">
              <div
                v-for="tpl in filteredPublishedTemplates"
                :key="tpl.id"
                :class="[
                  'tpl-card',
                  generateForm.templateId === tpl.id ? 'selected' : '',
                ]"
                @click="selectTemplate(tpl)"
              >
                <div class="tpl-title">
                  {{ tpl.name }}
                  <span class="tpl-type">{{ tpl.type }}</span>
                </div>
                <div class="tpl-scene">{{ tpl.scene }}</div>
                <div class="tpl-meta">
                  <span>版本：{{ tpl.version }}</span>
                  <span>更新时间：{{ tpl.updatedAt }}</span>
                </div>
              </div>
              <div v-if="!filteredPublishedTemplates.length" class="empty-tip">
                暂无已发布模板，请先在“报告模板管理”中创建并发布模板。
              </div>
            </div>
          </div>

          <!-- 第二步：配置参数 -->
          <div v-if="currentStep === 2" class="step-body">
            <div class="panel-title">第二步：配置报告参数</div>
            <div class="form-group">
              <label>报告名称</label>
              <input
                v-model="generateForm.title"
                type="text"
                placeholder="如：2025-01 高血压病例统计报告"
              />
            </div>
            <div class="form-group">
              <label>时间范围</label>
              <div class="quick-range">
                <span
                  v-for="item in quickRanges"
                  :key="item.value"
                  :class="[
                    'range-chip',
                    generateForm.quickRange === item.value ? 'active' : '',
                  ]"
                  @click="setQuickRange(item.value)"
                >
                  {{ item.label }}
                </span>
              </div>
              <div class="inline-inputs" style="margin-top: 8px">
                <input v-model="generateForm.startDate" type="date" />
                <span class="split">至</span>
                <input v-model="generateForm.endDate" type="date" />
              </div>
            </div>

            <div class="form-group">
              <label>患者筛选条件（可选）</label>
              <div class="inline-inputs">
                <select v-model="generateForm.caseFilter.disease">
                  <option value="">全部疾病</option>
                  <option v-for="d in diseaseTypes" :key="d" :value="d">
                    {{ d }}
                  </option>
                </select>
                <select v-model="generateForm.caseFilter.gender">
                  <option value="">全部性别</option>
                  <option value="男">男</option>
                  <option value="女">女</option>
                </select>
                <select v-model="generateForm.caseFilter.hospital">
                  <option value="">全部医院</option>
                  <option v-for="h in hospitals" :key="h" :value="h">
                    {{ h }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group" v-if="hasChartBlock">
              <label>图表维度（作用于当前模板的图表模块）</label>
              <div class="checkbox-row">
                <label>
                  <input
                    type="checkbox"
                    v-model="generateForm.dimensions"
                    value="age"
                  />
                  按年龄分组
                </label>
                <label>
                  <input
                    type="checkbox"
                    v-model="generateForm.dimensions"
                    value="gender"
                  />
                  按性别分组
                </label>
                <label>
                  <input
                    type="checkbox"
                    v-model="generateForm.dimensions"
                    value="department"
                  />
                  按科室分组
                </label>
              </div>
              <p class="field-tip">
                说明：仅当所选模板包含「图表模块」时生效，这里的选项会决定导出的 PDF / Word 报告中图表的统计维度（年龄、性别、科室）。
              </p>
            </div>

            <div class="mini-preview">
              <div class="mini-title">参数预览</div>
              <p>时间：{{ generateForm.startDate || '未选' }} 至
                {{ generateForm.endDate || '未选' }}</p>
              <p>
                筛选：
                {{ generateForm.caseFilter.disease || '全部疾病' }} /
                {{ generateForm.caseFilter.gender || '全部性别' }} /
                {{ generateForm.caseFilter.hospital || '全部医院' }}
              </p>
              <p>
                维度：
                {{ generateForm.dimensions.length ? generateForm.dimensions.join('、') : '未选择' }}
              </p>
            </div>
          </div>

          <!-- 第三步：确认生成 -->
          <div v-if="currentStep === 3" class="step-body">
            <div class="panel-title">第三步：确认生成 & 导出设置</div>
            <div class="summary-block">
              <div class="summary-row">
                <span>报告名称：</span>
                <span>{{ generateForm.title || '未填写' }}</span>
              </div>
              <div class="summary-row">
                <span>模板：</span>
                <span>{{ currentTemplateName || '未选择' }}</span>
              </div>
              <div class="summary-row">
                <span>时间范围：</span>
                <span>
                  {{ generateForm.startDate || '未选' }} 至
                  {{ generateForm.endDate || '未选' }}
                </span>
              </div>
            </div>

            <div class="form-group">
              <label>导出格式</label>
              <div class="checkbox-row">
                <label v-for="fmt in exportFormats" :key="fmt.value">
                  <input
                    type="radio"
                    name="exportFormat"
                    :value="fmt.value"
                    v-model="generateForm.exportFormat"
                  />
                  {{ fmt.label }}
                </label>
              </div>
            </div>

            <div class="form-group">
              <label>是否调用大模型生成诊断文字</label>
              <div class="checkbox-row">
                <label>
                  <input
                    type="checkbox"
                    v-model="generateForm.useLLM"
                  />
                  使用 DeepSeek 智能生成“诊断结论 & 解释说明”（基于真实统计结果）
                </label>
              </div>
            </div>

            <div class="form-actions">
              <button
                class="btn primary"
                :disabled="generating"
                @click="handleGenerateReport"
              >
                {{ generating ? '正在生成...' : '生成报告并预览' }}
              </button>
              <button class="btn ghost" @click="resetAll">
                重置向导
              </button>
            </div>
          </div>

          <div class="step-footer">
            <button
              class="btn ghost"
              :disabled="currentStep === 1"
              @click="prevStep"
            >
              上一步
            </button>
            <button
              class="btn primary"
              v-if="currentStep < 3"
              :disabled="!canNext"
              @click="nextStep"
            >
              下一步
            </button>
          </div>
        </div>

        <!-- 右侧：报告预览 / 导出 -->
        <div class="right-panel">
          <div class="panel-title">报告预览</div>
          <dv-border-box-12 class="preview-box">
            <div v-if="!previewSections.length" class="preview-placeholder">
              请选择模板并完成参数配置后，点击“生成报告并预览”，这里会展示完整报告。
            </div>
            <div v-else class="preview-scroll">
              <div
                v-for="(sec, idx) in previewSections"
                :key="sec.id"
                class="preview-section"
              >
                <div class="section-header">
                  <span class="sec-index">第 {{ idx + 1 }} 节</span>
                  <span class="sec-title">{{ sec.title }}</span>
                  <span class="sec-type-tag">{{ sec.typeLabel }}</span>
                </div>
                <!-- 文本模块，可临时编辑 -->
                <div
                  v-if="sec.type === 'text'"
                  class="sec-body"
                >
                  <textarea
                    v-model="sec.runtimeContent"
                    rows="4"
                  ></textarea>
                </div>
                <!-- 统计摘要模块：关键指标 -->
                <div v-else-if="sec.type === 'kpi'" class="sec-body kpi-grid">
                  <div
                    v-for="k in sec.runtimeKpi"
                    :key="k.key"
                    class="kpi-card"
                  >
                    <div class="kpi-label">{{ k.label }}</div>
                    <div class="kpi-value">{{ k.value }}</div>
                    <div class="kpi-desc">{{ k.desc }}</div>
                  </div>
                </div>
                <!-- 表格模块：病例列表摘要 -->
                <div v-else-if="sec.type === 'table'" class="sec-body">
                  <table class="preview-table">
                    <thead>
                      <tr>
                        <th v-for="h in sec.runtimeHeader" :key="h">
                          {{ h }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, rIdx) in sec.runtimeRows" :key="rIdx">
                        <td v-for="(cell, cIdx) in row" :key="cIdx">
                          {{ cell }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <div class="table-tip">
                    仅展示前 {{ sec.runtimeRows.length }} 行，完整数据可在导出的 Excel 中查看。
                  </div>
                </div>
                <!-- 图表模块：这里以占位说明为主，实际图表可复用首页 ECharts 组件 -->
                <div v-else-if="sec.type === 'chart'" class="sec-body chart-placeholder">
                  <p>图表占位：{{ sec.chartDesc }}</p>
                  <p class="chart-sub">
                    生成 PDF / 大屏展示时，将根据模板中配置的图表类型与数据源（如
                    “疾病类型饼图”“年龄分布柱状图”）渲染真实图表。
                  </p>
                </div>
              </div>

              <div class="export-actions">
                <button class="btn primary" @click="exportReport">
                  导出（{{ exportLabel }}）
                </button>
                <button class="btn ghost" @click="scrollTop">
                  回到顶部
                </button>
              </div>
            </div>
          </dv-border-box-12>
        </div>
      </div>

      <!-- 模板管理：模板库 + 简易“拖拽”编辑器 + 版本记录 -->
      <div v-if="activeTab !== 'generate'" class="report-content">
        <div class="template-left">
          <div class="panel-title">模板库</div>
          <div class="form-group">
            <label>搜索模板</label>
            <input
              v-model="templateQuery.keyword"
              type="text"
              placeholder="按名称 / 场景搜索"
            />
          </div>
          <div class="form-group">
            <label>模板类型</label>
            <select v-model="templateQuery.type">
              <option value="">全部类型</option>
              <option v-for="t in templateTypes" :key="t" :value="t">
                {{ t }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>状态</label>
            <select v-model="templateQuery.status">
              <option value="">全部状态</option>
              <option value="draft">草稿</option>
              <option value="published">已发布</option>
              <option value="offline">已下架</option>
            </select>
          </div>
          <div class="template-toolbar">
            <button class="btn primary" @click="createTemplate">
              新建模板
            </button>
          </div>

          <div class="template-list">
            <div
              v-for="tpl in filteredTemplates"
              :key="tpl.id"
              :class="[
                'tpl-item',
                currentTemplate && currentTemplate.id === tpl.id ? 'active' : '',
              ]"
              @click="selectTemplateForEdit(tpl)"
            >
              <div class="tpl-main">
                <div class="tpl-name">{{ tpl.name }}</div>
                <div class="tpl-scene">{{ tpl.scene }}</div>
              </div>
              <div class="tpl-meta-row">
                <span class="tag">{{ tpl.type }}</span>
                <span class="tag" :class="['status', tpl.status]">
                  {{ statusMap[tpl.status] }}
                </span>
                <span class="version">V{{ tpl.version }}</span>
              </div>
            </div>
            <div v-if="!filteredTemplates.length" class="empty-tip">
              暂无符合条件的模板，可点击“新建模板”创建。
            </div>
          </div>
        </div>

        <!-- 右侧：模板编辑器 -->
        <div class="template-right" v-if="currentTemplate">
          <div class="panel-title">
            模板编辑：{{ currentTemplate.name }}
          </div>
          <div class="editor-helper">
            操作说明：1）左侧选择或新建模板；2）在右侧“可用模块”中点击添加需要的模块；
            3）通过“上移 / 下移 / 删除”调整顺序；4）填好说明文字和字段后点击“保存为新版本”，再点击“发布模板”即可在“报告生成”中使用。
          </div>

          <!-- 可滚动编辑区域，避免内容过长时撑出页面 -->
          <div class="template-scroll">
            <div class="form-group">
              <label>模板名称</label>
              <input v-model="currentTemplate.name" type="text" />
            </div>

            <div class="form-group">
              <label>适用场景</label>
              <input
                v-model="currentTemplate.scene"
                type="text"
                placeholder="例如：用于某疾病月度统计，适合管理层查看"
              />
            </div>

            <div class="form-group">
              <label>模板类型</label>
              <select v-model="currentTemplate.type">
                <option v-for="t in templateTypes" :key="t" :value="t">
                  {{ t }}
                </option>
              </select>
            </div>

            <!-- 可选模块“组件库” -->
            <div class="editor-layout">
            <div class="editor-palette">
              <div class="palette-title">可用模块</div>
              <div
                v-for="b in blockPalette"
                :key="b.type"
                class="palette-item"
                @click="addBlock(b.type)"
              >
                <div class="p-name">{{ b.label }}</div>
                <div class="p-desc">{{ b.desc }}</div>
              </div>
            </div>

            <!-- 模板已选模块 + 顺序调整 -->
            <div class="editor-canvas">
              <div class="canvas-header">
                已选模块（可调整先后顺序）
              </div>
              <div
                v-for="(blk, idx) in currentTemplate.blocks"
                :key="blk.id"
                class="canvas-block"
              >
                <div class="cb-header">
                  <span>{{ idx + 1 }}. {{ blockTypeMap[blk.type] }}</span>
                  <div class="cb-actions">
                    <button
                      class="mini-btn"
                      :disabled="idx === 0"
                      @click="moveBlock(idx, -1)"
                    >
                      上移
                    </button>
                    <button
                      class="mini-btn"
                      :disabled="idx === currentTemplate.blocks.length - 1"
                      @click="moveBlock(idx, 1)"
                    >
                      下移
                    </button>
                    <button class="mini-btn danger" @click="removeBlock(idx)">
                      删除
                    </button>
                  </div>
                </div>
                <div class="cb-body">
                  <!-- 针对不同类型展示关键配置项 -->
                  <div v-if="blk.type === 'text'">
                    <label>固定说明文本 / 变量占位</label>
                    <textarea
                      v-model="blk.config.template"
                      rows="3"
                      placeholder="例如：报告说明……可使用 startDate / endDate / disease 等占位符"
                    ></textarea>
                  </div>
                  <div v-else-if="blk.type === 'kpi'">
                    <label>指标配置（示例）</label>
                    <input
                      v-model="blk.config.source"
                      type="text"
                      placeholder="一般保持默认：使用首页 /getHomeData 统计结果"
                    />
                    <p class="field-tip">
                      说明：关键指标模块会自动根据病例库和当前筛选条件计算“病例总数、平均年龄、最多疾病类型”等，
                      这里只是标记统计数据来自哪里，通常不需要修改。
                    </p>
                  </div>
                  <div v-else-if="blk.type === 'table'">
                    <label>数据源</label>
                    <input
                      v-model="blk.config.source"
                      type="text"
                      placeholder="默认：病例表 medicalinfo.cases"
                    />
                    <label>展示字段（逗号分隔）</label>
                    <input
                      v-model="blk.config.fields"
                      type="text"
                      placeholder="例如：type,gender,age,time,docHospital"
                    />
                  </div>
                  <div v-else-if="blk.type === 'chart'">
                    <label>图表说明</label>
                    <input
                      v-model="blk.config.desc"
                      type="text"
                      placeholder="对图表含义的简短说明（例如：本报告将展示年龄/性别/科室的病例分布情况）"
                    />
                  </div>
                </div>
              </div>
              <div
                v-if="!currentTemplate.blocks.length"
                class="empty-tip"
                style="margin-top: 10px"
              >
                尚未添加模块，可从左侧“可用模块”中点击添加。
              </div>
            </div>

            <!-- 结束 editor-layout 左右布局 -->
            </div>

            <!-- 版本记录（前端模拟） -->
            <div class="version-panel">
              <div class="version-title">版本记录</div>
              <div
                v-for="ver in currentTemplate.versions"
                :key="ver.id"
                class="version-item"
              >
                <div>
                  <span class="v-code">{{ ver.code }}</span>
                  <span class="v-time">{{ ver.time }}</span>
                </div>
                <div class="v-desc">{{ ver.desc }}</div>
              </div>
            </div>
          </div>

          <div class="template-actions">
            <button class="btn primary" @click="saveTemplate">
              保存为新版本
            </button>
            <button
              class="btn ghost"
              :disabled="currentTemplate.status === 'published'"
              @click="publishTemplate"
            >
              发布模板
            </button>
            <button
              class="btn ghost"
              :disabled="currentTemplate.status !== 'published'"
              @click="offlineTemplate"
            >
              下架模板
            </button>
            <button class="btn ghost" @click="deleteTemplate">
              删除模板
            </button>
          </div>
        </div>

        <div v-if="!currentTemplate" class="template-right empty-tip">
          请选择左侧模板，或点击“新建模板”开始配置。
        </div>
      </div>
    </dv-border-box-13>

    <!-- 操作 / 数据源说明弹窗 -->
    <div v-if="showHelp" class="help-mask" @click.self="showHelp = false">
      <div class="help-dialog">
        <div class="help-header">
          <span>报告模板使用与数据源说明</span>
          <button class="help-close" @click="showHelp = false">×</button>
        </div>
        <div class="help-body">
          <p>
            本系统所有报告都基于同一份病例库 <strong>medicalinfo.cases</strong> 与既有接口生成，
            模板管理只负责配置“展示哪些字段、以什么形式展示”，不会修改或新增底层数据。
          </p>
          <p><strong>1）文本说明模块</strong></p>
          <ul>
            <li>不直接访问数据库，用于填写“报告概述、诊断结论”等说明文字。</li>
            <li>
              支持变量：<code>'“{ { startDate } }”（报告统计起始日期）'</code>、
              <code>'“{ { endDate } }”（报告统计结束日期）'</code>、
              <code>'“{ { disease } }”（筛选的疾病类型）'</code>、
              <code>'“{ { gender} }”（筛选的性别）'</code>、
              <code>'“{ { hospital } }”（筛选的医院）'</code>、
              <code>'“{ { total_cases } }”（当前筛选条件下的病例总数）'</code>、
              <code>'“{ { top_disease } }”（出现次数最多的疾病类型）'</code>、
              <code>'“{ { llm_summary } }”（DeepSeek生成的智能诊断文字）'</code>；
              生成报告时由后端 <code>/reports/generate</code> 自动替换为真实值。
            </li>
          </ul>
          <p><strong>2）关键指标模块（KPI）</strong></p>
          <ul>
            <li>基础数据来自病例表 <code>medicalinfo.cases</code>，部分全局统计可参考首页接口 <code>/getHomeData</code>。</li>
            <li>典型指标：病例总数、平均年龄、最多疾病类型等，均按当前筛选条件在后端自动计算。</li>
            <li>“指标配置”一般保持默认即可，表示本模块从哪里读取统计结果（如：使用首页统计接口的数据）。</li>
          </ul>
          <p><strong>3）图表模块</strong></p>
          <ul>
            <li>所有图表都基于 <code>medicalinfo.cases</code>，并自动应用当前的筛选条件。</li>
            <li>年龄分布柱状图：统计 <code>age</code> 字段；疾病类型饼图：统计 <code>type</code> 字段；科室接诊量环形图：统计 <code>department</code> 字段。</li>
          </ul>
          <p><strong>4）病例表格模块</strong></p>
          <ul>
            <li><code>数据源 = cases</code> 表示使用病例表 <code>medicalinfo.cases</code>（等价于 <code>/tableData</code> 返回数据）。</li>
            <li>
              “展示字段”请填写该表中的字段名，多个字段用英文逗号分隔，例如：
              <code>type,gender,age,time,docHospital,department</code>。
            </li>
          </ul>
          <p>
            若不确定字段含义或示例，可以先到“数据表格”页面查看表头与样例数据，再回到此处配置模板。
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import templateMocks from "@/mock/reportTemplates";

export default {
  name: "Report",
  data() {
    return {
      activeTab: "generate",
      // 步骤配置
      steps: [
        { id: 1, label: "选择模板" },
        { id: 2, label: "配置参数" },
        { id: 3, label: "确认生成" },
      ],
      currentStep: 1,
      generating: false,
      showHelp: false,
      // 模板库数据
      // 默认先使用前端 mock 数据；后端接入后由 /templates 接口返回替换
      templates: [],
      // 模板筛选
      templateQuery: {
        keyword: "",
        type: "",
        status: "",
      },
  watch: {
    "generateForm.templateId"() {
      // 如果当前模板不包含图表模块，则清空维度选择，避免误导
      const tpl = this.templates.find((t) => t.id === this.generateForm.templateId);
      if (!tpl || !tpl.blocks || !tpl.blocks.some((b) => b.type === "chart")) {
        this.generateForm.dimensions = [];
      }
    },
  },
      // 正在编辑/预览的模板
      currentTemplate: null,
      // 报告生成表单
      generateForm: {
        templateId: "",
        filterType: "",
        title: "",
        startDate: "",
        endDate: "",
        quickRange: "",
        caseFilter: {
          disease: "",
          gender: "",
          hospital: "",
        },
        dimensions: [],
        exportFormat: "pdf",
        useLLM: true,
      },
      // 报告预览的节结构
      previewSections: [],
      // 供选择的枚举（当前仅支持统计类模板）
      templateTypes: ["统计类"],
      quickRanges: [
        { value: "7d", label: "近 7 天" },
        { value: "30d", label: "近 30 天" },
        { value: "custom", label: "自定义" },
      ],
      exportFormats: [
        { value: "pdf", label: "PDF" },
        { value: "word", label: "Word" },
      ],
      blockPalette: [
        {
          type: "text",
          label: "文本说明模块",
          desc: "用于诊断结论、报告说明，可包含动态变量。",
        },
        {
          type: "kpi",
          label: "关键指标模块",
          desc: "展示病例总数、平均年龄、TOP 疾病等。",
        },
        {
          type: "chart",
          label: "图表模块",
          desc: "配置为疾病分布、年龄分布或科室统计等图表。",
        },
        {
          type: "table",
          label: "病例表格模块",
          desc: "展示病例明细数据，字段来源于 medicalinfo.cases。",
        },
      ],
      diseaseTypes: [
        "高血压",
        "感冒",
        "骨折",
        "颈椎病",
        "腰椎间盘突出",
        "胃炎",
        "抑郁症",
      ],
      hospitals: [
        "六安市中医院",
        "北京大学第三医院",
        "南方医科大学南方医院",
        "中国医学科学院北京协和医院",
      ],
      statusMap: {
        draft: "草稿",
        published: "已发布",
        offline: "已下架",
      },
    };
  },
  computed: {
    // 导航可用的模板（已发布）
    filteredPublishedTemplates() {
      return this.templates.filter((t) => {
        if (t.status !== "published") return false;
        if (this.generateForm.filterType && t.type !== this.generateForm.filterType) {
          return false;
        }
        return true;
      });
    },
    filteredTemplates() {
      return this.templates.filter((t) => {
        const { keyword, type, status } = this.templateQuery;
        if (keyword) {
          const lower = keyword.toLowerCase();
          if (
            !(
              t.name.toLowerCase().includes(lower) ||
              t.scene.toLowerCase().includes(lower)
            )
          ) {
            return false;
          }
        }
        if (type && t.type !== type) return false;
        if (status && t.status !== status) return false;
        return true;
      });
    },
    currentTemplateName() {
      const tpl = this.templates.find((t) => t.id === this.generateForm.templateId);
      return tpl ? tpl.name : "";
    },
    canNext() {
      if (this.currentStep === 1) {
        return !!this.generateForm.templateId;
      }
      if (this.currentStep === 2) {
        return !!this.generateForm.title && !!this.generateForm.startDate && !!this.generateForm.endDate;
      }
      return true;
    },
    exportLabel() {
      const fmt = this.exportFormats.find(
        (f) => f.value === this.generateForm.exportFormat
      );
      return fmt ? fmt.label : "PDF";
    },
    blockTypeMap() {
      return {
        text: "文本说明模块",
        kpi: "关键指标模块",
        chart: "图表模块",
        table: "病例表格模块",
      };
    },
    hasChartBlock() {
      const tpl = this.templates.find((t) => t.id === this.generateForm.templateId);
      if (!tpl || !tpl.blocks) return false;
      return tpl.blocks.some((b) => b.type === "chart");
    },
  },
  methods: {
    notify(msg) {
      // 简单提示封装：如果项目里集成了 this.$message 就用它，否则退回 alert
      if (this.$message && this.$message.warning) {
        this.$message.warning(msg);
      } else {
        // eslint-disable-next-line no-alert
        alert(msg);
      }
    },
    goStep(id) {
      if (id < this.currentStep && id >= 1) {
        this.currentStep = id;
      }
    },
    nextStep() {
      if (!this.canNext) return;
      if (this.currentStep < 3) this.currentStep += 1;
    },
    prevStep() {
      if (this.currentStep > 1) this.currentStep -= 1;
    },
    resetAll() {
      this.currentStep = 1;
      this.generateForm = {
        templateId: "",
        filterType: "",
        title: "",
        startDate: "",
        endDate: "",
        quickRange: "",
        caseFilter: {
          disease: "",
          gender: "",
          hospital: "",
        },
        dimensions: [],
        exportFormat: "pdf",
        useLLM: true,
      };
      this.previewSections = [];
    },
    setQuickRange(value) {
      this.generateForm.quickRange = value;
      const today = new Date();
      const format = (d) =>
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
          d.getDate()
        ).padStart(2, "0")}`;
      if (value === "7d") {
        const start = new Date(today.getTime() - 6 * 24 * 3600 * 1000);
        this.generateForm.startDate = format(start);
        this.generateForm.endDate = format(today);
      } else if (value === "30d") {
        const start = new Date(today.getTime() - 29 * 24 * 3600 * 1000);
        this.generateForm.startDate = format(start);
        this.generateForm.endDate = format(today);
      }
    },
    selectTemplate(tpl) {
      this.generateForm.templateId = tpl.id;
      if (!this.generateForm.title) {
        this.generateForm.title = `${tpl.name}`;
      }
    },
    // 生成报告：调用后端 /reports/generate +（可选）/ai/report
    async handleGenerateReport() {
      // 更明确的必填校验提示
      if (!this.generateForm.templateId) {
        this.currentStep = 1;
        this.notify("请先在第 1 步选择一个要使用的报告模板。");
        return;
      }
      if (!this.generateForm.title || !this.generateForm.startDate || !this.generateForm.endDate) {
        this.currentStep = 2;
        this.notify("请在第 2 步填写“报告名称”和完整的时间范围。");
        return;
      }
      this.generating = true;
      try {
        // 1. 组装请求体：携带当前选中的模板结构，便于后端按最新配置生成报告
        const currentTemplate = this.templates.find(
          (t) => t.id === this.generateForm.templateId
        );
        const payload = {
          templateId: this.generateForm.templateId,
          params: this.generateForm,
        };
        if (currentTemplate) {
          payload.template = currentTemplate;
        }

        // 2. 调用后端生成报告 sections
        const res = await this.$http.post("/reports/generate", payload);
        let sections =
          (res && res.data && res.data.sections) ||
          (res && res.data && res.data.data && res.data.data.sections) ||
          [];

        // 3. 如果勾选 LLM，则调用 /ai/report 生成一段智能诊断说明
        if (this.generateForm.useLLM) {
          try {
            const kpiSection = sections.find((s) => s.type === "kpi");
            const llmRes = await this.$http.post("/ai/report", {
              title: this.generateForm.title || "医疗数据分析报告",
              kpi: (kpiSection && kpiSection.runtimeKpi) || [],
              filters: this.generateForm,
            });
            const payload = llmRes && (llmRes.data || llmRes);
            const summary =
              (payload && payload.summary) ||
              (payload && payload.data && payload.data.summary) ||
              "";
            if (summary) {
              let injected = false;
              sections = sections.map((sec) => {
                if (
                  sec.type === "text" &&
                  typeof sec.runtimeContent === "string" &&
                  sec.runtimeContent.indexOf("{{llm_summary}}") !== -1
                ) {
                  injected = true;
                  return {
                    ...sec,
                    runtimeContent: sec.runtimeContent.replace(
                      "{{llm_summary}}",
                      summary
                    ),
                  };
                }
                return sec;
              });
              if (!injected) {
                sections.unshift({
                  id: "llm-summary",
                  type: "text",
                  typeLabel: "智能诊断",
                  title: "智能诊断说明",
                  runtimeContent: summary,
                });
              }
            }
          } catch (e) {
            console.error("调用 /ai/report 失败：", e);
            this.notify("智能诊断文字生成失败，将只展示统计结果。");
          }
        }

        this.previewSections = sections;
        if (!this.previewSections.length) {
          this.notify("后端未返回任何报告内容，请检查 /reports/generate 接口。");
        }
      } catch (e) {
        console.error("生成报告失败：", e);
        this.notify("生成报告失败，请稍后重试或查看控制台错误信息。");
      } finally {
        this.generating = false;
      }
    },
    filterCases(tableData) {
      const f = this.generateForm.caseFilter;
      return tableData.filter((row) => {
        // row 对应 medicalinfo.cases 的部分字段顺序：见 TableData.vue
        const type = row[0];
        const gender = row[1];
        const hospital = row[6];
        if (f.disease && f.disease !== type) return false;
        if (f.gender && f.gender !== gender) return false;
        if (f.hospital && f.hospital !== hospital) return false;
        return true;
      });
    },
    buildKpi(cases, homeData) {
      const total = cases.length;
      const ages = cases
        .map((r) => Number(r[2]))
        .filter((n) => !isNaN(n));
      const avgAge =
        ages.length > 0
          ? (ages.reduce((a, b) => a + b, 0) / ages.length).toFixed(1)
          : "-";
      const diseaseCount = {};
      cases.forEach((r) => {
        const t = r[0];
        diseaseCount[t] = (diseaseCount[t] || 0) + 1;
      });
      let topDisease = "-";
      let topValue = 0;
      Object.keys(diseaseCount).forEach((k) => {
        if (diseaseCount[k] > topValue) {
          topDisease = k;
          topValue = diseaseCount[k];
        }
      });
      return [
        {
          key: "total",
          label: "病例总数",
          value: total,
          desc: "筛选条件下的病例总量。",
        },
        {
          key: "avgAge",
          label: "平均年龄",
          value: avgAge,
          desc: "按病例年龄字段计算得到。",
        },
        {
          key: "topDisease",
          label: "最多疾病类型",
          value: topDisease,
          desc: `在筛选范围内出现次数最高的疾病（共 ${topValue} 例）。`,
        },
        {
          key: "homeTotal",
          label: "全库数据量",
          value: homeData && homeData.maxNum ? homeData.maxNum : "-",
          desc: "来自首页统计接口 /getHomeData。",
        },
      ];
    },
    applyVariables(template, cases, kpi) {
      if (!template) return "";
      const map = {
        startDate: this.generateForm.startDate,
        endDate: this.generateForm.endDate,
        disease: this.generateForm.caseFilter.disease,
        gender: this.generateForm.caseFilter.gender,
        hospital: this.generateForm.caseFilter.hospital,
        total_cases: cases.length,
        top_disease:
          (kpi.find((k) => k.key === "topDisease") || {}).value || "",
      };
      return template.replace(/{{(.*?)}}/g, (m, key) => {
        const v = map[key.trim()];
        return v != null && v !== "" ? v : m;
      });
    },
    async exportReport() {
      if (!this.previewSections.length) {
        this.notify("请先点击 \"生成报告并预览\" 再导出报告。");
        return;
      }
      if (!this.generateForm.templateId) {
        this.notify("请先选择一个报告模板。");
        return;
      }

      const format = this.generateForm.exportFormat || "excel";

      try {
        const payload = {
          templateId: this.generateForm.templateId,
          params: this.generateForm,
          format,
          sections: this.previewSections,
        };
        const res = await this.$http.post("/reports/export", payload, {
          responseType: "blob",
        });

        let mimeType = "application/octet-stream";
        let filename = "report_export.bin";
        if (format === "excel") {
          mimeType =
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
          filename = "report_export.xlsx";
        } else if (format === "csv") {
          mimeType = "text/csv;charset=utf-8";
          filename = "report_export.csv";
        } else if (format === "pdf") {
          mimeType = "application/pdf";
          filename = "report_export.pdf";
        } else if (format === "word") {
          mimeType =
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
          filename = "report_export.docx";
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
        console.error("导出报告失败", e);
        this.$message && this.$message.error("导出报告失败，请稍后重试。");
      }
    },
    scrollTop() {
      const el = this.$el.querySelector(".preview-scroll");
      if (el) el.scrollTop = 0;
    },
    // 模板管理相关
    createTemplate() {
      const id = `tpl-${Date.now()}`;
      const tpl = {
        id,
        name: "新建模板",
        type: "统计类",
        scene: "请填写适用场景说明",
        version: "1.0",
        status: "draft",
        updatedAt: new Date().toISOString().slice(0, 16).replace("T", " "),
        blocks: [],
        versions: [],
      };
      this.templates.unshift(tpl);
      this.currentTemplate = tpl;
    },
    selectTemplateForEdit(tpl) {
      this.currentTemplate = tpl;
    },
    addBlock(type) {
      if (!this.currentTemplate) return;
      const id = `${type}-${Date.now()}`;
      const baseConfig = {};
      if (type === "text") {
        baseConfig.template =
          "报告说明：本报告基于 {{startDate}} 至 {{endDate}} 数据生成，仅供参考。";
      } else if (type === "table") {
        baseConfig.source = "cases";
        baseConfig.fields = "type,gender,age,time,docHospital,department";
      } else if (type === "chart") {
        baseConfig.chartType = "disease";
        baseConfig.desc = "主要疾病类型分布图";
      } else if (type === "kpi") {
        baseConfig.source = "/getHomeData";
      }
      this.currentTemplate.blocks.push({
        id,
        type,
        config: baseConfig,
      });
    },
    moveBlock(index, offset) {
      const list = this.currentTemplate.blocks;
      const target = index + offset;
      if (target < 0 || target >= list.length) return;
      const item = list[index];
      this.$set(this.currentTemplate, "blocks", [
        ...list.slice(0, index),
        list[target],
        item,
        ...list.slice(target + 1),
      ]);
    },
    removeBlock(index) {
      this.currentTemplate.blocks.splice(index, 1);
    },
    async saveTemplate() {
      if (!this.currentTemplate) return;
      try {
        // 计算新版本号并追加版本记录
        const now = new Date();
        const currentVersion = parseFloat(this.currentTemplate.version || "1.0");
        const nextVersion = isNaN(currentVersion)
          ? "1.0"
          : (currentVersion + 0.1).toFixed(1);
        const code = `V${nextVersion}`;
        this.currentTemplate.version = nextVersion;
        this.currentTemplate.updatedAt = now
          .toISOString()
          .slice(0, 16)
          .replace("T", " ");
        if (!Array.isArray(this.currentTemplate.versions)) {
          this.currentTemplate.versions = [];
        }
        this.currentTemplate.versions.push({
          id: `ver-${Date.now()}`,
          code,
          time: now.toISOString().slice(0, 10),
          desc: "自动保存的新版本记录，可在实际项目中记录详细变更说明。",
        });

        const payload = {
          id: this.currentTemplate.id,
          name: this.currentTemplate.name,
          type: this.currentTemplate.type || "统计类",
          scene: this.currentTemplate.scene,
          status: this.currentTemplate.status || "draft",
          version: this.currentTemplate.version || "1.0",
          blocks: this.currentTemplate.blocks || [],
          versions: this.currentTemplate.versions || [],
        };
        const res = await this.$http.post("/templates/save", payload);
        const wrapper = res && (res.data || res);
        const data = wrapper && (wrapper.data || wrapper);
        if (data && data.id) {
          // 用后端返回的最新模板数据覆盖当前模板，并同步到模板列表中
          const idx = this.templates.findIndex((t) => t.id === data.id);
          if (idx >= 0) {
            this.$set(this.templates, idx, data);
          } else {
            this.templates.unshift(data);
          }
          this.currentTemplate = data;
        }
        this.$message && this.$message.success("模板已保存并持久化到数据库。");
      } catch (e) {
        console.error("保存模板失败", e);
        this.$message && this.$message.error("保存模板失败，请检查后端日志。");
      }
    },
    async publishTemplate() {
      if (!this.currentTemplate) return;
      try {
        const id = this.currentTemplate.id;
        const res = await this.$http.post(`/templates/${id}/publish`);
        const wrapper = res && (res.data || res);
        const data = wrapper && (wrapper.data || wrapper);
        if (data && data.id) {
          const idx = this.templates.findIndex((t) => t.id === data.id);
          if (idx >= 0) {
            this.$set(this.templates, idx, data);
          }
          this.currentTemplate = data;
        } else {
          this.currentTemplate.status = "published";
        }
        this.$message && this.$message.success("模板已发布，可在报告生成中使用。");
      } catch (e) {
        console.error("发布模板失败", e);
        this.$message && this.$message.error("发布模板失败，请检查后端日志。");
      }
    },
    async offlineTemplate() {
      if (!this.currentTemplate) return;
      try {
        const id = this.currentTemplate.id;
        const res = await this.$http.post(`/templates/${id}/offline`);
        const wrapper = res && (res.data || res);
        const data = wrapper && (wrapper.data || wrapper);
        if (data && data.id) {
          const idx = this.templates.findIndex((t) => t.id === data.id);
          if (idx >= 0) {
            this.$set(this.templates, idx, data);
          }
          this.currentTemplate = data;
        } else {
          this.currentTemplate.status = "offline";
        }
        this.$message && this.$message.success("模板已下架，不再出现在报告生成中。");
      } catch (e) {
        console.error("下架模板失败", e);
        this.$message && this.$message.error("下架模板失败，请检查后端日志。");
      }
    },
    async deleteTemplate() {
      if (!this.currentTemplate) return;
      const id = this.currentTemplate.id;
      // 使用浏览器原生确认框，避免引入额外依赖
      // eslint-disable-next-line no-alert
      const ok = window.confirm("确认删除当前模板？该操作不可恢复。");
      if (!ok) return;
      try {
        await this.$http.delete(`/templates/${id}`);
        const idx = this.templates.findIndex((t) => t.id === id);
        if (idx >= 0) {
          this.templates.splice(idx, 1);
        }
        if (this.generateForm.templateId === id) {
          this.generateForm.templateId = "";
        }
        if (this.currentTemplate && this.currentTemplate.id === id) {
          this.currentTemplate = this.templates.length ? this.templates[0] : null;
        }
        this.$message && this.$message.success("模板已删除。");
      } catch (e) {
        console.error("删除模板失败", e);
        this.$message && this.$message.error("删除模板失败，请检查后端日志。");
      }
    },
  },
  async created() {
    try {
      // TODO(backend): 将来改为从后端获取模板：
      // const res = await this.$http.get('/templates')
      // this.templates = res.data
      const res = await this.$http.get("/templates");
      const payload = res && (res.data || res);
      // 后端约定返回 { message, code, data: templates }
      this.templates = (payload && payload.data) || payload || [];
      if (!Array.isArray(this.templates)) {
        this.templates = [];
      }
    } catch (e) {
      // 目前使用前端 mock 数据
      console.error("加载报告模板失败，将使用前端示例模板。", e);
      this.templates = templateMocks;
    }
    if (this.templates.length) {
      this.currentTemplate = this.templates[0];
    }
  },
};
</script>

<style lang="less" scoped>
.report-container {
  width: 100%;
  /* 让整页大致占满视口高度（减去顶部标题栏） */
  height: calc(100vh - 80px);
  box-sizing: border-box;
}

.report-wrapper {
  width: 100%;
  /* 外层边框宽度固定为内容区域 100%，高度充满 report-container */
  max-width: 100%;
  height: 100%;
  padding: 10px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.report-header {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 16px;
}

.tabs {
  display: inline-flex;
  background: rgba(9, 25, 52, 0.8);
  border-radius: 999px;
  padding: 4px;
}

.tab-item {
  min-width: 140px;
  padding: 8px 20px;
  text-align: center;
  color: #7da5ff;
  font-size: 14px;
  cursor: pointer;
  border-radius: 999px;
  transition: all 0.2s;
}

.tab-item.active {
  background: linear-gradient(90deg, #1b67ff, #29e1ff);
  color: #fff;
  box-shadow: 0 0 12px rgba(29, 123, 255, 0.7);
}

.report-content {
  flex: 1;
  display: flex;
  gap: 20px;
  align-items: stretch;
}

.left-panel,
.right-panel {
  background: rgba(7, 18, 40, 0.9);
  border-radius: 12px;
  padding: 16px 20px;
  box-sizing: border-box;
}

.left-panel {
  flex: 0 0 40%;
  display: flex;
  flex-direction: column;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.panel-title {
  font-size: 16px;
  color: #3f96a5;
  font-weight: bold;
  margin-bottom: 12px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.step-item {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 6px 8px;
  margin-right: 6px;
  border-radius: 999px;
  background: rgba(14, 35, 72, 0.8);
  cursor: pointer;
  color: #7e9bff;
  font-size: 12px;
}

.step-item:last-child {
  margin-right: 0;
}

.step-item.active {
  background: linear-gradient(90deg, #1b67ff, #29e1ff);
  color: #fff;
}

.step-item.done {
  border: 1px solid #1b67ff;
}

.step-index {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 4px;
}

.step-body {
  flex: 1;
  overflow: auto;
  padding-right: 4px;
}

.step-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

.form-group {
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
}

.form-group label {
  color: #dce7ff;
  font-size: 13px;
  margin-bottom: 4px;
}

.form-group input,
.form-group select,
.form-group textarea {
  background: rgba(12, 32, 72, 0.9);
  border-radius: 6px;
  border: 1px solid #264b7f;
  color: #fff;
  padding: 6px 10px;
  font-size: 13px;
  outline: none;
}

.form-group textarea {
  resize: vertical;
}

.inline-inputs {
  display: flex;
  align-items: center;
  gap: 6px;
}

.inline-inputs .split {
  color: #9cb4ff;
  font-size: 12px;
}

.quick-range {
  display: flex;
  gap: 6px;
}

.range-chip {
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #264b7f;
  color: #9cb4ff;
  font-size: 12px;
  cursor: pointer;
}

.range-chip.active {
  background: #1b67ff;
  border-color: #1b67ff;
  color: #fff;
}

.checkbox-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #c4d3ff;
}

.checkbox-row input {
  margin-right: 4px;
}

.form-actions {
  margin-top: 8px;
  display: flex;
  gap: 10px;
}

.btn {
  min-width: 96px;
  padding: 6px 12px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  font-size: 13px;
}

.btn.primary {
  background: linear-gradient(90deg, #1b67ff, #29e1ff);
  color: #fff;
}

.btn.ghost {
  background: transparent;
  color: #7da5ff;
  border: 1px solid #295a9b;
}

.template-select-list {
  max-height: 320px;
  overflow: auto;
  margin-top: 4px;
}

.tpl-card {
  background: rgba(10, 30, 70, 0.9);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid transparent;
}

.tpl-card.selected {
  border-color: #1b67ff;
  box-shadow: 0 0 8px rgba(29, 123, 255, 0.6);
}

.tpl-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #e5f1ff;
  font-size: 14px;
  margin-bottom: 2px;
}

.tpl-type {
  font-size: 12px;
  color: #9cb4ff;
}

.tpl-scene {
  font-size: 12px;
  color: #a0b4da;
  margin-bottom: 2px;
}

.tpl-meta {
  font-size: 11px;
  color: #6276aa;
  display: flex;
  justify-content: space-between;
}

.mini-preview {
  margin-top: 6px;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px dashed #2b4f80;
  font-size: 12px;
  color: #a0b4da;
}

.mini-title {
  color: #3f96a5;
  margin-bottom: 2px;
}

.preview-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  /* 为预览区域统一设置内边距，确保占位提示文字完全落在边框内部 */
  padding: 10px 12px;
  box-sizing: border-box;
}

.preview-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7082a9;
  font-size: 13px;
  padding: 0 40px;
  text-align: center;
}

.preview-scroll {
  flex: 1;
  overflow: auto;
  color: #e5f1ff;
  font-size: 13px;
}

.preview-section {
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px dashed #283f6b;
}

.section-header {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.sec-index {
  font-size: 12px;
  color: #9cb4ff;
  margin-right: 6px;
}

.sec-title {
  font-size: 14px;
  color: #e5f1ff;
  margin-right: 8px;
}

.sec-type-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(16, 76, 140, 0.8);
}

.sec-body textarea {
  width: 100%;
  min-height: 80px;
  background: rgba(12, 32, 72, 0.9);
  border-radius: 6px;
  border: 1px solid #264b7f;
  color: #fff;
  padding: 6px 8px;
  font-size: 13px;
  resize: vertical;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}

.kpi-card {
  background: rgba(10, 30, 70, 0.9);
  border-radius: 8px;
  padding: 8px;
}

.kpi-label {
  font-size: 12px;
  color: #9cb4ff;
}

.kpi-value {
  font-size: 18px;
  font-weight: bold;
  margin: 2px 0;
}

.kpi-desc {
  font-size: 11px;
  color: #8898c2;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.preview-table th,
.preview-table td {
  border: 1px solid #2d4470;
  padding: 4px 6px;
}

.preview-table thead {
  background: rgba(18, 51, 96, 0.9);
}

.table-tip {
  margin-top: 4px;
  font-size: 11px;
  color: #8898c2;
}

.chart-placeholder {
  padding: 8px;
  background: rgba(9, 27, 64, 0.9);
  border-radius: 8px;
  border: 1px dashed #2b4f80;
}

.chart-sub {
  margin-top: 4px;
  font-size: 11px;
  color: #8898c2;
}

.export-actions {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

.empty-tip {
  font-size: 12px;
  color: #7082a9;
}

/* 模板管理右侧 */
.template-left {
  flex: 0 0 32%;
  background: rgba(7, 18, 40, 0.9);
  border-radius: 12px;
  padding: 14px 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  /* 高度由内容决定，避免裁切导致底部露白 */
  height: auto;
}

.template-right {
  flex: 1;
  background: rgba(7, 18, 40, 0.9);
  border-radius: 12px;
  padding: 14px 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.template-toolbar {
  margin-top: 6px;
  margin-bottom: 6px;
  display: flex;
  justify-content: flex-start;
}

.template-list {
  flex: 1;
  overflow: auto;
  margin-top: 4px;
}

.tpl-item {
  padding: 8px;
  border-radius: 8px;
  background: rgba(10, 30, 70, 0.9);
  margin-bottom: 6px;
  cursor: pointer;
}

.tpl-item.active {
  border: 1px solid #1b67ff;
}

.tpl-main {
  margin-bottom: 4px;
}

.tpl-name {
  color: #e5f1ff;
  font-size: 14px;
}

.tpl-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.tag {
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(18, 51, 96, 0.9);
}

.tag.status.draft {
  background: rgba(120, 120, 120, 0.5);
}

.tag.status.published {
  background: rgba(40, 190, 120, 0.3);
}

.tag.status.offline {
  background: rgba(190, 40, 80, 0.3);
}

.version {
  color: #a0b4da;
}

.editor-layout {
  display: flex;
  gap: 10px;
  margin-top: 4px;
  flex: 1;
  min-height: 0;
}

.editor-palette {
  flex: 0 0 34%;
  background: rgba(9, 27, 64, 0.9);
  border-radius: 10px;
  padding: 8px;
  box-sizing: border-box;
}

.editor-canvas {
  flex: 1;
  background: rgba(9, 27, 64, 0.9);
  border-radius: 10px;
  padding: 8px;
  box-sizing: border-box;
  /* 固定高度，内容多了在这个区域内滚动，不再撑高整个编辑模块 */
  height: 450px;
  overflow-y: auto;
  overflow-x: hidden;
}

.palette-title,
.canvas-header {
  font-size: 13px;
  color: #9cb4ff;
  margin-bottom: 4px;
}

.palette-item {
  padding: 6px;
  border-radius: 8px;
  background: rgba(12, 32, 72, 0.9);
  margin-bottom: 4px;
  cursor: pointer;
}

.p-name {
  font-size: 13px;
  color: #e5f1ff;
}

.p-desc {
  font-size: 11px;
  color: #8898c2;
}

.canvas-block {
  margin-bottom: 6px;
  padding: 6px;
  border-radius: 8px;
  background: rgba(12, 32, 72, 0.9);
}

.cb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #e5f1ff;
  margin-bottom: 4px;
}

.cb-actions {
  display: flex;
  gap: 4px;
}

.mini-btn {
  padding: 2px 6px;
  border-radius: 999px;
  border: 1px solid #295a9b;
  background: transparent;
  color: #9cb4ff;
  font-size: 11px;
  cursor: pointer;
}

.mini-btn.danger {
  border-color: #b05564;
  color: #ff7d8f;
}

.cb-body label {
  display: block;
  font-size: 12px;
  color: #a0b4da;
  margin-top: 4px;
  margin-bottom: 2px;
}

.cb-body textarea,
.cb-body input,
.cb-body select {
  width: 100%;
  background: rgba(7, 23, 55, 0.9);
  border-radius: 6px;
  border: 1px solid #264b7f;
  color: #fff;
  padding: 4px 6px;
  font-size: 12px;
}

.version-panel {
  margin-top: 6px;
  max-height: 120px;
  overflow: auto;
  border-top: 1px solid #283f6b;
  padding-top: 4px;
}

.version-title {
  font-size: 13px;
  color: #9cb4ff;
  margin-bottom: 2px;
}

.version-item {
  font-size: 11px;
  color: #a0b4da;
  margin-bottom: 4px;
}

.v-code {
  margin-right: 6px;
}

.v-time {
  color: #7082a9;
}

.template-actions {
  margin-top: 6px;
  display: flex;
  gap: 8px;
}

.template-scroll {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.editor-helper {
  font-size: 12px;
  color: #8898c2;
  margin-bottom: 4px;
  line-height: 1.5;
}

.help-btn {
  margin-left: auto;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #295a9b;
  background: transparent;
  color: #7da5ff;
  font-size: 12px;
  cursor: pointer;
}

.help-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.help-dialog {
  width: 720px;
  max-height: 80vh;
  background: #050b1e;
  border-radius: 10px;
  border: 1px solid #295a9b;
  box-shadow: 0 0 18px rgba(10, 40, 90, 0.9);
  display: flex;
  flex-direction: column;
}

.help-header {
  padding: 10px 14px;
  border-bottom: 1px solid #283f6b;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #e5f1ff;
  font-size: 14px;
}

.help-close {
  border: none;
  background: transparent;
  color: #7da5ff;
  font-size: 18px;
  cursor: pointer;
}

.help-body {
  padding: 12px 16px 16px;
  overflow: auto;
  color: #c4d3ff;
  font-size: 13px;
  line-height: 1.6;
}

.help-body p {
  margin: 6px 0;
}

.help-body ul {
  padding-left: 18px;
  margin: 4px 0 8px;
}

.help-body code {
  font-family: Consolas, Menlo, monospace;
  font-size: 12px;
  background: rgba(15, 37, 80, 0.9);
  padding: 1px 4px;
  border-radius: 3px;
}

.field-tip {
  margin-top: 2px;
  font-size: 11px;
  color: #8898c2;
}
</style>

