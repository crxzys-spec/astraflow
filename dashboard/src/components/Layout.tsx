import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/runs", label: "Runs" },
  { to: "/workflows", label: "Workflows", disabled: true },
  { to: "/workers", label: "Workers", disabled: true }
];

export const Layout = ({ children }: PropsWithChildren) => {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar__brand">AstraFlow</div>
        <nav className="sidebar__nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-item${isActive ? " nav-item--active" : ""}${item.disabled ? " nav-item--disabled" : ""}`
              }
              aria-disabled={item.disabled}
              tabIndex={item.disabled ? -1 : 0}
            >
              {item.label}
              {item.disabled && <span className="nav-item__badge">Soon</span>}
            </NavLink>
          ))}
        </nav>
      </aside>
      <section className="workspace">{children}</section>
    </div>
  );
};

export default Layout;

