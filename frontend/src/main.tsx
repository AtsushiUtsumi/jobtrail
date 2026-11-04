import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { toast, Toaster } from "sonner";
import { ApiError } from "@/api/client";
import { Layout } from "@/components/Layout";
import { ApplicationDetailPage } from "@/pages/ApplicationDetail";
import { ApplicationsPage } from "@/pages/Applications";
import { CompaniesPage } from "@/pages/Companies";
import { CompanyDetailPage } from "@/pages/CompanyDetail";
import { DashboardPage } from "@/pages/Dashboard";
import { DocumentsPage } from "@/pages/Documents";
import { PastePage } from "@/pages/Paste";
import { SkillProfilePage } from "@/pages/SkillProfile";
import "./index.css";

const POLLING_INTERVAL_MS = 10_000;

const queryClient: QueryClient = new QueryClient({
  defaultOptions: { queries: { refetchInterval: POLLING_INTERVAL_MS, retry: 1 } },
  mutationCache: new MutationCache({
    onSuccess: () => queryClient.invalidateQueries(),
    onError: (error) => {
      if (error instanceof ApiError && error.code === "CONFLICT") {
        queryClient.invalidateQueries();
        toast.warning("他の更新と競合したため、最新の内容を再取得しました。");
        return;
      }
      if (error instanceof ApiError) {
        queryClient.invalidateQueries();
        toast.error(error.message, { description: error.hint });
        return;
      }
      toast.error(error.message);
    },
  }),
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="applications" element={<ApplicationsPage />} />
            <Route path="applications/:id" element={<ApplicationDetailPage />} />
            <Route path="companies" element={<CompaniesPage />} />
            <Route path="companies/:id" element={<CompanyDetailPage />} />
            <Route path="documents" element={<DocumentsPage />} />
            <Route path="skill-profile" element={<SkillProfilePage />} />
            <Route path="paste" element={<PastePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  </StrictMode>,
);
