import Vue from 'vue'
import VueRouter from 'vue-router'
import Index from '../views/Index.vue'
import Pred from '../views/Pred.vue'
import TableData from '../views/TableData.vue'
import Report from '../views/Report.vue'
import AiChat from '../views/AiChat.vue'

Vue.use(VueRouter)

const routes = [{
    path: '/',
    name: 'Index',
    component: Index,
    meta: { name: '首页' }
}, {
    path: '/pred',
    name: 'Pred',
    component: Pred,
    meta: { name: "在线预测" }
}, 
{
    path: '/tableData',
    name: 'TableData',
    component: TableData,
    meta: { name: "数据管理" }
},
{
    path: '/report',
    name: 'Report',
    component: Report,
    meta: { name: "报告生成" }
},
{
    path: '/ai-chat',
    name: 'AiChat',
    component: AiChat,
    meta: { name: "AI医疗助手" }
}]

const router = new VueRouter({
    mode: 'history',
    base: process.env.BASE_URL,
    routes
})

export default router