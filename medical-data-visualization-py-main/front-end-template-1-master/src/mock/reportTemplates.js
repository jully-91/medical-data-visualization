// 报告模板前端示例数据
// TODO(backend): 后端可以直接实现 GET /templates 接口返回相同结构的数据

const templates = [
  {
    id: "tpl-stat-month",
    name: "月度疾病统计报告",
    type: "统计类",
    scene: "用于展示某个月内各疾病类型、年龄段、科室就诊情况。",
    version: "1.0",
    status: "published",
    updatedAt: "2025-12-01 10:20",
    blocks: [
      {
        id: "b1",
        type: "text",
        config: {
          // 支持变量占位：startDate、endDate、disease、gender、hospital、total_cases、top_disease
          template:
            "本报告基于 {{startDate}} 至 {{endDate}} 期间的病例数据生成，仅供医疗决策与教学参考。",
        },
      },
      {
        id: "b2",
        type: "kpi",
        config: { source: "/getHomeData" },
      },
      {
        id: "b3",
        type: "chart",
        config: { chartType: "disease", desc: "主要疾病类型占比情况" },
      },
      {
        id: "b4",
        type: "table",
        config: {
          source: "cases",
          fields: "type,gender,age,time,docHospital,department",
        },
      },
    ],
    versions: [
      {
        id: "v1",
        code: "V1.0",
        time: "2025-12-01",
        desc: "初始版本：包含概览说明、关键指标、疾病饼图与病例明细表。",
      },
    ],
  },
];

export default templates;


