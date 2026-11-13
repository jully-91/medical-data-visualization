<template>
  <div class="home">
    <transition name="fade" mode="out-in">
      <dv-loading v-if="!config4.data.length">Loading...</dv-loading>
      <dv-border-box-10 class="outer-border">
        <div class="naca">
          <div class="index-header" style="margin-top: 5px">
            <div>
              <dv-decoration-10
                style="width: 450px; height: 1px; margin-bottom: 45px"
              />
              <dv-decoration-8
                style="width: 180px; height: 50px"
                :color="['#568aea', '#000000']"
              />
              <div
                style="
                  width: 150px;
                  color: #eeecec;
                  font-size: 18px;
                  padding: 0 15px;
                  font-weight: bold;
                "
              >
                可视化平台
              </div>
              <dv-decoration-8
                :reverse="true"
                style="width: 180px; height: 50px"
                :color="['#568aea', '#000000']"
              />
              <dv-decoration-10
                style="
                  width: 450px;
                  height: 1px;
                  transform: rotateY(180deg);
                  margin-bottom: 45px;
                "
              />
            </div>
            <dv-decoration-5
              style="width: 10%; height: 20px"
              :color="['#568aea', '#000000']"
            />
          </div>

          <!-- 筛选与控制区域，仅前端过滤与交互（自定义下拉 + 复选框） -->
          <div class="filter-bar" @click="closeDropdown">
            <!-- 年龄多选下拉 -->
            <div class="filter-group filter-dropdown">
              <div class="filter-header" @click.stop="toggleDropdown('age')">
                <span class="filter-label">年龄:</span>
                <div class="filter-display">{{ getDisplayText('age') }}</div>
                <span class="filter-arrow">▼</span>
              </div>
              <div class="filter-panel" v-if="openDropdown === 'age'">
                <label class="filter-panel-item">
                  <input
                    type="checkbox"
                    :checked="filters.age.length === 0"
                    @click.stop
                    @change.stop="setAll('age')"
                  />
                  全部
                </label>
                <label
                  v-for="item in ageOptions"
                  :key="item.value"
                  class="filter-panel-item"
                >
                  <input
                    type="checkbox"
                    :value="item.value"
                    :checked="filters.age.includes(item.value)"
                    @click.stop
                    @change.stop="toggleOption('age', item.value)"
                  />
                  {{ item.label }}
                </label>
              </div>
            </div>

            <!-- 性别多选下拉 -->
            <div class="filter-group filter-dropdown">
              <div class="filter-header" @click.stop="toggleDropdown('gender')">
                <span class="filter-label">性别:</span>
                <div class="filter-display">{{ getDisplayText('gender') }}</div>
                <span class="filter-arrow">▼</span>
              </div>
              <div class="filter-panel" v-if="openDropdown === 'gender'">
                <label class="filter-panel-item">
                  <input
                    type="checkbox"
                    :checked="filters.gender.length === 0"
                    @click.stop
                    @change.stop="setAll('gender')"
                  />
                  全部
                </label>
                <label class="filter-panel-item">
                  <input
                    type="checkbox"
                    value="男"
                    :checked="filters.gender.includes('男')"
                    @click.stop
                    @change.stop="toggleOption('gender', '男')"
                  />
                  男
                </label>
                <label class="filter-panel-item">
                  <input
                    type="checkbox"
                    value="女"
                    :checked="filters.gender.includes('女')"
                    @click.stop
                    @change.stop="toggleOption('gender', '女')"
                  />
                  女
                </label>
              </div>
            </div>

            <!-- 疾病类型多选下拉 -->
            <div class="filter-group filter-dropdown">
              <div class="filter-header" @click.stop="toggleDropdown('disease')">
                <span class="filter-label">疾病类型:</span>
                <div class="filter-display long-display">{{ getDisplayText('disease') }}</div>
                <span class="filter-arrow">▼</span>
              </div>
              <div class="filter-panel" v-if="openDropdown === 'disease'">
                <label class="filter-panel-item">
                  <input
                    type="checkbox"
                    :checked="filters.disease.length === 0"
                    @click.stop
                    @change.stop="setAll('disease')"
                  />
                  全部
                </label>
                <label
                  v-for="item in diseaseOptions"
                  :key="item"
                  class="filter-panel-item"
                >
                  <input
                    type="checkbox"
                    :value="item"
                    :checked="filters.disease.includes(item)"
                    @click.stop
                    @change.stop="toggleOption('disease', item)"
                  />
                  {{ item }}
                </label>
              </div>
            </div>

            <!-- 时间多选下拉 -->
            <div class="filter-group filter-dropdown">
              <div class="filter-header" @click.stop="toggleDropdown('time')">
                <span class="filter-label">时间:</span>
                <div class="filter-display">{{ getDisplayText('time') }}</div>
                <span class="filter-arrow">▼</span>
              </div>
              <div class="filter-panel" v-if="openDropdown === 'time'">
                <label class="filter-panel-item">
                  <input
                    type="checkbox"
                    :checked="filters.time.length === 0"
                    @click.stop
                    @change.stop="setAll('time')"
                  />
                  全部
                </label>
                <label
                  v-for="item in timeOptions"
                  :key="item"
                  class="filter-panel-item"
                >
                  <input
                    type="checkbox"
                    :value="item"
                    :checked="filters.time.includes(item)"
                    @click.stop
                    @change.stop="toggleOption('time', item)"
                  />
                  {{ item }}
                </label>
              </div>
            </div>

            <button class="filter-reset" @click="resetFilters">重置筛选</button>
            <button class="fullscreen-btn" @click="toggleFullScreen">
              {{ isFullscreen ? '退出全屏' : '全屏展示' }}
            </button>
          </div>

          <div class="index-content">
            <div class="left">
              <div class="left-1">
                <!-- 顶部年龄饼图略微缩小，给下方留空间 -->
                <dv-border-box-12
                  ><div style="padding: 6px 8px 0 8px; height: 100%">
                    <div class="title" style="margin-top: 0">
                      各年龄段患病占比
                    </div>

                    <div
                      ref="firstMain"
                      style="width: 100%; height: 180px"
                    ></div></div
                ></dv-border-box-12>
                <dv-border-box-8
                  ><div style="padding: 8px 8px 10px 8px; height: 100%">
                    <div class="title" style="margin-top: 2px">
                      疾病类型分布
                    </div>
                    <dv-capsule-chart
                      :config="config1"
                      style="width: 95%; height: 180px"
                    /></div
                ></dv-border-box-8>

                <!-- 病例列表整体上移，保证完全落在外框之内 -->
                <dv-border-box-3
                  ><div style="padding: 8px 12px 10px 12px; height: 100%">
                    <div class="title" style="margin-top: 8px">病例列表</div>
                    <!-- <div ref="timeZhou" style="width: 100%; height: 350px"></div> -->
                    <div class="row_list" style="">
                      <ul class="cases_list">
                        <li style="font-size: 15px">
                          <div>编号</div>
                          <div>求诊类型</div>
                          <div>性别</div>
                          <div>年龄</div>
                          <div>身高</div>
                          <div>体重</div>
                          <div>患病时长</div>
                        </li>
                        <li v-for="cases in casesData">
                          <div>{{ cases[0] }}</div>
                          <div>{{ cases[1] }}</div>
                          <div>{{ cases[2] }}</div>
                          <div>{{ cases[3] }}</div>
                          <div>{{ cases[10] }}</div>
                          <div>{{ cases[11] }}</div>
                          <div>{{ cases[12] }}</div>
                        </li>
                      </ul>
                    </div>
                  </div></dv-border-box-3
                >
              </div>
            </div>
            <div class="cents">
              <!-- 上半部分整体稍微下移一点 -->
              <div class="above" style="margin-top: 6px">
                <div class="aboveOne">
                  <div
                    style="
                      padding: 10px 25px 0 25px;
                      width: 100%;
                      box-sizing: border-box;
                    "
                  >
                    <div class="title">疾病数据信息</div>
                    <div
                      style="
                        display: flex;
                        flex-direction: column;
                        width: 100%;
                        height: 150px;
                        color: #eeecec;
                      "
                    >
                      <div style="display: flex; flex: 1">
                        <dv-decoration-11
                          style="height: 60px; text-align: center"
                          ><div style="flex: 1">
                            数据数量:{{ centerData.maxNum }}
                          </div></dv-decoration-11
                        >
                        <dv-decoration-11
                          style="height: 60px; text-align: center"
                          ><div style="flex: 1">
                            最多疾病类型:{{ centerData.maxType }}
                          </div></dv-decoration-11
                        >
                        <dv-decoration-11
                          style="height: 60px; text-align: center"
                          ><div style="flex: 1">
                            求诊最多科室:{{ centerData.maxDep }}
                          </div></dv-decoration-11
                        >
                      </div>
                      <div style="display: flex; flex: 1">
                        <dv-decoration-11
                          style="height: 60px; text-align: center"
                          ><div style="flex: 1">
                            最大患者年龄:{{ centerData.maxAge }}
                          </div></dv-decoration-11
                        >
                        <dv-decoration-11
                          style="height: 60px; text-align: center"
                          ><div style="flex: 1">
                            最小患者年龄:{{ centerData.minAge }}
                          </div></dv-decoration-11
                        >
                        <dv-decoration-11
                          style="height: 60px; text-align: center"
                          ><div style="flex: 1">
                            热门医院:{{ centerData.maxHos }}
                          </div></dv-decoration-11
                        >
                      </div>
                    </div>
                  </div>
                  <div
                    style="
                      padding: 5px 25px 10px 25px;
                      width: 100%;
                      box-sizing: border-box;
                    "
                  >
                    <div class="title" style="margin-top: 0">
                      男女性别患病对比
                    </div>
                    <div class="content">
                      <dv-active-ring-chart
                        :config="config3"
                        style="width: 150px; height: 100px"
                      />
                      <dv-water-level-pond
                        :config="config4"
                        style="width: 100px; height: 90px"
                      />
                      <dv-active-ring-chart
                        :config="config3"
                        style="width: 150px; height: 100px"
                      />
                    </div>
                  </div>
                </div>
                <div class="aboveTwo">
                  <dv-border-box-9 :color="['#568aea']">
                    <div style="padding: 10px; height: 100%">
                      <div class="title" style="margin-top: 5px">
                        医院科室环形图
                      </div>
                      <div
                        id="secondMian"
                        style="width: 100%; height: 160px"
                      ></div></div
                  ></dv-border-box-9>
                  <dv-border-box-1
                    ><div style="padding: 8px; height: 100%">
                      <div class="title" style="margin-top: 5px">
                        疾病关键词云图
                      </div>
                      <div
                        ref="thirdMain"
                        style="width: 100%; height: 140px"
                      ></div></div
                  ></dv-border-box-1>
                </div>
              </div>
              <!-- 下半部分与左侧病例列表底部基本对齐 -->
              <div class="below" style="margin-top: 4px">
                <dv-border-box-13>
                  <div style="padding: 7px">
                    <div class="title" style="margin-top: 5px">
                      患病身高体重平均数图
                      <div class="height-weight-note">
                        注：仅统计身高和体重信息齐全的病例
                      </div>
                    </div>
                    <div
                      ref="lastMain"
                      style="width: 100%; height: 260px; margin-top: 10px"
                    ></div>
                  </div>
                </dv-border-box-13>
              </div>
            </div>
          </div>
        </div>
      </dv-border-box-10>
    </transition>
  </div>
