import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  useAddUserRole,
  useCreateUser,
  useListUsers,
  useRemoveUserRole,
  useResetUserPassword,
  useUpdateUserStatus,
} from "../api/endpoints";
import type { CreateUserRequest } from "../api/models/createUserRequest";
import type { UserSummary } from "../api/models/userSummary";
import { useAuthStore } from "../features/auth/store";

type CreateUserForm = Omit<CreateUserRequest, "roles"> & { roles: string[] };

const INITIAL_CREATE_FORM: CreateUserForm = {
  username: "",
  displayName: "",
  password: "",
  roles: [],
};

const ROLE_OPTIONS: { id: string; label: string; helper: string }[] = [
  { id: "admin", label: "Admin", helper: "Full access to scheduler and user management." },
  { id: "workflow.editor", label: "Workflow editor", helper: "Create and update workflows, start runs." },
  { id: "workflow.viewer", label: "Workflow viewer", helper: "Read-only access to workflow definitions." },
  { id: "run.viewer", label: "Run viewer", helper: "Inspect run telemetry without editing workflows." },
];

const getErrorMessage = (error: any, fallback: string) => {
  const detail = error?.response?.data?.detail;
  const detailMessage =
    typeof detail === "string"
      ? detail
      : detail && typeof detail === "object" && "message" in detail
        ? (detail as { message?: string }).message
        : undefined;
  return error?.response?.data?.message || detailMessage || error?.message || fallback;
};

