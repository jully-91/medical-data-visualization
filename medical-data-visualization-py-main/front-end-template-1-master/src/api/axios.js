import axios from "axios";


const axiosInstance = axios.create({
    baseURL: 'http://localhost:8080/api',
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