</template>

<script>
import $ from "jquery";
import LeftTop from "@/components/LeftTop.vue";
function formatter(number) {
  const numbers = number.toString().split("").reverse();
  const segs = [];

  while (numbers.length) segs.push(numbers.splice(0, 3).join(""));

  return segs.join(",").split("").reverse().join("");
}
export default {
  name: "Index",
  data() {
    return {
      // 原始病例数据与过滤后数据
      allCasesData: [],
      currentIndex: 0,
      pieData: [],
      casesData: [],
      centerData: {
        maxNum: "",
        maxType: "",
        maxDep: "",
        maxHos: "",
        maxAge: "",
        minAge: "",
      },
      wordData: "",
      circleData: "",
      lastData: {},
      // 疾病类型分布：完整数据及滚动窗口控制
      fullDiseaseStats: [],
      diseaseScrollIndex: 0,
      diseaseWindowSize: 6,
      // 前端筛选条件（多选，空数组表示“全部”）
      filters: {
        age: [],
        gender: [],
        disease: [],
        time: [],
      },
      ageOptions: [
        { value: "0-10", label: "0-10岁" },
        { value: "10-20", label: "10-20岁" },
        { value: "20-30", label: "20-30岁" },
        { value: "30-40", label: "30-40岁" },
        { value: "40-50", label: "40-50岁" },
        { value: "50-60", label: "50-60岁" },
        { value: "60+", label: "60岁以上" },
      ],
      diseaseOptions: [],
      timeOptions: [],
      isFullscreen: false,
      openDropdown: null,
      config1: {},
      config2: {
        lineWidth: 20,
        radius: "50%",
        activeRadius: "60%",
        activeTimeGap: 2000,
        digitalFlopStyle: {
          fontSize: 13,
        },
        data: [{ name: "demo", value: 1 }],
      },
      config3: {
        lineWidth: 20,
        radius: "50%",
        activeRadius: "60%",
        activeTimeGap: 2000,
        digitalFlopStyle: {
          fontSize: 13,
        },
        data: [],
      },
      config4: {
        data: [],
        shape: "roundRect",
      },
    };
  },
  methods: {
    // 计算年龄分段
    getAgeBucket(age) {
      const n = Number(age);
      if (Number.isNaN(n)) return null;
      if (n < 10) return "0-10";
      if (n < 20) return "10-20";
      if (n < 30) return "20-30";
      if (n < 40) return "30-40";
      if (n < 50) return "40-50";
      if (n < 60) return "50-60";
      return "60+";
    },
    // 应用筛选并重算前端各图表数据
    applyFilters() {
      if (!this.allCasesData || !this.allCasesData.length) return;
      const { age, gender, disease, time } = this.filters;
      const filtered = this.allCasesData.filter((row) => {
        const rowAgeBucket = this.getAgeBucket(row[3]);
        const rowGender = row[2];
        const rowDisease = row[1];
        const rowTime = row[4];

        if (age.length && !age.includes(rowAgeBucket)) return false;
        if (gender.length && !gender.includes(rowGender)) return false;
        if (disease.length && !disease.includes(rowDisease)) return false;
        if (time.length && !time.includes(rowTime)) return false;
        return true;
      });

      this.casesData = filtered;
      this.rebuildStatsFromCases(filtered);

      // 立即刷新一次图表（后续还有定时动画）
      this.setPieData();
      this.setConfig1();
      this.setCircleData();
      this.setWordData();
      this.setLastData();
    },
    // 从病例列表重建统计数据（不动后端）
    rebuildStatsFromCases(casesList) {
      // 中心统计
      this.centerData.maxNum = casesList.length;
      let maxAge = 0;
      let minAge = 200;
      const typeCount = {};
      const depCount = {};
      const hosCount = {};

      casesList.forEach((c) => {
        const type = c[1];
        const dep = c[8];
        const hos = c[7];
        const age = Number(c[3]);
        if (!Number.isNaN(age)) {
          if (age > maxAge) maxAge = age;
          if (age < minAge) minAge = age;
        }
        typeCount[type] = (typeCount[type] || 0) + 1;
        depCount[dep] = (depCount[dep] || 0) + 1;
        hosCount[hos] = (hosCount[hos] || 0) + 1;
      });
      this.centerData.maxAge = maxAge || "";
      this.centerData.minAge = minAge === 200 ? "" : minAge;

      const sortByValueDesc = (obj) =>
        Object.entries(obj).sort((a, b) => b[1] - a[1]);

      const typeSort = sortByValueDesc(typeCount);
      const depSort = sortByValueDesc(depCount);
      const hosSort = sortByValueDesc(hosCount);
      this.centerData.maxType = typeSort[0] ? typeSort[0][0] : "";
      this.centerData.maxDep = depSort[0] ? depSort[0][0] : "";
      this.centerData.maxHos = hosSort[0] ? hosSort[0][0] : "";

      // 年龄占比
      const ageDic = {
        "0-10岁": 0,
        "10-20岁": 0,
        "20-30岁": 0,
        "30-40岁": 0,
        "40-50岁": 0,
        "50-60岁": 0,
        "60岁以上": 0,
      };
      casesList.forEach((c) => {
        const bucket = this.getAgeBucket(c[3]);
        if (!bucket) return;
        if (bucket === "0-10") ageDic["0-10岁"]++;
        else if (bucket === "10-20") ageDic["10-20岁"]++;
        else if (bucket === "20-30") ageDic["20-30岁"]++;
        else if (bucket === "30-40") ageDic["30-40岁"]++;
        else if (bucket === "40-50") ageDic["40-50岁"]++;
        else if (bucket === "50-60") ageDic["50-60岁"]++;
        else ageDic["60岁以上"]++;
      });
      this.pieData = Object.keys(ageDic).map((k) => ({
        name: k,
        value: ageDic[k],
      }));

      // 疾病类型分布：保留完整列表，具体展示由滚动窗口控制
      const typeEntries = Object.entries(typeCount);
      this.fullDiseaseStats = typeEntries.map(([k, v]) => ({
        name: k,
        value: v,
      }));
      // 每次重建统计时，从头开始滚动
      this.diseaseScrollIndex = 0;

      // 性别相关
      const boyDic = {};
      const girlDic = {};
      let boyNum = 0;
      let girlNum = 0;
      casesList.forEach((c) => {
        const type = c[1];
        if (c[2] === "男") {
          boyNum++;
          boyDic[type] = (boyDic[type] || 0) + 1;
        } else if (c[2] === "女") {
          girlNum++;
          girlDic[type] = (girlDic[type] || 0) + 1;
        }
      });
      const boyList = Object.entries(boyDic).map(([k, v]) => ({
        name: k,
        value: v,
      }));
      const girlList = Object.entries(girlDic).map(([k, v]) => ({
        name: k,
        value: v,
      }));
      const ratioData = [];
      const totalNum = casesList.length || 1;
      const boyRatio = Math.round((boyNum / totalNum) * 100);
      const girlRatio = Math.round((girlNum / totalNum) * 100);
      ratioData.push(girlRatio);
      ratioData.push(boyRatio);
      this.config2.data = boyList;
      this.config3.data = girlList;
      this.config4.data = ratioData;

      // 科室环形图
      this.circleData = Object.entries(depCount).map(([k, v]) => ({
        name: k,
        value: v,
      }));

      // 关键词云图（这里简单使用疾病类型频次）
      this.wordData = this.fullDiseaseStats;

      // 身高体重平均值图
      const dataDic = {};
      casesList.forEach((c) => {
        const type = c[1];
        const height = Number(c[10]);
        const weight = Number(c[11]);
        // 仅统计身高和体重都为有效正数的病例
        if (
          Number.isNaN(height) ||
          Number.isNaN(weight) ||
          height <= 0 ||
          weight <= 0
        ) {
          return;
        }
        if (!dataDic[type]) {
          dataDic[type] = { sumH: 0, sumW: 0, cnt: 0 };
        }
        dataDic[type].sumH += height;
        dataDic[type].sumW += weight;
        dataDic[type].cnt += 1;
      });
      const xData = [];
      const y1Data = [];
      const y2Data = [];
      Object.entries(dataDic).forEach(([k, v]) => {
        xData.push(k);
        y1Data.push(v.cnt ? Math.round(v.sumH / v.cnt) : 0);
        y2Data.push(v.cnt ? Math.round(v.sumW / v.cnt) : 0);
      });
      this.lastData = { xData, y1Data, y2Data };
    },
    // 过滤条件变更
    handleFilterChange() {
      this.applyFilters();
    },
    resetFilters() {
      this.filters = {
        age: [],
        gender: [],
        disease: [],
        time: [],
      };
      this.applyFilters();
    },
    // “全部”按钮：清空对应维度的选中项
    setAll(field) {
      if (this.filters[field]) {
        this.filters[field] = [];
        this.applyFilters();
      }
    },
    // 多选项勾选/取消
    toggleOption(field, value) {
      const arr = this.filters[field] || [];
      const idx = arr.indexOf(value);
      if (idx === -1) {
        this.$set(this.filters, field, [...arr, value]);
      } else {
        const copy = [...arr];
        copy.splice(idx, 1);
        this.$set(this.filters, field, copy);
      }
      this.applyFilters();
    },
    // 显示当前选中项的文本
    getDisplayText(field) {
      const arr = this.filters[field] || [];
      if (!arr.length) return "全部";
      if (field === "age") {
        const labelMap = this.ageOptions.reduce((m, cur) => {
          m[cur.value] = cur.label;
          return m;
        }, {});
        return arr.map((v) => labelMap[v] || v).join("、");
      }
      return arr.join("、");
    },
    // 下拉开关
    toggleDropdown(field) {
      this.openDropdown = this.openDropdown === field ? null : field;
    },
    // 关闭下拉
    closeDropdown() {
      this.openDropdown = null;
    },
    // 全屏控制
    toggleFullScreen() {
      const doc = window.document;
      const docEl = doc.documentElement;
      const requestFullScreen =
        docEl.requestFullscreen ||
        docEl.mozRequestFullScreen ||
        docEl.webkitRequestFullScreen ||
        docEl.msRequestFullscreen;
      const cancelFullScreen =
        doc.exitFullscreen ||
        doc.mozCancelFullScreen ||
        doc.webkitExitFullscreen ||
        doc.msExitFullscreen;

      if (!doc.fullscreenElement && requestFullScreen) {
        requestFullScreen.call(docEl);
        this.isFullscreen = true;
      } else if (cancelFullScreen) {
        cancelFullScreen.call(doc);
        this.isFullscreen = false;
      }
    },
    setPieData() {
      $(document).ready(() => {
        var chartDom = this.$refs.firstMain;
        var myChart = this.$echarts.init(chartDom);
        var option;
        myChart.dispatchAction({
          type: "downplay",
          seriesIndex: 0,
          dataIndex: this.currentIndex,
        });
        this.currentIndex = (this.currentIndex + 1) % this.pieData.length;
        myChart.dispatchAction({
          type: "highlight",
          seriesIndex: 0,
          dataIndex: this.currentIndex,
        });
        var option = {
          tooltip: {
            trigger: "item",
            formatter: "{a} <br/>{b}:{c} ({d}%)",
          },
          toolbox: {
            show: true,
          },
          calculable: true,
          legend: {
            orient: "vertical",
            icon: "circle",
            left: 0,
            x: "center",
            data: this.pieData.map((item) => item.name),
            textStyle: {
              color: "#fff",
            },
          },
          series: [
            {
              name: "年龄占比",
              type: "pie",
              radius: [20, 50],
              roseType: "area",
              center: ["50%", "55%"],

              label: {
                show: true,
              },
              emphasis: {
                itemStyle: {
                  shadowBlur: 10,
                  shadowOffsetX: 0,
                  label: {
                    show: true,
                    fontWeight: "bold",
                  },
                },
              },
              data: this.pieData,
            },
          ],
        };
        // 图表联动：点击年龄区段时按年龄筛选
        myChart.off("click");
        myChart.on("click", (params) => {
          const name = params.name;
          const mapping = {
            "0-10岁": "0-10",
            "10-20岁": "10-20",
            "20-30岁": "20-30",
            "30-40岁": "30-40",
            "40-50岁": "40-50",
            "50-60岁": "50-60",
            "60岁以上": "60+",
          };
          this.filters.age = mapping[name] ? [mapping[name]] : [];
          this.applyFilters();
        });
        option && myChart.setOption(option);
      });
    },
    changeData(x) {
      var st = x[0];
      for (var i = 0; i < x.length - 1; i++) {
        x[i] = x[i + 1];
      }
      x[x.length - 1] = st;
    },
    getSeriesData() {
      const series = [];
      this.circleData.forEach((item, index) => {
        if (index < 5) {
          series.push({
            name: item.name,
            type: "pie",
            clockWise: false,
            hoverAnimation: false,
            radius: [73 - index * 15 + "%", 68 - index * 15 + "%"],
            center: ["50%", "50%"],
            label: {
              show: false,
            },
            data: [
              {
                value: item.value,
                name: item.name,
              },
              {
                value: 3,
                itemStyle: {
                  color: "rgba(0,0,0,0)",
                  borderWidth: 0,
                },
                tooltip: {
                  show: false,
                },
                hoverAnimation: false,
              },
            ],
          });
        }
      });
      return series;
    },
    randomColor() {
      const r = Math.floor(Math.random() * 255);
      const g = Math.floor(Math.random() * 255);
      const b = Math.floor(Math.random() * 255);
      return `rgb(${r},${g},${b})`;
    },
    setWordData() {
      var chartDom = this.$refs.thirdMain;
      var myChart = this.$echarts.init(chartDom);
      var option = {
        series: {
          type: "wordCloud",
          sizeRange: [20, 40],
          gridSize: 0,
          rotationRange: [0, 0],
          layoutAnimation: true,
          textStyle: {
            color: this.randomColor,
          },
          emphasis: {
            textStyle: {
              fontWeight: "bold",
              color: "#fff",
            },
          },
          data: this.wordData,
        },
      };
      option && myChart.setOption(option);
    },
    setCircleData() {
      $(document).ready(() => {
        var newData = this.circleData;
        this.changeData(newData);
        this.circleData = newData;
        var chartDom = document.getElementById("secondMian");
        var myChart = this.$echarts.init(chartDom);
        var option = {
          legend: {
            show: true,
            icon: "circle",
            top: "8%",
            left: "10%",
            data: this.circleData.map((item) => item.name),
            width: -5,
            itemWidth: 10,
            itemHeight: 10,
            itemGap: 6,
            textStyle: {
              fontSize: 12,
              lineHeight: 5,
              color: "#ffffff",
            },
          },
          tooltip: {
            show: true,
            trigger: "item",
            formatter: "{b}<br>{c}({d}%)",
          },
          yAxis: [
            {
              type: "category",
              inverse: true,
              axisLine: {
                show: false,
              },
            },
          ],
          xAxis: [
            {
              show: true,
            },
          ],
          series: this.getSeriesData(),
        };
        option && myChart.setOption(option);
      });
    },
    setLastData() {
      $(document).ready(() => {
        var newData = this.lastData;
        this.changeData(newData.xData);
        this.changeData(newData.y1Data);
        this.changeData(newData.y2Data);
        this.lastData = newData;
        var chartDom = this.$refs.lastMain;
        var myChart = this.$echarts.init(chartDom);
        var option = {
          tooltip: {
            trigger: "axis",
            backgroundColor: "rgba(255,255,255,0.1)",
            axisPointer: {
              type: "shadow",
              label: {
                show: true,
                backgroundColor: "#7B7DDC",
              },
            },
          },
          dataZoom: [
            {
              type: "slider",
              start: 0,
              end: 80,
              show: false,
            },
          ],
          legend: {
            data: ["身高", "体重"],
            textStyle: {
              color: "#B4B4B4",
            },
            top: "0%",
          },
          grid: {
            x: "8%",
            width: "85%",
            height: "87%",
            y: "4%",
          },

          xAxis: {
            data: this.lastData.xData,
            axisLine: {
              lineStyle: {
                color: "#B4B4B4",
              },
            },
            axisLabel: {
              show: true,
              interval: 0,
            },
            axisTick: {
              show: false,
            },
          },
          yAxis: [
            {
              splitLine: { show: false },
              axisLine: {
                lineStyle: {
                  color: "#B4B4B4",
                },
              },

              axisLabel: {
                formatter: "{value} ",
              },
            },
            {
              splitLine: { show: false },
              axisLine: {
                lineStyle: {
                  color: "#B4B4B4",
                },
              },
              axisLabel: {
                formatter: "{value} ",
              },
            },
          ],
          series: [
            {
              name: "身高",
              type: "line",
              smooth: true,
              showAllSymbol: true,
              symbol: "emptyCircle",
              symbolSize: 8,
              yAxisIndex: 1,
              // areaStyle: {},
              itemStyle: {
                normal: {
                  barBorderRadius: 5,
                  color: new this.$echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: "#5C4033" },
                    { offset: 1, color: "#FAEBD7" },
                  ]),
                },
              },
              data: this.lastData.y1Data,
            },
            {
              name: "体重",
              type: "bar",
              barWidth: "60%",
              itemStyle: {
                normal: {
                  barBorderRadius: 5,
                  color: new this.$echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: "#082e53" },
                    { offset: 1, color: "white" },
                  ]),
                },
              },
              data: this.lastData.y2Data,
            },
          ],
        };
        // 图表联动：点击疾病类型时按疾病筛选
        myChart.off("click");
        myChart.on("click", (params) => {
          const diseaseName = params.name;
          this.filters.disease = diseaseName ? [diseaseName] : [];
          this.applyFilters();
        });
        option && myChart.setOption(option);
      });
    },
    setConfig1() {
      // 使用滚动窗口控制柱子数量，避免超出框外
      const full = this.fullDiseaseStats || [];
      const total = full.length;
      if (!total) {
        this.config1 = { data: [], showValue: true };
        return;
      }

      const windowSize = Math.min(this.diseaseWindowSize, total);
      const start = this.diseaseScrollIndex % total;
      const windowData = [];
      for (let i = 0; i < windowSize; i++) {
        const idx = (start + i) % total;
        windowData.push(full[idx]);
      }
      this.diseaseScrollIndex = (start + 1) % total;

      this.config1 = {
        data: windowData,
        showValue: true,
      };
    },
    // 从后端拉取最新数据（不改后端）
    async fetchHomeData() {
      const res = await this.$http.get("/getHomeData");
      const data = res.data;
      // 原始病例列表
      this.allCasesData = data.casesData || [];
      this.casesData = this.allCasesData;

      // 为筛选下拉准备疾病与时间选项
      const diseaseSet = new Set();
      const timeSet = new Set();
      this.allCasesData.forEach((row) => {
        if (row[1]) diseaseSet.add(row[1]);
        if (row[4]) timeSet.add(row[4]);
      });
      this.diseaseOptions = Array.from(diseaseSet);
      this.timeOptions = Array.from(timeSet);

      // 基于病例列表前端重算统计，支持筛选/联动
      this.rebuildStatsFromCases(this.allCasesData);
    },
  },
  async created() {
    $(document).ready(async () => {
      setInterval(() => {
        this.setPieData();
        this.setConfig1();
        this.setWordData();
      }, 1000);
      setInterval(() => {
        this.setCircleData();
      }, 3000);
      setInterval(() => {
        this.setLastData();
      }, 2000);
      // 周期性从后端拉取最新数据，实现前端实时刷新
      setInterval(() => {
        this.fetchHomeData();
      }, 30000);
    });
  },
  async mounted() {
    await this.fetchHomeData();
  },
  components: {
    LeftTop,
  },
};

