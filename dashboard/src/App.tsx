import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import "./App.css";
import Layout from "./components/Layout";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import WorkflowBuilderPage from "./pages/WorkflowBuilderPage";

const NotFound = () => (
  <div className="card">
    <h2>404</h2>
    <p>Page not found.</p>
  </div>
);

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/runs" replace />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
          <Route path="/workflows/:workflowId" element={<WorkflowBuilderPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
      <ReactQueryDevtools initialIsOpen={false} position="bottom" />
    </BrowserRouter>
  );
}

export default App;


