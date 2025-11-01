import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import "./App.css";
import AppShell, { type NavItem } from "./components/AppShell";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import WorkflowBuilderPage from "./pages/WorkflowBuilderPage";
import WorkflowsPage from "./pages/WorkflowsPage";

const NotFound = () => (
  <div className="card">
    <h2>404</h2>
    <p>Page not found.</p>
  </div>
);

const dashboardNav: NavItem[] = [
  {
    to: "/runs",
    label: "Runs",
    match: (pathname) => pathname === "/runs" || pathname.startsWith("/runs/")
  },
  {
    to: "/workflows",
    label: "Workflows",
    match: (pathname) => pathname === "/workflows"
  },
  { to: "/workers", label: "Workers", disabled: true }
];

const DashboardRoute = ({ children }: React.PropsWithChildren) => (
  <AppShell navItems={dashboardNav}>{children}</AppShell>
);

const WorkflowBuilderRoute = () => {
  const { workflowId = "" } = useParams<{ workflowId: string }>();
  const builderNav: NavItem[] = [
    ...dashboardNav,
    {
      to: `/workflows/${workflowId}`,
      label: "Builder",
      match: (pathname) => pathname === `/workflows/${workflowId}`
    }
  ];

  return (
    <AppShell navItems={builderNav} variant="builder">
      <WorkflowBuilderPage />
    </AppShell>
  );
};

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Navigate to="/runs" replace />} />
        <Route
          path="/runs"
          element={
            <DashboardRoute>
              <RunsPage />
            </DashboardRoute>
          }
        />
        <Route
          path="/runs/:runId"
          element={
            <DashboardRoute>
              <RunDetailPage />
            </DashboardRoute>
          }
        />
        <Route
          path="/workflows"
          element={
            <DashboardRoute>
              <WorkflowsPage />
            </DashboardRoute>
          }
        />
        <Route path="/workflows/:workflowId" element={<WorkflowBuilderRoute />} />
        <Route
          path="*"
          element={
            <DashboardRoute>
              <NotFound />
            </DashboardRoute>
          }
        />
      </Routes>
      <ReactQueryDevtools initialIsOpen={false} position="bottom" />
    </BrowserRouter>
  );
}

export default App;
