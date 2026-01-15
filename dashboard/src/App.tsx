import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { ReactFlowProvider } from "reactflow";
import AppShell, { type NavItem } from "./components/AppShell";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import WorkflowBuilderPage from "./features/builder/pages/WorkflowBuilderPage";
import WorkflowsPage from "./pages/WorkflowsPage";
import HubWorkflowsPage from "./pages/HubWorkflowsPage";
import PackageCenterPage from "./features/packages/pages/PackageCenterPage";
import AuditLogPage from "./features/admin/pages/AuditLogPage";
import UsersPage from "./features/admin/pages/UsersPage";
import WorkersPage from "./features/admin/pages/WorkersPage";
import LoginPage from "./features/auth/pages/LoginPage";
import AccountPage from "./features/account/pages/AccountPage";
import { useAuthStore } from "@store/authSlice";
import { useEffect, useMemo, useRef, useState } from "react";
import { RunSseSubscriptions } from "./lib/sse/RunSseSubscriptions";
import { NodeSseSubscriptions } from "./lib/sse/NodeSseSubscriptions";
import { WorkerSseSubscriptions } from "./lib/sse/WorkerSseSubscriptions";
import { MessageProvider } from "./components/MessageCenter";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "./components/LanguageSwitcher";

const NotFound = () => {
  const { t } = useTranslation();
  return (
    <div className="card">
      <h2>404</h2>
      <p>{t("common.pageNotFound")}</p>
    </div>
  );
};

const buildDashboardNav = (t: (key: string) => string): NavItem[] => [
  {
    to: "/workflows",
    label: t("nav.workflows"),
    match: (pathname) => pathname === "/workflows"
  },
  {
    to: "/hub/workflows",
    label: t("nav.hubLibrary"),
    match: (pathname) => pathname.startsWith("/hub/workflows")
  },
  {
    to: "/packages",
    label: t("nav.packageCenter"),
    match: (pathname) => pathname === "/packages"
  }
];

