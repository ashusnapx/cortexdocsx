import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DashboardAPI } from "../services/dashboard.api";
import { toast } from "sonner";

export const dashboardKeys = {
  all: ["dashboard"] as const,
  config: () => [...dashboardKeys.all, "config"] as const,
  documents: () => [...dashboardKeys.all, "documents"] as const,
};

export function useAppConfig() {
  return useQuery({
    queryKey: dashboardKeys.config(),
    queryFn: DashboardAPI.getConfig,
    staleTime: Infinity, // Configuration rarely changes during a session
  });
}

export function useDocuments() {
  return useQuery({
    queryKey: dashboardKeys.documents(),
    queryFn: DashboardAPI.listDocuments,
    refetchInterval: (query) => {
      // If any document is still processing, poll every 3 seconds to update the UI
      const docs = query.state?.data?.data?.documents || [];
      const hasProcessing = docs.some(
        (d) => d.status === "PENDING" || d.status === "PROCESSING",
      );
      return hasProcessing ? 3000 : false;
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: DashboardAPI.uploadDocument,
    onMutate: () => {
      // Show an immediate toast indicating progress has started
      toast.loading("Uploading and parsing document...", {
        id: "upload-toast",
      });
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(
          `Success! ${data.data?.ingestion_job.page_count} pages processed.`,
          {
            id: "upload-toast",
          },
        );
        // Invalidate the documents list so the UI refetches the new list
        queryClient.invalidateQueries({ queryKey: dashboardKeys.documents() });
      } else {
        toast.error(`Upload failed: ${data.error?.message}`, {
          id: "upload-toast",
        });
      }
    },
    onError: (error) => {
      toast.error(error.message || "Failed to upload document", {
        id: "upload-toast",
      });
    },
  });
}
