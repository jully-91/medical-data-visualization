import axios from "axios";


// 默认 /api 走同源代理：
//   开发环境 -> vue.config.js 的 devServer.proxy 转发到 localhost:5000
//   生产环境 -> deploy/serve_dist.py 内置代理转发到后端，换 IP 无需重新 build
// 如需绕过代理直连后端，构建时设置 VUE_APP_API_BASE_URL=http://服务器IP:5000（注意不带 /api）
const axiosInstance = axios.create({
    baseURL: process.env.VUE_APP_API_BASE_URL || '/api',
    timeout:10000,
})

axiosInstance.interceptors.request.use(
    (config) => {
        return config;
    },
    (error) => {
        return Promise.reject(error);
    } 
);
axiosInstance.interceptors.response.use(
    (response) => {
        return response.data;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export default axiosInstance;