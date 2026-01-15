import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { CreateUserRequest } from "../../../client/models";
import type { UserSummary } from "../../../client/models";
import { useAuthStore } from "@store/authSlice";
import {
  addUserRole,
  createUser,
  listUsers,
  removeUserRole,
  resetUserPassword,
  updateUserStatus,
} from "../../../services/users";
import { useAsyncAction } from "../../../hooks/useAsyncAction";
import { toApiError, type ApiError } from "../../../api/fetcher";
import { resolveApiErrorMessage } from "../../../lib/apiErrors";

type CreateUserForm = Omit<CreateUserRequest, "roles"> & { roles: string[] };

const INITIAL_CREATE_FORM: CreateUserForm = {
  username: "",
  displayName: "",
  password: "",
  roles: [],
};

const getErrorMessage = (error: unknown, fallback: string) =>
  resolveApiErrorMessage(error, fallback);

const UsersPage = () => {
  const isAdmin = useAuthStore((state) => state.hasRole(["admin"]));
  const { t } = useTranslation();
  const roleOptions: { id: string; label: string; helper: string }[] = [
    { id: "admin", label: t("admin.roles.admin.label"), helper: t("admin.roles.admin.helper") },
    { id: "workflow.editor", label: t("admin.roles.editor.label"), helper: t("admin.roles.editor.helper") },
    { id: "workflow.viewer", label: t("admin.roles.viewer.label"), helper: t("admin.roles.viewer.helper") },
    { id: "run.viewer", label: t("admin.roles.runViewer.label"), helper: t("admin.roles.runViewer.helper") },
  ];

  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<CreateUserForm>(INITIAL_CREATE_FORM);
  const [newPassword, setNewPassword] = useState("");
  const [feedback, setFeedback] = useState<{ type: "info" | "error"; message: string } | null>(null);
  const [isCreateModalOpen, setCreateModalOpen] = useState(false);
  const [isManageModalOpen, setManageModalOpen] = useState(false);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [usersStatus, setUsersStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [usersError, setUsersError] = useState<ApiError | null>(null);

  const fetchUsers = async () => {
    if (!isAdmin) {
      return;
    }
    setUsersStatus("loading");
    setUsersError(null);
    try {
      const response = await listUsers();
      const items = response.items ?? [];
      setUsers([...items].sort((a, b) => a.username.localeCompare(b.username)));
      setUsersStatus("success");
    } catch (err) {
      setUsersError(toApiError(err));
      setUsersStatus("error");
    }
  };

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

  useEffect(() => {
    if (isAdmin) {
      void fetchUsers();
    } else {
      setUsers([]);
      setSelectedUserId(null);
    }
  }, [isAdmin]);

  const createUserMutation = useAsyncAction(async (payload: CreateUserRequest) => createUser(payload));
  const resetPasswordMutation = useAsyncAction(async ({ userId, password }: { userId: string; password: string }) =>
    resetUserPassword(userId, password),
  );
  const addRoleMutation = useAsyncAction(async ({ userId, role }: { userId: string; role: string }) =>
    addUserRole(userId, { role }),
  );
  const removeRoleMutation = useAsyncAction(async ({ userId, role }: { userId: string; role: string }) =>
    removeUserRole(userId, role),
  );

  if (!isAdmin) {
    return (
      <div className="admin-view">
        <div className="card stack admin-panel">
          <h2>{t("admin.usersPage.accessDeniedTitle")}</h2>
          <p className="text-subtle">{t("admin.usersPage.accessDeniedMessage")}</p>
        </div>
      </div>
    );
  }

  const updateStatusMutation = useAsyncAction(async ({ userId, isActive }: { userId: string; isActive: boolean }) =>
    updateUserStatus(userId, isActive),
  );

  const handleCreateSubmit = (evt: FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    setFeedback(null);
    const payload: CreateUserRequest = {
      username: createForm.username.trim(),
      displayName: createForm.displayName.trim(),
      password: createForm.password,
      ...(createForm.roles.length ? { roles: createForm.roles } : {}),
    };
    createUserMutation.mutate(payload, {
      onSuccess: (response) => {
        setFeedback({ type: "info", message: t("admin.usersPage.messages.createSuccess", { username: response.username }) });
        setCreateForm(INITIAL_CREATE_FORM);
        setCreateModalOpen(false);
        void fetchUsers();
      },
      onError: (error: any) => {
        setFeedback({ type: "error", message: getErrorMessage(error, t("admin.usersPage.messages.createError")) });
      },
    });
  };

  const handlePasswordReset = (evt: FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    if (!selectedUser) {
      return;
    }
    const password = newPassword.trim();
    if (!password) {
      setFeedback({ type: "error", message: t("admin.usersPage.messages.passwordRequired") });
      return;
    }
    setFeedback(null);
    resetPasswordMutation.mutate(
      { userId: selectedUser.userId, password },
      {
        onSuccess: () => {
          const username = selectedUser?.username ?? t("admin.usersPage.messages.fallbackUser");
          setFeedback({ type: "info", message: t("admin.usersPage.messages.passwordUpdated", { username }) });
          setNewPassword("");
        },
        onError: (error: any) => {
          setFeedback({ type: "error", message: getErrorMessage(error, t("admin.usersPage.messages.passwordResetError")) });
        },
      },
    );
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
      addRoleMutation.mutate(
        { userId: selectedUser.userId, role: roleName },
        {
          onSuccess: () => {
            setFeedback({ type: "info", message: t("admin.usersPage.messages.roleAssigned") });
            void fetchUsers();
          },
          onError: (error: any) => {
            setFeedback({ type: "error", message: getErrorMessage(error, t("admin.usersPage.messages.roleAssignError")) });
          },
        },
      );
    } else {
      removeRoleMutation.mutate(
        { userId: selectedUser.userId, role: roleName },
        {
          onSuccess: () => {
            setFeedback({ type: "info", message: t("admin.usersPage.messages.roleRemoved") });
            void fetchUsers();
          },
          onError: (error: any) => {
            setFeedback({ type: "error", message: getErrorMessage(error, t("admin.usersPage.messages.roleRemoveError")) });
          },
        },
      );
    }
  };

  const handleStatusToggle = (nextActive: boolean) => {
    if (!selectedUser) {
      return;
    }
    setFeedback(null);
    updateStatusMutation.mutate(
      { userId: selectedUser.userId, isActive: nextActive },
      {
        onSuccess: () => {
          setFeedback({ type: "info", message: t("admin.usersPage.messages.statusUpdated") });
          void fetchUsers();
        },
        onError: (error: any) => {
          setFeedback({ type: "error", message: getErrorMessage(error, t("admin.usersPage.messages.statusUpdateError")) });
        },
      },
    );
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
      <div className="card stack admin-user-card admin-panel">
        <header className="card__header admin-panel__header">
          <div>
            <span className="admin-panel__eyebrow">{t("admin.eyebrow")}</span>
            <h2>{t("admin.usersPage.title")}</h2>
            <p className="text-subtle admin-panel__description">{t("admin.usersPage.subtitle")}</p>
          </div>
          <div className="users-layout__actions">
            <button className="btn btn--ghost" type="button" onClick={() => setCreateModalOpen(true)}>
              {t("admin.usersPage.actions.createUser")}
            </button>
            <button className="btn" type="button" onClick={() => void fetchUsers()} disabled={usersStatus === "loading"}>
              {usersStatus === "loading" ? t("admin.usersPage.actions.refreshing") : t("common.refresh")}
            </button>
          </div>
        </header>

        {feedback && (
          <div className={`users-feedback users-feedback--${feedback.type === "error" ? "error" : "info"}`}>
            {feedback.message}
          </div>
        )}
        {usersStatus === "error" && (
          <div className="users-feedback users-feedback--error">
            {usersError?.message ?? t("admin.usersPage.messages.loadError")}
          </div>
        )}

        <div className="admin-section admin-section--table">
          <div className="users-table-wrapper admin-table-wrap">
            <table className="data-table users-table admin-table">
              <thead>
                <tr>
                  <th>{t("admin.usersPage.table.username")}</th>
                  <th>{t("admin.usersPage.table.displayName")}</th>
                  <th>{t("admin.usersPage.table.roles")}</th>
                  <th>{t("admin.usersPage.table.status")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {usersStatus === "loading" ? (
                  <tr>
                    <td colSpan={4}>{t("admin.usersPage.table.loading")}</td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={4}>{t("admin.usersPage.table.empty")}</td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.userId}>
                      <td>{user.username}</td>
                      <td>{user.displayName}</td>
                      <td>{user.roles.join(", ") || t("admin.usersPage.roles.none")}</td>
                      <td>
                        <span className={`badge ${user.isActive ? "badge--success" : "badge--muted"}`}>
                          {user.isActive ? t("admin.usersPage.status.active") : t("admin.usersPage.status.disabled")}
                        </span>
                      </td>
                      <td className="users-table__actions admin-table__actions">
                        <button
                          className="btn btn--ghost"
                          type="button"
                          onClick={() => {
                            setSelectedUserId(user.userId);
                            setManageModalOpen(true);
                            setNewPassword("");
                          }}
                        >
                          {t("admin.usersPage.actions.manage")}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {isCreateModalOpen && (
        <div className="modal">
          <div className="modal__backdrop" onClick={closeCreateModal} />
          <div className="modal__panel card stack">
            <header className="modal__header">
              <h3>{t("admin.usersPage.createModal.title")}</h3>
              <button className="btn btn--ghost" type="button" onClick={closeCreateModal}>
                {t("common.dismiss")}
              </button>
            </header>
            <form className="stack" onSubmit={handleCreateSubmit}>
              <label className="stack">
                <span>{t("admin.usersPage.createModal.username")}</span>
                <input
              type="text"
              value={createForm.username}
              onChange={(evt) => setCreateForm((prev) => ({ ...prev, username: evt.target.value }))}
              placeholder={t("admin.usersPage.createModal.usernamePlaceholder")}
              required
            />
          </label>
          <label className="stack">
            <span>{t("admin.usersPage.createModal.displayName")}</span>
            <input
              type="text"
              value={createForm.displayName}
              onChange={(evt) => setCreateForm((prev) => ({ ...prev, displayName: evt.target.value }))}
              placeholder={t("admin.usersPage.createModal.displayNamePlaceholder")}
              required
            />
          </label>
              <label className="stack">
                <span>{t("admin.usersPage.createModal.password")}</span>
                <input
                  type="password"
                  value={createForm.password}
                  onChange={(evt) => setCreateForm((prev) => ({ ...prev, password: evt.target.value }))}
                  placeholder={t("admin.usersPage.createModal.passwordPlaceholder")}
                  required
                />
              </label>
              <fieldset className="stack users-role-fieldset">
                <legend>{t("admin.usersPage.createModal.rolesLabel")}</legend>
                <div className="users-role-grid">
                  {roleOptions.map((role) => (
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
                {createUserMutation.isPending ? t("admin.usersPage.createModal.creating") : t("admin.usersPage.actions.createUser")}
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
                <h3>{t("admin.usersPage.manageModal.title", { name: selectedUser.displayName })}</h3>
                <p className="text-subtle">
                  {t("admin.usersPage.manageModal.summary", {
                    username: selectedUser.username,
                    roles: selectedUser.roles.join(", ") || t("admin.usersPage.roles.none"),
                  })}
                </p>
                <p className="text-subtle">
                  {t("admin.usersPage.manageModal.statusLabel")}{" "}
                  <span className={`badge ${selectedUser.isActive ? "badge--success" : "badge--muted"}`}>
                    {selectedUser.isActive ? t("admin.usersPage.status.active") : t("admin.usersPage.status.disabled")}
                  </span>
                </p>
              </div>
              <button className="btn btn--ghost" type="button" onClick={closeManageModal}>
                {t("common.dismiss")}
              </button>
            </header>
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => handleStatusToggle(!selectedUser.isActive)}
              disabled={updateStatusMutation.isPending}
            >
              {selectedUser.isActive
                ? t("admin.usersPage.manageModal.disableAccount")
                : t("admin.usersPage.manageModal.enableAccount")}
            </button>

            <div className="users-role-grid">
              {roleOptions.map((role) => {
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
                <span>{t("admin.usersPage.manageModal.resetPassword")}</span>
              <input
                  type="password"
                  value={newPassword}
                  onChange={(evt) => setNewPassword(evt.target.value)}
                  placeholder={t("admin.usersPage.manageModal.newPasswordPlaceholder")}
                />
              </label>
              <button className="btn" type="submit" disabled={disableReset}>
                {resetPasswordMutation.isPending
                  ? t("admin.usersPage.manageModal.updating")
                  : t("admin.usersPage.manageModal.updatePassword")}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersPage;
