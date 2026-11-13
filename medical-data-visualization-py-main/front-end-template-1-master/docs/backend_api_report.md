# 报告生成 & 模板管理接口约定（后端对接说明）

> 说明：当前前端已完成页面与示例逻辑，本文档约定后端需要实现的接口和数据结构，方便直接对接。

## 一、模板管理相关

### 1. 获取模板列表

- **URL**: `GET /templates`
- **说明**: 返回所有可用报告模板，用于“报告模板管理”和“报告生成”的模板选择。
- **返回示例**:

```json
[
  {
    "id": "tpl-stat-month",
    "name": "月度疾病统计报告",
    "type": "统计类",
    "scene": "用于展示某个月内各疾病类型、年龄段、科室就诊情况。",
    "version": "1.0",
    "status": "published",
    "updatedAt": "2025-12-01 10:20",
    "blocks": [
      { "id": "b1", "type": "text", "config": { "template": "..." } },
      { "id": "b2", "type": "kpi", "config": { "source": "/getHomeData" } },
      {
        "id": "b3",
        "type": "chart",
        "config": { "chartType": "disease", "desc": "主要疾病类型占比情况" }
      },
      {
        "id": "b4",
        "type": "table",
        "config": {
          "source": "cases",
          "fields": "type,gender,age,time,docHospital,department"
        }
      }
    ],
    "versions": [
      {
        "id": "v1",
        "code": "V1.0",
        "time": "2025-12-01",
        "desc": "初始版本：包含概览说明、关键指标、疾病饼图与病例明细表。"
      }
    ]
  }
]
```

### 2. 新建 / 更新 / 发布模板（可选）

前端目前在本地做“保存为新版本”和“发布模板”的模拟，后端如需落库，可按以下约定实现：

- `POST /templates`：创建模板
- `PUT /templates/:id`：更新模板内容（包括 blocks）
- `POST /templates/:id/publish`：发布模板（status 置为 `published`）

数据结构与 `GET /templates` 返回的单条模板一致。

## 二、报告生成相关

### 1. 生成报告预览

> 当前前端仍在 `Report.vue` 中通过 `/getHomeData` + `/tableData` 自行拼装预览。  
> 后端接入后，可统一通过本接口返回“sections”结构，前端只负责展示。

- **URL**: `POST /reports/generate`
- **请求体**:

```json
{
  "templateId": "tpl-stat-month",
  "params": {
    "title": "2025-01 高血压病例统计报告",
    "startDate": "2025-01-01",
    "endDate": "2025-01-31",
    "caseFilter": {
      "disease": "高血压",
      "gender": "女",
      "hospital": "六安市中医院"
    },
    "dimensions": ["age", "gender", "department"],
    "exportFormat": "pdf",
    "useLLM": true
  }
}
```

- **返回结构**（对应前端的 `previewSections`）:

```json
{
  "sections": [
    {
      "id": "b1",
      "type": "text",
      "typeLabel": "文本说明",
      "title": "诊断说明 / 报告概述",
      "runtimeContent": "替换变量后的完整文本..."
    },
    {
      "id": "b2",
      "type": "kpi",
      "typeLabel": "关键指标",
      "title": "关键统计指标",
      "runtimeKpi": [
        { "key": "total", "label": "病例总数", "value": 1286, "desc": "..." },
        { "key": "avgAge", "label": "平均年龄", "value": 47.3, "desc": "..." }
      ]
    },
    {
      "id": "b3",
      "type": "chart",
      "typeLabel": "统计图表",
      "title": "统计图表",
      "chartDesc": "主要疾病类型占比情况",
      "chartType": "disease",
      "data": {}  // 供前端 ECharts 使用的配置或原始数据
    },
    {
      "id": "b4",
      "type": "table",
      "typeLabel": "病例表格",
      "title": "部分病例明细（Top 10）",
      "runtimeHeader": ["疾病类型", "性别", "年龄", "就诊时间", "医院", "科室"],
      "runtimeRows": [
        ["高血压", "女", "62", "01.09", "沧州市人民医院", "肾病内科"]
      ]
    }
  ]
}
```

前端当前逻辑中对该接口的调用位置预留在 `Report.vue` 的 `handleGenerateReport` 中。

### 2. DeepSeek 智能诊断文字

- **URL**: `POST /ai/report`
- **说明**: 后端代理调用 DeepSeek，根据统计指标和筛选条件生成诊断说明文字。
- **请求体示例**:

```json
{
  "title": "2025-01 高血压病例统计报告",
  "kpi": [
    { "key": "total", "label": "病例总数", "value": 1286 },
    { "key": "avgAge", "label": "平均年龄", "value": 47.3 }
  ],
  "filters": {
    "startDate": "2025-01-01",
    "endDate": "2025-01-31",
    "caseFilter": {
      "disease": "高血压",
      "gender": "女",
      "hospital": "六安市中医院"
    }
  }
}
```

- **返回示例**:

```json
{
  "summary": "本月共收治高血压女性患者 1286 例，平均年龄约 47.3 岁，主要集中在 40-60 岁年龄段..."
}
```

模板中的 `text` 模块可以通过 `{{llm_summary}}` 占位符插入该内容。

## 三、已有接口复用

前端现有页面已使用以下接口，后端无需更改入参，只需保证返回格式稳定：

- `GET /getHomeData`：首页大屏统计数据（总量、热门科室等）。
- `GET /tableData`：病例表格数据，对应数据库 `medicalinfo.cases`。
- `POST /submitModel`：在线预测（Pred 页面）。

扩展接口（在需求文档中已有说明，可按需实现）：

- `POST /getSimilarCases`：返回与输入症状相似的病例列表。
- `GET /evaluateModel`：不同算法模型评估指标。
- `GET /dataQualityCheck`：数据质量统计（缺失值、异常值、重复记录等）。


