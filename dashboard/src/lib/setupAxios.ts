import axios from "axios";

const baseURL = import.meta.env.VITE_SCHEDULER_BASE_URL ?? "http://127.0.0.1:8080";
axios.defaults.baseURL = baseURL;

const token = import.meta.env.VITE_SCHEDULER_TOKEN ?? "dev-token";
axios.defaults.headers.common.Authorization = `Bearer ${token}`;