const UsersPage = () => {
  const isAdmin = useAuthStore((state) => state.hasRole(["admin"]));

  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<CreateUserForm>(INITIAL_CREATE_FORM);
  const [newPassword, setNewPassword] = useState("");
  const [feedback, setFeedback] = useState<{ type: "info" | "error"; message: string } | null>(null);
  const [isCreateModalOpen, setCreateModalOpen] = useState(false);
  const [isManageModalOpen, setManageModalOpen] = useState(false);

  const usersQuery = useListUsers({ query: { enabled: isAdmin, refetchOnWindowFocus: false } });

  const users: UserSummary[] = useMemo(() => {
    const items = usersQuery.data?.data.items ?? [];
    return [...items].sort((a, b) => a.username.localeCompare(b.username));
  }, [usersQuery.data]);

  const selectedUser = users.find((user) => user.userId === selectedUserId) ?? null;

  useEffect(() => {
    if (!users.length) {
      setSelectedUserId(null);
      return;
    }
    if (!selectedUserId || !users.some((user) => user.userId === selectedUserId)) {
      setSelectedUserId(users[0].userId);
    }
  }, [users, selectedUserId]);

  const createUserMutation = useCreateUser({
    mutation: {
      onSuccess: (response) => {
        setFeedback({ type: "info", message: `User '${response.data.username}' created successfully.` });
        setCreateForm(INITIAL_CREATE_FORM);
        setCreateModalOpen(false);
        usersQuery.refetch();
      },
      onError: (error: any) => {
        setFeedback({ type: "error", message: getErrorMessage(error, "Unable to create user.") });
      },
    },
  });

  const resetPasswordMutation = useResetUserPassword({
    mutation: {
      onSuccess: () => {
        const username = selectedUser?.username ?? "user";
        setFeedback({ type: "info", message: `Password updated for '${username}'.` });
        setNewPassword("");
      },
      onError: (error: any) => {
        setFeedback({ type: "error", message: getErrorMessage(error, "Unable to reset password.") });
      },
    },
  });

  const addRoleMutation = useAddUserRole({
    mutation: {
      onSuccess: () => {
        setFeedback({ type: "info", message: "Role assigned successfully." });
        usersQuery.refetch();
      },
      onError: (error: any) => {
        setFeedback({ type: "error", message: getErrorMessage(error, "Unable to assign role.") });
      },
    },
  });

  const removeRoleMutation = useRemoveUserRole({
    mutation: {
      onSuccess: () => {
        setFeedback({ type: "info", message: "Role removed successfully." });
        usersQuery.refetch();
      },
      onError: (error: any) => {
        setFeedback({ type: "error", message: getErrorMessage(error, "Unable to remove role.") });
      },
    },
  });

  if (!isAdmin) {
    return (
      <div className="admin-view">
        <div className="card stack">
          <h2>User Management</h2>
          <p className="text-subtle">
            Only administrators can provision accounts. Contact your AstraFlow administrator to request access.
          </p>
        </div>
      </div>
    );
  }

  const updateStatusMutation = useUpdateUserStatus({
    mutation: {
      onSuccess: () => {
        setFeedback({ type: "info", message: "Account status updated." });
        usersQuery.refetch();
      },
      onError: (error: any) => {
        setFeedback({ type: "error", message: getErrorMessage(error, "Unable to update status.") });
      },
    },
  });

  const handleCreateSubmit = (evt: FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    setFeedback(null);
    const payload: CreateUserRequest = {
      username: createForm.username.trim(),
      displayName: createForm.displayName.trim(),
      password: createForm.password,
      ...(createForm.roles.length ? { roles: createForm.roles } : {}),
    };
    createUserMutation.mutate({ data: payload });
  };

  const handlePasswordReset = (evt: FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    if (!selectedUser) {
      return;
    }
    const password = newPassword.trim();
    if (!password) {
      setFeedback({ type: "error", message: "New password is required." });
      return;
    }
    setFeedback(null);
    resetPasswordMutation.mutate({ userId: selectedUser.userId, data: { password } });
  };

  const toggleCreateRole = (roleName: string) => {
    setCreateForm((prev) => ({
      ...prev,
      roles: prev.roles.includes(roleName) ? prev.roles.filter((role) => role !== roleName) : [...prev.roles, roleName],
    }));
  };

  const handleRoleToggle = (roleName: string, checked: boolean) => {
    if (!selectedUser) {
      return;
    }
    setFeedback(null);
    if (checked) {
      addRoleMutation.mutate({ userId: selectedUser.userId, data: { role: roleName } });
    } else {
      removeRoleMutation.mutate({ userId: selectedUser.userId, role: roleName });
    }
  };

  const handleStatusToggle = (nextActive: boolean) => {
    if (!selectedUser) {
      return;
    }
    setFeedback(null);
    updateStatusMutation.mutate({ userId: selectedUser.userId, data: { isActive: nextActive } });
  };

  const disableCreate =
    !createForm.username.trim() || !createForm.displayName.trim() || !createForm.password || createUserMutation.isPending;
  const disableReset = !selectedUser || !newPassword.trim() || resetPasswordMutation.isPending;

  const closeCreateModal = () => {
    setCreateModalOpen(false);
    setCreateForm(INITIAL_CREATE_FORM);
  };

  const closeManageModal = () => {
    setManageModalOpen(false);
    setNewPassword("");
  };

  return (
    <div className="admin-view">
      <div className="card stack admin-user-card">
        <header className="card__header">
          <div>
            <h2>User Management</h2>
            <p className="text-subtle">Manage accounts, roles, and passwords across the platform.</p>
          </div>
          <div className="users-layout__actions">
            <button className="btn btn--ghost" type="button" onClick={() => setCreateModalOpen(true)}>
              Create User
            </button>
            <button className="btn" type="button" onClick={() => usersQuery.refetch()} disabled={usersQuery.isFetching}>
              {usersQuery.isFetching ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </header>

        {feedback && (
          <div className={`users-feedback users-feedback--${feedback.type === "error" ? "error" : "info"}`}>
            {feedback.message}
          </div>
        )}

        <div className="users-table-wrapper">
          <table className="data-table users-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Display name</th>
                <th>Roles</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {usersQuery.isLoading ? (
                <tr>
                  <td colSpan={4}>Loading users...</td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={4}>No users found. Use “Create User” to add one.</td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.userId}>
                    <td>{user.username}</td>
                    <td>{user.displayName}</td>
                    <td>{user.roles.join(", ") || "—"}</td>
                    <td>
                      <span className={`badge ${user.isActive ? "badge--success" : "badge--muted"}`}>
                        {user.isActive ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="users-table__actions">
                      <button
                        className="btn btn--ghost"
                        type="button"
                        onClick={() => {
                          setSelectedUserId(user.userId);
                          setManageModalOpen(true);
                          setNewPassword("");
                        }}
                      >
                        Manage
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isCreateModalOpen && (
        <div className="modal">
          <div className="modal__backdrop" onClick={closeCreateModal} />
          <div className="modal__panel card stack">
            <header className="modal__header">
              <h3>Create User</h3>
              <button className="btn btn--ghost" type="button" onClick={closeCreateModal}>
                Close
              </button>
            </header>
            <form className="stack" onSubmit={handleCreateSubmit}>
              <label className="stack">
                <span>Username</span>
                <input
                  type="text"
                  value={createForm.username}
                  onChange={(evt) => setCreateForm((prev) => ({ ...prev, username: evt.target.value }))}
                  placeholder="jane.doe"
                  required
                />
              </label>
              <label className="stack">
                <span>Display name</span>
                <input
                  type="text"
                  value={createForm.displayName}
                  onChange={(evt) => setCreateForm((prev) => ({ ...prev, displayName: evt.target.value }))}
                  placeholder="Jane Doe"
                  required
                />
              </label>
              <label className="stack">
                <span>Temporary password</span>
                <input
                  type="password"
                  value={createForm.password}
                  onChange={(evt) => setCreateForm((prev) => ({ ...prev, password: evt.target.value }))}
                  placeholder="••••••••"
                  required
                />
              </label>
              <fieldset className="stack users-role-fieldset">
                <legend>Initial roles (optional)</legend>
                <div className="users-role-grid">
                  {ROLE_OPTIONS.map((role) => (
                    <label key={role.id} className="users-role-option">
                      <input
                        type="checkbox"
                        checked={createForm.roles.includes(role.id)}
                        onChange={() => toggleCreateRole(role.id)}
                      />
                      <div>
                        <span className="users-role-option__label">{role.label}</span>
                        <span className="text-subtle">{role.helper}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </fieldset>
              <button className="btn btn--primary" type="submit" disabled={disableCreate}>
                {createUserMutation.isPending ? "Creating..." : "Create User"}
              </button>
            </form>
          </div>
        </div>
      )}

      {isManageModalOpen && selectedUser && (
        <div className="modal">
          <div className="modal__backdrop" onClick={closeManageModal} />
          <div className="modal__panel card stack">
            <header className="modal__header">
              <div>
                <h3>Manage {selectedUser.displayName}</h3>
                <p className="text-subtle">
                  Username: {selectedUser.username} • Roles: {selectedUser.roles.join(", ") || "None"}
                </p>
                <p className="text-subtle">
                  Status:{" "}
                  <span className={`badge ${selectedUser.isActive ? "badge--success" : "badge--muted"}`}>
                    {selectedUser.isActive ? "Active" : "Disabled"}
                  </span>
                </p>
              </div>
              <button className="btn btn--ghost" type="button" onClick={closeManageModal}>
                Close
              </button>
            </header>
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => handleStatusToggle(!selectedUser.isActive)}
              disabled={updateStatusMutation.isPending}
            >
              {selectedUser.isActive ? "Disable Account" : "Enable Account"}
            </button>

            <div className="users-role-grid">
              {ROLE_OPTIONS.map((role) => {
                const assigned = selectedUser.roles.includes(role.id);
                const pending = addRoleMutation.isPending || removeRoleMutation.isPending;
                return (
                  <label key={role.id} className="users-role-option">
                    <input
                      type="checkbox"
                      checked={assigned}
                      disabled={pending}
                      onChange={(evt) => handleRoleToggle(role.id, evt.target.checked)}
                    />
                    <div>
                      <span className="users-role-option__label">{role.label}</span>
                      <span className="text-subtle">{role.helper}</span>
                    </div>
                  </label>
                );
              })}
            </div>

            <form className="stack users-password-form" onSubmit={handlePasswordReset}>
              <label className="stack">
                <span>Reset password</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(evt) => setNewPassword(evt.target.value)}
                  placeholder="New password"
                />
              </label>
              <button className="btn" type="submit" disabled={disableReset}>
                {resetPasswordMutation.isPending ? "Updating..." : "Update Password"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersPage;
