import type { PropsWithChildren } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useToolbarStore } from "../features/builder/hooks/useToolbar";

export interface NavItem {
  to: string;
  label: string;
  disabled?: boolean;
  match?: (pathname: string) => boolean;
}

interface AppShellProps extends PropsWithChildren {
  navItems: NavItem[];
  variant?: "default" | "builder";
  rightSlot?: React.ReactNode;
}

const AppShell = ({ children, navItems, variant = "default", rightSlot }: AppShellProps) => {
  const location = useLocation();
  const toolbarContent = useToolbarStore((state) => state.content);

  return (
    <div className={`app-shell app-shell--${variant}`}>
      <header className="app-shell__header">
        <div className="app-shell__brand">
          <span className="app-shell__logo">AstraFlow</span>
          <span className="app-shell__siglum">Orion</span>
        </div>
        <nav className="app-shell__nav">
          {navItems.map((item) => {
            const isActive = item.match ? item.match(location.pathname) : location.pathname === item.to;
            const className = [
              "app-shell__nav-link",
              isActive ? "app-shell__nav-link--active" : "",
              item.disabled ? "app-shell__nav-link--disabled" : ""
            ]
              .filter(Boolean)
              .join(" ");
            return item.disabled ? (
              <span key={item.to} className={className} aria-disabled="true">
                {item.label}
              </span>
            ) : (
              <NavLink key={item.to} to={item.to} className={className}>
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="app-shell__actions">
          {toolbarContent && <div className="app-shell__toolbar-inline">{toolbarContent}</div>}
          <div className="app-shell__meta">{rightSlot}</div>
        </div>
      </header>
      <main className={`app-shell__body app-shell__body--${variant}`}>{children}</main>
    </div>
  );
};

export default AppShell;
