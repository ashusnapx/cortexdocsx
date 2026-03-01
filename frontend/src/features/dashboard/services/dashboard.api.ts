import { apiClient } from "@/core/api/client";
import { ListDocumentsResponse, UploadResponse } from "../types";
import { AppConfig, MOCK_APP_CONFIG } from "@/core/config/env";

export const DashboardAPI = {
  /**
   * Fetches dynamic UI capability config from the backend.
   */
  getConfig: async (): Promise<AppConfig> => {
    // Return MOCK_APP_CONFIG gracefully since the /config endpoint isn't implemented in the backend yet
    return Promise.resolve(MOCK_APP_CONFIG);
  },

  listDocuments: async (): Promise<ListDocumentsResponse> => {
    return await apiClient.get<never, ListDocumentsResponse>("/documents");
  },

  uploadDocument: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    return await apiClient.post<never, UploadResponse>(
      "/documents/upload",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
        // extended timeout for uploads
        timeout: 120000,
      },
    );
  },
};
