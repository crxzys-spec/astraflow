import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import AppShell, { type NavItem } from "./components/AppShell";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import WorkflowBuilderPage from "./pages/WorkflowBuilderPage";
import WorkflowsPage from "./pages/WorkflowsPage";
import StorePage from "./pages/StorePage";
import AuditLogPage from "./pages/AuditLogPage";
import UsersPage from "./pages/UsersPage";
import WorkersPage from "./pages/WorkersPage";
import LoginPage from "./pages/LoginPage";
import { useAuthStore } from "./features/auth/store";
import { useEffect, useMemo, useRef, useState } from "react";

const NotFound = () => (
  <div className="card">
    <h2>404</h2>
    <p>Page not found.</p>
  </div>
);

const baseNavItems: NavItem[] = [
  {
    to: "/workflows",
    label: "Workflows",
    match: (pathname) => pathname === "/workflows"
  },
  {
    to: "/store",
    label: "Store",
    match: (pathname) => pathname === "/store"
  }
];

const buildDashboardNav = (): NavItem[] => [...baseNavItems];

const AuthHeader = () => {
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
    navigate("/store?tab=mine");
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
          {canViewPackages && (
            <button className="auth-menu__item" type="button" onClick={handleMyPackagesNavigate}>
              My Packages
            </button>
          )}
          {isAdmin && (
            <button className="auth-menu__item" type="button" onClick={handleAdminNavigate}>
              Admin Console
            </button>
          )}
          <button className="auth-menu__item" type="button" onClick={handleLogoutClick}>
            Logout
          </button>
        </div>
      )}
    </div>
  );
};

const DashboardRoute = ({ children }: React.PropsWithChildren) => {
  const navItems = useMemo(() => buildDashboardNav(), []);
  return (
    <AppShell navItems={navItems} rightSlot={<AuthHeader />}>
      {children}
    </AppShell>
  );
};

const RunsRoute = () => (
  <DashboardRoute>
    <RunsPage />
    <Outlet />
  </DashboardRoute>
);

const adminLinks = [
  { to: "/admin/users", label: "Users" },
  { to: "/admin/audit", label: "Audit Log" },
  { to: "/admin/workers", label: "Workers" },
];

const AdminLayout = ({ children }: React.PropsWithChildren) => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="admin-layout">
      <aside className="admin-layout__sidebar">
        <div className="admin-layout__header">
          <h3>Admin</h3>
          <p className="text-subtle">Manage accounts & compliance</p>
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
  const isAdmin = useAuthStore((state) => state.hasRole(["admin"]));
  const navItems = useMemo(() => buildDashboardNav(), []);

  if (!isAdmin) {
    return (
      <AppShell navItems={navItems} rightSlot={<AuthHeader />}>
        <div className="card stack">
          <h2>Admin Access Required</h2>
          <p className="text-subtle">You need the admin role to view this section.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell navItems={navItems} rightSlot={<AuthHeader />}>
      <AdminLayout>{children}</AdminLayout>
    </AppShell>
  );
};

const WorkflowBuilderRoute = () => {
  const { workflowId = "" } = useParams<{ workflowId: string }>();
  const builderNav = useMemo(() => {
    const nav = buildDashboardNav();
    nav.push({
      to: `/workflows/${workflowId}`,
      label: "Builder",
      match: (pathname) => pathname === `/workflows/${workflowId}`
    });
    return nav;
  }, [workflowId]);

  return (
    <AppShell navItems={builderNav} variant="builder" rightSlot={<AuthHeader />}>
      <WorkflowBuilderPage />
    </AppShell>
  );
};

const RequireAuth = ({ children }: React.PropsWithChildren) => {
  const initialized = useAuthStore((state) => state.initialized);
  const token = useAuthStore((state) => state.token);
  const hydrate = useAuthStore((state) => state.hydrate);

  useEffect(() => {
    if (!initialized) {
      hydrate();
    }
  }, [initialized, hydrate]);

  if (!initialized) {
    return <div className="card">Checking session...</div>;
  }
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Navigate to="/workflows" replace />} />
        <Route
          path="/runs"
          element={
            <RequireAuth>
              <RunsRoute />
            </RequireAuth>
          }
        >
          <Route path=":runId" element={<RunDetailPage />} />
        </Route>
        <Route
          path="/workflows"
          element={
            <RequireAuth>
              <DashboardRoute>
                <WorkflowsPage />
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
          path="/store"
          element={
            <RequireAuth>
              <DashboardRoute>
                <StorePage />
              </DashboardRoute>
            </RequireAuth>
          }
        />
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
  );
}

export default App;
