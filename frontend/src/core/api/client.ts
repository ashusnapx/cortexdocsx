import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // If the backend returned a structured error, extract it.
    const message =
      error.response?.data?.error?.message ||
      error.message ||
      "Unknown error occurred";
    return Promise.reject(new Error(message));
  },
);