const AuthHeader = () => {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const isAdmin = useAuthStore((state) => state.hasRole(["admin"]));
  const canViewPackages = useAuthStore((state) =>
    state.hasRole(["admin", "workflow.viewer", "workflow.editor"])
  );
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  if (!user) {
    return null;
  }

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  useEffect(() => {
    if (!open) {
      return;
    }
    const handleClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const handleAdminNavigate = () => {
    setOpen(false);
    navigate("/admin/users");
  };

  const handleMyPackagesNavigate = () => {
    setOpen(false);
    navigate("/packages?tab=mine");
  };

  const handleAccountNavigate = () => {
    setOpen(false);
    navigate("/account");
  };

  const handleLogoutClick = () => {
    setOpen(false);
    handleLogout();
  };

  return (
    <div className="auth-status" ref={menuRef}>
      <button
        className="auth-status__trigger"
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="auth-status__name">{user.displayName}</span>
        <span className="auth-status__chevron" aria-hidden="true">
          ▾
        </span>
      </button>
      {open && (
        <div className="auth-menu" role="menu">
          <button className="auth-menu__item" type="button" onClick={handleAccountNavigate}>
            {t("auth.personalPanel")}
          </button>
          {canViewPackages && (
            <button className="auth-menu__item" type="button" onClick={handleMyPackagesNavigate}>
              {t("auth.myPackages")}
            </button>
          )}
          {isAdmin && (
            <button className="auth-menu__item" type="button" onClick={handleAdminNavigate}>
              {t("auth.adminConsole")}
            </button>
          )}
          <button className="auth-menu__item" type="button" onClick={handleLogoutClick}>
            {t("auth.logout")}
          </button>
        </div>
      )}
    </div>
  );
};

const HeaderControls = () => (
  <>
    <LanguageSwitcher />
    <AuthHeader />
  </>
);

const DashboardRoute = ({
  children,
  navItems,
}: React.PropsWithChildren<{ navItems: NavItem[] }>) => (
  <AppShell navItems={navItems} rightSlot={<HeaderControls />}>
    {children}
  </AppShell>
);

const RunsRoute = ({ navItems }: { navItems: NavItem[] }) => (
  <DashboardRoute navItems={navItems}>
    <RunsPage />
    <Outlet />
  </DashboardRoute>
);

const AdminLayout = ({ children }: React.PropsWithChildren) => {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const adminLinks = useMemo(
    () => [
      { to: "/admin/users", label: t("admin.users") },
      { to: "/admin/audit", label: t("admin.auditLog") },
      { to: "/admin/workers", label: t("admin.workers") },
    ],
    [i18n.language, t]
  );

  return (
    <div className="admin-layout">
      <aside className="admin-layout__sidebar">
        <div className="admin-layout__header">
          <h3>{t("admin.title")}</h3>
          <p className="text-subtle">{t("admin.subtitle")}</p>
        </div>
        <div className="admin-layout__nav">
          {adminLinks.map((link) => {
            const isActive = location.pathname === link.to;
            return (
              <button
                key={link.to}
                type="button"
                className={`admin-layout__link ${isActive ? "admin-layout__link--active" : ""}`}
                onClick={() => navigate(link.to)}
              >
                {link.label}
              </button>
            );
          })}
        </div>
      </aside>
      <div className="admin-layout__content">{children}</div>
    </div>
  );
};

const AdminRoute = ({ children }: React.PropsWithChildren) => {
  const { t } = useTranslation();
  const isAdmin = useAuthStore((state) => state.hasRole(["admin"]));
  const navItems = useMemo(() => buildDashboardNav(t), [t]);

  if (!isAdmin) {
    return (
      <AppShell navItems={navItems} rightSlot={<HeaderControls />}>
        <div className="card stack">
          <h2>{t("auth.adminAccessRequired")}</h2>
          <p className="text-subtle">{t("auth.adminAccessHint")}</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell navItems={navItems} rightSlot={<HeaderControls />}>
      <AdminLayout>{children}</AdminLayout>
    </AppShell>
  );
};

const WorkflowBuilderRoute = () => {
  const { t, i18n } = useTranslation();
  const { workflowId = "" } = useParams<{ workflowId: string }>();
  const builderNav = useMemo(() => {
    const nav = buildDashboardNav(t);
    nav.push({
      to: `/workflows/${workflowId}`,
      label: t("nav.builder"),
      match: (pathname) => pathname === `/workflows/${workflowId}`
    });
    return nav;
  }, [workflowId, i18n.language, t]);

  return (
    <ReactFlowProvider>
      <AppShell navItems={builderNav} variant="builder" rightSlot={<HeaderControls />}>
        <WorkflowBuilderPage />
      </AppShell>
    </ReactFlowProvider>
  );
};

const RequireAuth = ({ children }: React.PropsWithChildren) => {
  const { t } = useTranslation();
  const initialized = useAuthStore((state) => state.initialized);
  const token = useAuthStore((state) => state.token);
  const hydrate = useAuthStore((state) => state.hydrate);

  useEffect(() => {
    if (!initialized) {
      hydrate();
    }
  }, [initialized, hydrate]);

  if (!initialized) {
    return <div className="card">{t("auth.checkingSession")}</div>;
  }
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  const { t, i18n } = useTranslation();
  const navItems = useMemo(() => buildDashboardNav(t), [i18n.language, t]);

  return (
    <MessageProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <RunSseSubscriptions />
        <NodeSseSubscriptions />
        <WorkerSseSubscriptions />
        <Routes>
          <Route path="/" element={<Navigate to="/workflows" replace />} />
          <Route
            path="/runs"
            element={
              <RequireAuth>
                <RunsRoute navItems={navItems} />
              </RequireAuth>
            }
          >
            <Route path=":runId" element={<RunDetailPage />} />
          </Route>
          <Route
            path="/workflows"
            element={
              <RequireAuth>
                <DashboardRoute navItems={navItems}>
                  <WorkflowsPage />
                </DashboardRoute>
              </RequireAuth>
            }
          />
          <Route
            path="/hub/workflows"
            element={
              <RequireAuth>
                <DashboardRoute navItems={navItems}>
                  <HubWorkflowsPage />
                </DashboardRoute>
              </RequireAuth>
            }
          />
          <Route
            path="/account"
            element={
              <RequireAuth>
                <DashboardRoute navItems={navItems}>
                  <AccountPage />
                </DashboardRoute>
              </RequireAuth>
            }
          />
          <Route
            path="/workflows/:workflowId"
            element={
              <RequireAuth>
                <WorkflowBuilderRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/packages"
            element={
              <RequireAuth>
                <DashboardRoute navItems={navItems}>
                  <PackageCenterPage />
                </DashboardRoute>
              </RequireAuth>
            }
          />
          <Route path="/store" element={<Navigate to="/packages" replace />} />
          <Route path="/admin" element={<Navigate to="/admin/users" replace />} />
          <Route
            path="/admin/users"
            element={
              <RequireAuth>
                <AdminRoute>
                  <UsersPage />
                </AdminRoute>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/audit"
            element={
              <RequireAuth>
                <AdminRoute>
                  <AuditLogPage />
                </AdminRoute>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/workers"
            element={
              <RequireAuth>
                <AdminRoute>
                  <WorkersPage />
                </AdminRoute>
              </RequireAuth>
            }
          />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="*"
            element={
              <RequireAuth>
                <DashboardRoute>
                  <NotFound />
                </DashboardRoute>
              </RequireAuth>
            }
          />
          <Route path="/audit" element={<Navigate to="/admin/audit" replace />} />
          <Route path="/users" element={<Navigate to="/admin/users" replace />} />
        </Routes>
      </BrowserRouter>
    </MessageProvider>
  );
}

export default App;