</script>

<style lang="less" scoped>
.loading {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
}

.cent-1-content {
  padding: 20px;
  display: flex;
}

.right-content {
  margin-left: 30px;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
}

.right-content div {
  display: flex;
  font-size: 15px;
  align-items: center;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}

.fade-enter,
.fade-leave-to {
  opacity: 0;
}

.cents {
  display: flex;
  flex-direction: column;
  flex: 6;
  height: 100%;
}

.above {
  display: flex;
  flex: 3;
}

.aboveOne {
  display: flex;
  flex-direction: column;
  flex: 3;
  justify-content: space-evenly;
  align-items: center;
  margin-left: -70px;
}

.aboveTwo {
  display: flex;
  flex-direction: column;
  flex: 2;
}

.cent {
  width: 850px;
  height: 300px;
}

.cent-1 {
  margin: 10px;
  color: aliceblue;
  width: 500px;
  height: 220px;
}

.left {
  display: flex;
  flex-direction: column;
  flex: 4;
  height: 100%;
}

.left-1 {
  margin: 10px 15px 0 15px;
  color: aliceblue;
  width: 550px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.left-2 {
  margin: 15px;
  color: aliceblue;
  width: 530px;
  display: flex;
  flex-direction: column;
}

.naca {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.home {
  width: 100%;
  height: calc(100vh - 80px);
}

.outer-border {
  width: 100%;
  height: 100%;
}

.naca .index-header {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.naca .index-header div {
  display: flex;
  justify-content: center;
  align-items: center;
}

.naca .index-content {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  margin-top: 10px;
  height: calc(100% - 140px);
}

.filter-bar {
  margin-top: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #e6f7ff;
  z-index: 2;
}

.filter-group {
  display: flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 16px;
  border: 1px solid rgba(86, 138, 234, 0.8);
  background: rgba(6, 25, 60, 0.8);
  box-shadow: 0 0 8px rgba(86, 138, 234, 0.6);
}

.filter-label {
  margin-right: 6px;
  color: #9ad6ff;
}

.filter-dropdown {
  position: relative;
  cursor: pointer;
}

.filter-header {
  display: flex;
  align-items: center;
}

.filter-display {
  min-width: 90px;
  max-width: 180px;
  padding: 2px 6px;
  font-size: 12px;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.long-display {
  min-width: 140px;
  max-width: 220px;
}

.filter-arrow {
  margin-left: 4px;
  font-size: 10px;
  color: #9ad6ff;
}

.filter-panel {
  position: absolute;
  top: 32px;
  left: 0;
  z-index: 10;
  min-width: 120px;
  max-height: 220px;
  padding: 6px 8px;
  background: rgba(3, 14, 40, 0.96);
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(86, 138, 234, 0.9);
  border: 1px solid rgba(86, 138, 234, 0.9);
  overflow-y: auto;
}

.filter-panel-item {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #e6f7ff;
  margin-bottom: 4px;
}

.filter-panel-item input {
  margin-right: 4px;
}

.filter-reset,
.fullscreen-btn {
  padding: 4px 12px;
  border-radius: 16px;
  border: 1px solid rgba(86, 138, 234, 0.9);
  background: linear-gradient(
    90deg,
    rgba(29, 75, 167, 0.9),
    rgba(33, 119, 203, 0.9)
  );
  color: #e6f7ff;
  cursor: pointer;
  font-size: 12px;
  box-shadow: 0 0 8px rgba(86, 138, 234, 0.8);
}

.filter-reset:hover,
.fullscreen-btn:hover {
  background: linear-gradient(
    90deg,
    rgba(50, 132, 255, 0.95),
    rgba(108, 192, 255, 0.95)
  );
}

.bg {
  width: 100%;
  height: 45rem;
  background-color: black;
  position: relative;
}

.title {
  color: #3f96a5;
  font-size: 18px;
  margin-top: -20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  font-weight: bold;
}

.height-weight-note {
  margin-top: 4px;
  font-size: 12px;
  color: #8898c2;
}

.content {
  display: flex;
  align-items: center;
  justify-content: space-evenly;
  width: 100%;
}

.content-word {
  width: 140px;
  height: 130px;
  background: #11193e;
  border-radius: 40px;
  border: 1px solid #3d3d3d;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.content-word-item {
  margin-left: 19px;
  margin-bottom: 10px;
  img {
    width: 20px;
    height: 20px;
  }
}
.content-word-item-title {
  font-size: 18px;
}
.content-word-item-content {
  margin-top: 5px;

  display: flex;
  align-items: center;
}
.row_list {
  list-style: none;
}
.cases_list {
  width: 100%;
  height: 220px;
  overflow: auto;
  scrollbar-width: thin; /* Firefox */
  scrollbar-color: #52a2e4 transparent;
}
.cases_list li {
  display: grid;
  -ms-grid-columns: 30px 110px 60px 60px 60px 50px 100px;
  grid-template-columns: 30px 110px 60px 60px 60px 50px 100px;
  cursor: pointer;
  margin-left: 23px;
  text-align: center;
  line-height: 30px;
  color: rgb(238, 236, 236);
}
.list_time {
  height: 30px;
  overflow: auto;
}
.list_time::-webkit-scrollbar {
  display: none;
}
/* 美化病例列表滚动条（Webkit 内核） */
.cases_list::-webkit-scrollbar {
  width: 6px;
}
.cases_list::-webkit-scrollbar-track {
  background: transparent;
}
.cases_list::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #52a2e4, #1b2d4a);
  border-radius: 3px;
}
</style>