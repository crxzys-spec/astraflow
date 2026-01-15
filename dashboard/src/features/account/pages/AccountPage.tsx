import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { accountGateway } from "../../../services/account";
import { resourcesGateway } from "../../../services/resources";
import { listPackages, getPackage } from "../../../services/packages";
import { packageAccessGateway } from "../../../services/packageAccess";
import { useAuthStore } from "@store/authSlice";
import type {
  ManifestPermissionRequirement,
  ManifestVaultRequirement,
  PackageDetail,
  PackagePermission,
  PackageSummary,
  PackageVaultItem,
  Resource,
  UserSummary,
} from "../../../client/models";
import { resolveLocalizedText } from "../../../lib/manifestText";
import "../account.css";

const formatResourceSize = (size?: number | null): string => {
  if (size == null) {
    return "-";
  }
  return `${size.toLocaleString()} bytes`;
};

const formatBytes = (value?: number) => {
  if (!value && value !== 0) {
    return "";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
};

const formatDate = (value?: string | Date | null): string => {
  if (!value) {
    return "-";
  }
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString();
};

const LOCAL_PACKAGE_OWNER = "local";

const resolvePackageOwner = (pkg: PackageSummary) => {
  const owner = (pkg.ownerId ?? "").trim();
  if (!owner || owner === LOCAL_PACKAGE_OWNER) {
    return null;
  }
  return owner;
};

const resolvePackageRef = (pkg: PackageSummary) => {
  const owner = resolvePackageOwner(pkg);
  if (!owner) {
    return pkg.name;
  }
  return `${owner}/${pkg.name}`;
};

type UploadEntry = {
  key: string;
  name: string;
  size: number;
  progress: number;
  status: "queued" | "uploading" | "error";
  error?: string;
};

type StatusState = {
  type: "idle" | "error" | "success";
  message?: string;
};

type KeyValueEntry = {
  id: string;
  key: string;
  value: string;
};

type PreviewKind = "image" | "video" | "audio";

type PreviewEntry = {
  status: "loading" | "ready" | "error";
  kind: PreviewKind;
  url?: string;
  error?: string;
};

type AccountSection = "profile" | "resources" | "packages";

type UploadOptions = Parameters<typeof resourcesGateway.upload>[1];

const isAbortError = (value: unknown) => {
  const code = (value as { code?: string })?.code;
  const name = (value as { name?: string })?.name;
  const message = (value as { message?: string })?.message;
  return code === "ERR_CANCELED" || name === "CanceledError" || name === "AbortError" || message === "canceled";
};

const inferPreviewKind = (resource: Resource): PreviewKind | null => {
  const mime = resource.mimeType?.toLowerCase();
  if (mime) {
    if (mime.startsWith("image/")) {
      return "image";
    }
    if (mime.startsWith("video/")) {
      return "video";
    }
    if (mime.startsWith("audio/")) {
      return "audio";
    }
  }
  const name = resource.filename?.toLowerCase() ?? "";
  if (/\.(png|jpg|jpeg|gif|webp|svg)$/.test(name)) {
    return "image";
  }
  if (/\.(mp4|webm|ogg)$/.test(name)) {
    return "video";
  }
  if (/\.(mp3|wav|ogg|flac|m4a)$/.test(name)) {
    return "audio";
  }
  return null;
};

const createKvEntryId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const createKvEntry = (): KeyValueEntry => ({
  id: createKvEntryId(),
  key: "",
  value: "",
});

const AccountPage = () => {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const updateUser = useAuthStore((state) => state.updateUser);
  const [profile, setProfile] = useState<UserSummary | null>(user ?? null);
  const [displayName, setDisplayName] = useState(user?.displayName ?? "");
  const [profileStatus, setProfileStatus] = useState<StatusState>({ type: "idle" });
  const [saving, setSaving] = useState(false);

  const [resources, setResources] = useState<Resource[]>([]);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [resourceSearch, setResourceSearch] = useState("");
  const [providerFilter, setProviderFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [uploadEntries, setUploadEntries] = useState<UploadEntry[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProvider, setUploadProvider] = useState("default");
  const [kvResourceName, setKvResourceName] = useState("");
  const [kvEntries, setKvEntries] = useState<KeyValueEntry[]>(() => [createKvEntry()]);
  const [previews, setPreviews] = useState<Record<string, PreviewEntry>>({});
  const previewControllersRef = useRef(new Map<string, AbortController>());
  const previewsRef = useRef(previews);
  const [activeSection, setActiveSection] = useState<AccountSection>("profile");
  const [packages, setPackages] = useState<PackageSummary[]>([]);
  const [packagesLoading, setPackagesLoading] = useState(false);
  const [packagesError, setPackagesError] = useState<string | null>(null);
  const [selectedPackage, setSelectedPackage] = useState<string>("");
  const [packageDetail, setPackageDetail] = useState<PackageDetail | null>(null);
  const [packageDetailLoading, setPackageDetailLoading] = useState(false);
  const [packageDetailError, setPackageDetailError] = useState<string | null>(null);
  const [vaultItems, setVaultItems] = useState<PackageVaultItem[]>([]);
  const [vaultDrafts, setVaultDrafts] = useState<Record<string, string>>({});
  const [vaultLoading, setVaultLoading] = useState(false);
  const [vaultStatus, setVaultStatus] = useState<StatusState>({ type: "idle" });
  const [permissionItems, setPermissionItems] = useState<PackagePermission[]>([]);
  const [permissionLoading, setPermissionLoading] = useState(false);
  const [permissionStatus, setPermissionStatus] = useState<StatusState>({ type: "idle" });

  useEffect(() => {
    if (user) {
      setProfile(user);
      setDisplayName(user.displayName);
    }
  }, [user]);

  const loadProfile = useCallback(async () => {
    setProfileStatus({ type: "idle" });
    try {
      const data = await accountGateway.getProfile();
      setProfile(data);
      setDisplayName(data.displayName);
      updateUser(data);
    } catch (error) {
      console.error("Failed to load profile", error);
      setProfileStatus({ type: "error", message: t("account.profile.messages.loadError") });
    }
  }, [t, updateUser]);

  const loadResources = useCallback(
    async (searchValue?: string) => {
      setResourceLoading(true);
      setResourceError(null);
      try {
        const items = await resourcesGateway.listResources({
          ownerId: "me",
          search: searchValue && searchValue.trim() ? searchValue.trim() : undefined,
        });
        setResources(items);
      } catch (error) {
        console.error("Failed to load resources", error);
        setResourceError(t("account.resources.messages.loadError"));
      } finally {
        setResourceLoading(false);
      }
    },
    [t]
  );

  const loadPackages = useCallback(async () => {
    setPackagesLoading(true);
    setPackagesError(null);
    try {
      const items = await listPackages();
      const sorted = [...items].sort((a, b) => resolvePackageRef(a).localeCompare(resolvePackageRef(b)));
      setPackages(sorted);
      setSelectedPackage((prev) => {
        if (prev && sorted.some((item) => resolvePackageRef(item) === prev)) {
          return prev;
        }
        return sorted[0] ? resolvePackageRef(sorted[0]) : "";
      });
    } catch (error) {
      console.error("Failed to load packages", error);
      setPackages([]);
      setPackagesError(t("account.packages.messages.loadError"));
    } finally {
      setPackagesLoading(false);
    }
  }, [t]);

  const loadPackageDetail = useCallback(async (packageName: string) => {
    setPackageDetailLoading(true);
    setPackageDetailError(null);
    try {
      const detail = await getPackage(packageName);
      setPackageDetail(detail);
    } catch (error) {
      console.error("Failed to load package detail", error);
      setPackageDetail(null);
      setPackageDetailError(t("account.packages.messages.requirementsError"));
    } finally {
      setPackageDetailLoading(false);
    }
  }, [t]);

  const loadPackageVault = useCallback(async (packageName: string) => {
    setVaultLoading(true);
    setVaultStatus({ type: "idle" });
    try {
      const items = await packageAccessGateway.listVault(packageName);
      setVaultItems(items);
    } catch (error) {
      console.error("Failed to load package vault", error);
      setVaultItems([]);
      setVaultStatus({ type: "error", message: t("account.packages.vault.messages.loadError") });
    } finally {
      setVaultLoading(false);
    }
  }, [t]);

  const loadPackagePermissions = useCallback(async (packageName: string) => {
    setPermissionLoading(true);
    setPermissionStatus({ type: "idle" });
    try {
      const items = await packageAccessGateway.listPermissions(packageName);
      setPermissionItems(items);
    } catch (error) {
      console.error("Failed to load package permissions", error);
      setPermissionItems([]);
      setPermissionStatus({ type: "error", message: t("account.packages.permissions.messages.loadError") });
    } finally {
      setPermissionLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadProfile();
    loadResources();
  }, [loadProfile, loadResources]);

  useEffect(() => {
    if (activeSection !== "packages") {
      return;
    }
    loadPackages();
  }, [activeSection, loadPackages]);

  useEffect(() => {
    if (!selectedPackage) {
      setPackageDetail(null);
      setPackageDetailError(null);
      setPackageDetailLoading(false);
      setVaultItems([]);
      setPermissionItems([]);
      return;
    }
    loadPackageDetail(selectedPackage);
    loadPackageVault(selectedPackage);
    loadPackagePermissions(selectedPackage);
  }, [selectedPackage, loadPackageDetail, loadPackageVault, loadPackagePermissions]);

  useEffect(() => {
    setVaultStatus({ type: "idle" });
    setPermissionStatus({ type: "idle" });
  }, [selectedPackage]);

  useEffect(() => {
    previewsRef.current = previews;
  }, [previews]);

  useEffect(() => {
    const resourceIds = new Set(resources.map((item) => item.resourceId));
    setPreviews((prev) => {
      let changed = false;
      const next = { ...prev };
      Object.keys(next).forEach((resourceId) => {
        if (!resourceIds.has(resourceId)) {
          changed = true;
          if (next[resourceId]?.url) {
            URL.revokeObjectURL(next[resourceId].url ?? "");
          }
          const controller = previewControllersRef.current.get(resourceId);
          if (controller) {
            controller.abort();
            previewControllersRef.current.delete(resourceId);
          }
          delete next[resourceId];
        }
      });
      return changed ? next : prev;
    });
  }, [resources]);

  useEffect(() => {
    return () => {
      Object.values(previewsRef.current).forEach((entry) => {
        if (entry.url) {
          URL.revokeObjectURL(entry.url);
        }
      });
      previewControllersRef.current.forEach((controller) => controller.abort());
      previewControllersRef.current.clear();
    };
  }, []);

  const handleSaveProfile = async () => {
    if (!profile) {
      return;
    }
    const nextName = displayName.trim();
    if (!nextName) {
      setProfileStatus({ type: "error", message: t("account.profile.messages.displayNameRequired") });
      return;
    }
    setSaving(true);
    setProfileStatus({ type: "idle" });
    try {
      const updated = await accountGateway.updateProfile({ displayName: nextName });
      setProfile(updated);
      setDisplayName(updated.displayName);
      updateUser(updated);
      setProfileStatus({ type: "success", message: t("account.profile.messages.updated") });
    } catch (error) {
      console.error("Failed to update profile", error);
      setProfileStatus({ type: "error", message: t("account.profile.messages.updateError") });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteResource = async (resourceId: string) => {
    if (!window.confirm(t("account.resources.messages.deleteConfirm"))) {
      return;
    }
    try {
      await resourcesGateway.delete(resourceId);
      setResources((prev) => prev.filter((item) => item.resourceId !== resourceId));
    } catch (error) {
      console.error("Failed to delete resource", error);
      setResourceError(t("account.resources.messages.deleteError"));
    }
  };

  const updateUploadEntry = (key: string, patch: Partial<UploadEntry>) => {
    setUploadEntries((prev) => prev.map((entry) => (entry.key === key ? { ...entry, ...patch } : entry)));
  };

  const removeUploadEntry = (key: string) => {
    setUploadEntries((prev) => prev.filter((entry) => entry.key !== key));
  };

  const addUploadEntries = (entries: UploadEntry[]) => {
    if (!entries.length) {
      return;
    }
    setUploadEntries((prev) => [...prev, ...entries]);
  };

  const handleUploadFiles = useCallback(
    async (files: File[], options?: UploadOptions) => {
      if (!files.length || uploading) {
        return false;
      }
      setUploadError(null);
      const batchId = Date.now();
      const queue = files.map((file, index) => ({
        file,
        key: `${file.name}-${file.size}-${file.lastModified}-${batchId}-${index}`,
      }));
      addUploadEntries(
        queue.map(({ file, key }) => ({
          key,
          name: file.name,
          size: file.size,
          progress: 0,
          status: "queued",
        })),
      );
      setUploading(true);
      const resolvedOptions = (options ?? {}) as NonNullable<UploadOptions>;
      const provider =
        resolvedOptions.provider ?? (uploadProvider === "default" ? undefined : uploadProvider);
      let uploadedAny = false;
      for (const { file, key } of queue) {
        updateUploadEntry(key, { status: "uploading" });
        try {
          const resource = await resourcesGateway.upload(file, {
            ...resolvedOptions,
            provider,
            onProgress: (progress) => {
              resolvedOptions.onProgress?.(progress);
              updateUploadEntry(key, { progress });
            },
          });
          removeUploadEntry(key);
          if (resource) {
            uploadedAny = true;
          }
        } catch (error) {
          const message = (error as { message?: string })?.message ?? t("account.resources.messages.uploadFailed");
          updateUploadEntry(key, { status: "error", error: message });
          setUploadError(message);
        }
      }
      setUploading(false);
      if (uploadedAny) {
        await loadResources(resourceSearch);
      }
      return uploadedAny;
    },
    [loadResources, resourceSearch, t, uploadProvider, uploading],
  );

  const handleUploadInput = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : [];
    void handleUploadFiles(files);
    event.target.value = "";
  };

  const resolveKvFilename = (rawName: string) => {
    const trimmed = rawName.trim().replace(/\.+$/, "");
    const base = trimmed || "key-values";
    return /\.[A-Za-z0-9]+$/.test(base) ? base : `${base}.json`;
  };

  const updateKvEntry = (id: string, patch: Partial<KeyValueEntry>) => {
    setKvEntries((prev) => prev.map((entry) => (entry.id === id ? { ...entry, ...patch } : entry)));
  };

  const handleAddKvEntry = () => {
    setKvEntries((prev) => [...prev, createKvEntry()]);
  };

  const handleRemoveKvEntry = (id: string) => {
    setKvEntries((prev) => {
      const next = prev.filter((entry) => entry.id !== id);
      return next.length ? next : [createKvEntry()];
    });
  };

  const buildKvPayload = (entries: KeyValueEntry[]) => {
    const payload: Record<string, string> = {};
    const keys: string[] = [];
    const duplicates = new Set<string>();
    entries.forEach((entry) => {
      const key = entry.key.trim();
      if (!key) {
        return;
      }
      if (Object.prototype.hasOwnProperty.call(payload, key)) {
        duplicates.add(key);
        return;
      }
      payload[key] = entry.value ?? "";
      keys.push(key);
    });
    const json = keys.length ? JSON.stringify(payload, null, 2) : "";
    return { payload, json, keys, duplicates: Array.from(duplicates) };
  };

  const handleCreateKeyValueResource = async () => {
    const payload = buildKvPayload(kvEntries);
    if (payload.duplicates.length) {
      setUploadError(t("account.resources.messages.duplicateKeys", { keys: payload.duplicates.join(", ") }));
      return;
    }
    if (!payload.json || !payload.keys.length) {
      setUploadError(t("account.resources.messages.kvMissing"));
      return;
    }
    const filename = resolveKvFilename(kvResourceName);
    const file = new File([payload.json], filename, {
      type: "application/json",
    });
    const uploaded = await handleUploadFiles([file], { resourceType: "kv" });
    if (uploaded) {
      setKvEntries([createKvEntry()]);
      setKvResourceName("");
    }
  };

  const handleDismissUpload = (key: string) => {
    removeUploadEntry(key);
  };

  const setPreviewEntry = (resourceId: string, entry: PreviewEntry) => {
    setPreviews((prev) => ({ ...prev, [resourceId]: entry }));
  };

  const clearPreviewEntry = (resourceId: string) => {
    setPreviews((prev) => {
      const existing = prev[resourceId];
      if (existing?.url) {
        URL.revokeObjectURL(existing.url);
      }
      const next = { ...prev };
      delete next[resourceId];
      return next;
    });
    const controller = previewControllersRef.current.get(resourceId);
    if (controller) {
      controller.abort();
      previewControllersRef.current.delete(resourceId);
    }
  };

  const handleTogglePreview = async (resource: Resource) => {
    const kind = inferPreviewKind(resource);
    if (!kind) {
      return;
    }
    const resourceId = resource.resourceId;
    if (previews[resourceId]) {
      clearPreviewEntry(resourceId);
      return;
    }
    const controller = new AbortController();
    previewControllersRef.current.set(resourceId, controller);
    setPreviewEntry(resourceId, { status: "loading", kind });
    try {
      const { blob } = await resourcesGateway.fetchBlob(resourceId, {
        signal: controller.signal,
        timeoutMs: 120_000,
      });
      const url = URL.createObjectURL(blob);
      setPreviewEntry(resourceId, { status: "ready", kind, url });
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }
      const message = (error as { message?: string })?.message ?? t("account.resources.messages.previewFailed");
      setPreviewEntry(resourceId, { status: "error", kind, error: message });
    } finally {
      previewControllersRef.current.delete(resourceId);
    }
  };

  const handleSaveVault = async () => {
    if (!selectedPackage) {
      return;
    }
    const missingRequired = vaultRequirements.filter(
      (requirement) =>
        requirement.required !== false && !vaultDrafts[requirement.key]?.toString().trim(),
    );
    if (missingRequired.length) {
      setVaultStatus({
        type: "error",
        message: t("account.packages.vault.messages.missingRequired", {
          keys: missingRequired.map((item) => item.key).join(", "),
        }),
      });
      return;
    }
    setVaultLoading(true);
    setVaultStatus({ type: "idle" });
    const existingKeys = new Set(vaultItems.map((item) => item.key));
    const items = vaultRequirements
      .map((requirement) => ({
        key: requirement.key,
        value: vaultDrafts[requirement.key] ?? "",
      }))
      .filter((entry) => entry.value.toString().trim().length > 0);
    const deleteKeys = vaultRequirements
      .filter(
        (requirement) =>
          existingKeys.has(requirement.key) &&
          !vaultDrafts[requirement.key]?.toString().trim(),
      )
      .map((requirement) => requirement.key);
    try {
      if (items.length) {
        await packageAccessGateway.upsertVault({
          packageName: selectedPackage,
          items,
        });
      }
      if (deleteKeys.length) {
        await Promise.all(deleteKeys.map((key) => packageAccessGateway.deleteVaultItem(selectedPackage, key)));
      }
      await loadPackageVault(selectedPackage);
      setVaultStatus({ type: "success", message: t("account.packages.vault.messages.updated") });
    } catch (error) {
      console.error("Failed to update vault", error);
      setVaultStatus({ type: "error", message: t("account.packages.vault.messages.updateError") });
    } finally {
      setVaultLoading(false);
    }
  };

  const handleDeleteVaultItem = async (key: string) => {
    if (!selectedPackage) {
      return;
    }
    setVaultLoading(true);
    setVaultStatus({ type: "idle" });
    try {
      await packageAccessGateway.deleteVaultItem(selectedPackage, key);
      await loadPackageVault(selectedPackage);
      setVaultStatus({ type: "success", message: t("account.packages.vault.messages.deleted") });
    } catch (error) {
      console.error("Failed to delete vault entry", error);
      setVaultStatus({ type: "error", message: t("account.packages.vault.messages.deleteError") });
    } finally {
      setVaultLoading(false);
    }
  };

  const handleGrantPermission = async (requirement: ManifestPermissionRequirement) => {
    if (!selectedPackage) {
      return;
    }
    setPermissionLoading(true);
    setPermissionStatus({ type: "idle" });
    try {
      await packageAccessGateway.createPermission({
        packageName: selectedPackage,
        permissionKey: requirement.key,
        types: requirement.types,
        providers: requirement.providers ?? undefined,
        actions: requirement.actions ?? ["read"],
      });
      await loadPackagePermissions(selectedPackage);
      setPermissionStatus({ type: "success", message: t("account.packages.permissions.messages.granted") });
    } catch (error) {
      console.error("Failed to grant permission", error);
      setPermissionStatus({ type: "error", message: t("account.packages.permissions.messages.grantError") });
    } finally {
      setPermissionLoading(false);
    }
  };

  const handleRevokePermission = async (permission: PackagePermission) => {
    if (!selectedPackage) {
      return;
    }
    setPermissionLoading(true);
    setPermissionStatus({ type: "idle" });
    try {
      await packageAccessGateway.deletePermission(permission.permissionId);
      await loadPackagePermissions(selectedPackage);
      setPermissionStatus({ type: "success", message: t("account.packages.permissions.messages.revoked") });
    } catch (error) {
      console.error("Failed to revoke permission", error);
      setPermissionStatus({ type: "error", message: t("account.packages.permissions.messages.revokeError") });
    } finally {
      setPermissionLoading(false);
    }
  };

  const providerOptions = useMemo(() => {
    const values = new Set(resources.map((item) => item.provider).filter(Boolean));
    return ["all", ...Array.from(values).sort()];
  }, [resources]);

  const uploadProviderOptions = useMemo(() => {
    const values = new Set(resources.map((item) => item.provider).filter(Boolean));
    values.add("local");
    values.add("db");
    return Array.from(values).sort();
  }, [resources]);

  const kvPayload = useMemo(() => buildKvPayload(kvEntries), [kvEntries]);
  const kvResourceSize = useMemo(
    () => new Blob([kvPayload.json || "{}"]).size,
    [kvPayload.json],
  );
  const vaultRequirements = useMemo<ManifestVaultRequirement[]>(
    () => packageDetail?.manifest?.requirements?.vault ?? [],
    [packageDetail],
  );
  const permissionRequirements = useMemo<ManifestPermissionRequirement[]>(
    () => packageDetail?.manifest?.requirements?.permissions ?? [],
    [packageDetail],
  );
  const permissionByKey = useMemo(() => {
    return new Map(permissionItems.map((item) => [item.permissionKey, item]));
  }, [permissionItems]);
  const selectedPackageSummary = useMemo(() => {
    return packages.find((item) => resolvePackageRef(item) === selectedPackage) ?? null;
  }, [packages, selectedPackage]);
  const selectedPackageOwner = useMemo(
    () => (selectedPackageSummary ? resolvePackageOwner(selectedPackageSummary) : null),
    [selectedPackageSummary],
  );
  const selectedPackageDescription = resolveLocalizedText(selectedPackageSummary?.description);

  useEffect(() => {
    if (!selectedPackage) {
      setVaultDrafts({});
      return;
    }
    const next: Record<string, string> = {};
    vaultRequirements.forEach((requirement) => {
      const existing = vaultItems.find((item) => item.key === requirement.key);
      next[requirement.key] = existing?.value ?? "";
    });
    setVaultDrafts(next);
  }, [selectedPackage, vaultRequirements, vaultItems]);

  const typeOptions = useMemo(() => {
    const values = new Set(resources.map((item) => item.type).filter(Boolean));
    return ["all", ...Array.from(values).sort()];
  }, [resources]);

  const filteredResources = useMemo(() => {
    return resources.filter((resource) => {
      if (providerFilter !== "all" && resource.provider !== providerFilter) {
        return false;
      }
      if (typeFilter !== "all" && resource.type !== typeFilter) {
        return false;
      }
      return true;
    });
  }, [resources, providerFilter, typeFilter]);

  const hasProfileChanges = Boolean(profile && displayName.trim() && displayName.trim() !== profile.displayName);
  const displayNameLabel = profile?.displayName || t("account.profile.fallbackDisplayName");
  const usernameLabel = profile?.username || t("account.profile.fallbackUsername");
  const userIdLabel = profile?.userId || t("account.profile.fallbackUserId");
  const roleCountLabel = profile ? `${profile.roles.length}` : "-";
  const statusLabel = profile
    ? profile.isActive
      ? t("account.profile.status.active")
      : t("account.profile.status.disabled")
    : t("account.profile.status.checking");
  const statusClass = profile ? (profile.isActive ? "is-active" : "is-disabled") : "is-unknown";
  const resourceCountLabel = resourceLoading ? "..." : resourceError ? "-" : `${resources.length}`;
  const packagesLoaded =
    packagesLoading || packagesError !== null || packages.length > 0 || activeSection === "packages";
  const packagesCountLabel = packagesLoading ? "..." : packagesLoaded ? `${packages.length}` : "-";
  const profileInitials = useMemo(() => {
    const source = `${displayNameLabel || ""}`.trim() || `${usernameLabel || ""}`.trim() || "AstraFlow";
    const initials = source
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("");
    return initials ? initials.toUpperCase() : "AF";
  }, [displayNameLabel, usernameLabel]);

  return (
    <div className="account-page">
      <div className="account-header">
        <div className="account-header__intro">
          <span className="account-kicker">{t("account.kicker")}</span>
          <h2>{t("account.title")}</h2>
          <p className="text-subtle">{t("account.subtitle")}</p>
        </div>
        <div className="account-hero">
          <div className="account-hero__profile">
            <div className="account-hero__avatar" aria-hidden="true">
              {profileInitials}
            </div>
            <div className="account-hero__identity">
              <div className="account-hero__name">{displayNameLabel}</div>
              <div className="account-hero__meta">
                <span>@{usernameLabel}</span>
                <span className="account-hero__dot" aria-hidden="true" />
                <span>{t("common.id")} {userIdLabel}</span>
              </div>
              <div className={`account-hero__status ${statusClass}`}>
                <span className="account-hero__status-dot" aria-hidden="true" />
                {statusLabel}
              </div>
            </div>
          </div>
          <div className="account-hero__stats">
            <div className="account-hero__stat">
              <span className="account-hero__stat-label">{t("account.stats.resources")}</span>
              <span className="account-hero__stat-value">{resourceCountLabel}</span>
            </div>
            <div className="account-hero__stat">
              <span className="account-hero__stat-label">{t("account.stats.packages")}</span>
              <span className="account-hero__stat-value">{packagesCountLabel}</span>
            </div>
            <div className="account-hero__stat">
              <span className="account-hero__stat-label">{t("account.stats.roles")}</span>
              <span className="account-hero__stat-value">{roleCountLabel}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="account-layout">
        <aside className="account-sidebar">
          <nav className="account-menu">
            <button
              type="button"
              className={`account-menu__button${activeSection === "profile" ? " is-active" : ""}`}
              onClick={() => setActiveSection("profile")}
            >
              {t("account.menu.profile")}
            </button>
            <button
              type="button"
              className={`account-menu__button${activeSection === "resources" ? " is-active" : ""}`}
              onClick={() => setActiveSection("resources")}
            >
              {t("account.menu.resources")}
            </button>
            <button
              type="button"
              className={`account-menu__button${activeSection === "packages" ? " is-active" : ""}`}
              onClick={() => setActiveSection("packages")}
            >
              {t("account.menu.packages")}
            </button>
          </nav>
        </aside>

        <section className="account-content">
          {activeSection === "profile" && (
            <div className="card account-section account-section--profile">
              <header className="card__header account-section__header">
                <div>
                  <span className="account-section__eyebrow">{t("account.profile.eyebrow")}</span>
                  <h3>{t("account.profile.title")}</h3>
                  <p className="text-subtle account-section__description">{t("account.profile.subtitle")}</p>
                </div>
              </header>
              {profile ? (
                <div className="stack">
                  <div className="account-field">
                    <span className="account-field__label">{t("account.profile.displayName")}</span>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                    />
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">{t("account.profile.username")}</span>
                    <div className="account__mono">{profile.username}</div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">{t("account.profile.userId")}</span>
                    <div className="account__mono">{profile.userId}</div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">{t("account.profile.roles")}</span>
                    <div className="account-inline">
                      {profile.roles.map((role) => (
                        <span key={role} className="account-pill account-pill--muted">
                          {role}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">{t("account.profile.status.label")}</span>
                    <div className={`account-status ${profile.isActive ? "" : "account-status--error"}`}>
                      {profile.isActive
                        ? t("account.profile.status.active")
                        : t("account.profile.status.disabled")}
                    </div>
                  </div>
                  <div className="account-actions">
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={handleSaveProfile}
                      disabled={saving || !hasProfileChanges}
                    >
                      {saving ? t("account.profile.actions.saving") : t("account.profile.actions.save")}
                    </button>
                    <button type="button" className="btn btn--ghost" onClick={loadProfile}>
                      {t("common.refresh")}
                    </button>
                  </div>
                  {profileStatus.type !== "idle" && (
                    <div
                      className={`account-note ${
                        profileStatus.type === "error" ? "account-status--error" : "account-status--success"
                      }`}
                    >
                      {profileStatus.message}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-subtle">{t("account.profile.messages.empty")}</p>
              )}
            </div>
          )}

          {activeSection === "resources" && (
            <div className="card account-section account-section--resources">
              <header className="card__header account-section__header">
                <div>
                  <span className="account-section__eyebrow">{t("account.resources.eyebrow")}</span>
                  <h3>{t("account.resources.title")}</h3>
                  <p className="text-subtle account-section__description">{t("account.resources.subtitle")}</p>
                </div>
              </header>
              <div className="stack">
                <div className="account-resource-upload">
                  <div className="account-upload-card">
                    <label className="account-upload-dropzone">
                      <input
                        className="account-upload-input"
                        type="file"
                        multiple
                        onChange={handleUploadInput}
                        disabled={uploading}
                      />
                      <span className="account-upload-title">{t("account.resources.upload.title")}</span>
                      <span className="account-upload-subtitle">{t("account.resources.upload.subtitle")}</span>
                    </label>
                    <div className="account-upload-options">
                      <label className="account-field account-resource-upload__field">
                        <span className="account-field__label">{t("account.resources.upload.provider")}</span>
                        <select
                          value={uploadProvider}
                          onChange={(event) => setUploadProvider(event.target.value)}
                          disabled={uploading}
                        >
                          <option value="default">{t("account.resources.upload.defaultProvider")}</option>
                          {uploadProviderOptions.map((provider) => (
                            <option key={provider} value={provider}>
                              {provider}
                            </option>
                          ))}
                        </select>
                      </label>
                      {uploading && <span className="account-upload-status">{t("account.resources.upload.uploading")}</span>}
                    </div>
                  </div>
                  <div className="account-kv-resource">
                    <div className="account-kv-resource__header">
                      <div>
                        <h4>{t("account.resources.kv.title")}</h4>
                        <p className="text-subtle">{t("account.resources.kv.subtitle")}</p>
                      </div>
                      <span className="account-kv-resource__size">{formatBytes(kvResourceSize)}</span>
                    </div>
                    <div className="account-kv-resource__meta">
                      <label className="account-field">
                        <span className="account-field__label">{t("account.resources.kv.resourceName")}</span>
                        <input
                          type="text"
                          value={kvResourceName}
                          onChange={(event) => setKvResourceName(event.target.value)}
                          placeholder={t("account.resources.kv.resourceNamePlaceholder")}
                          disabled={uploading}
                        />
                      </label>
                    </div>
                    <div className="account-kv-resource__table">
                      <div className="account-kv-resource__row account-kv-resource__row--header">
                        <span>{t("account.resources.kv.key")}</span>
                        <span>{t("account.resources.kv.value")}</span>
                        <span />
                      </div>
                      {kvEntries.map((entry, index) => (
                        <div key={entry.id} className="account-kv-resource__row">
                          <input
                            className="account-kv-resource__input"
                            type="text"
                            value={entry.key}
                            onChange={(event) => updateKvEntry(entry.id, { key: event.target.value })}
                            placeholder={
                              index === 0
                                ? t("account.resources.kv.keyPrimaryPlaceholder")
                                : t("account.resources.kv.keyPlaceholder")
                            }
                            disabled={uploading}
                          />
                          <textarea
                            className="account-kv-resource__textarea"
                            rows={2}
                            value={entry.value}
                            onChange={(event) => updateKvEntry(entry.id, { value: event.target.value })}
                            placeholder={t("account.resources.kv.valuePlaceholder")}
                            disabled={uploading}
                          />
                          {kvEntries.length > 1 ? (
                            <button
                              type="button"
                              className="btn btn--ghost"
                              onClick={() => handleRemoveKvEntry(entry.id)}
                              disabled={uploading}
                            >
                              {t("account.resources.kv.removeRow")}
                            </button>
                          ) : (
                            <span className="account-kv-resource__spacer" />
                          )}
                        </div>
                      ))}
                    </div>
                    {kvPayload.duplicates.length > 0 && (
                      <p className="account-kv-resource__warning">
                        {t("account.resources.messages.duplicateKeys", { keys: kvPayload.duplicates.join(", ") })}
                      </p>
                    )}
                    <div className="account-kv-resource__actions">
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={handleAddKvEntry}
                        disabled={uploading}
                      >
                        {t("account.resources.kv.addRow")}
                      </button>
                      <button
                        type="button"
                        className="btn btn--primary"
                        onClick={handleCreateKeyValueResource}
                        disabled={uploading || !kvPayload.keys.length || kvPayload.duplicates.length > 0}
                      >
                        {t("account.resources.kv.create")}
                      </button>
                    </div>
                    <p className="account-kv-resource__hint">{t("account.resources.kv.hint")}</p>
                  </div>
                  {uploadError && <p className="error">{uploadError}</p>}
                  {uploadEntries.length > 0 && (
                    <ul className="account-upload-list">
                      {uploadEntries.map((entry) => {
                        const progressPct = Math.round(Math.min(100, Math.max(0, entry.progress * 100)));
                        const statusLabel =
                          entry.status === "error"
                            ? t("account.resources.upload.status.failed")
                            : entry.status === "queued"
                              ? t("account.resources.upload.status.queued")
                              : `${progressPct}%`;
                        return (
                          <li key={entry.key} className="account-upload-item">
                            <div className="account-upload-row">
                              <span className="account-upload-name">{entry.name}</span>
                              <span className="account-upload-meta">{formatBytes(entry.size)}</span>
                              <span className="account-upload-progress-text">{statusLabel}</span>
                              {entry.status === "error" && (
                                <button
                                  type="button"
                                  className="btn btn--ghost"
                                  onClick={() => handleDismissUpload(entry.key)}
                                >
                                  {t("account.resources.upload.remove")}
                                </button>
                              )}
                            </div>
                            <div className="account-upload-bar">
                              <div className="account-upload-progress" style={{ width: `${progressPct}%` }} />
                            </div>
                            {entry.error && <div className="account-upload-error">{entry.error}</div>}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                <div className="account-resource-panel">
                    <div className="account-resource-toolbar">
                      <div className="account-resource-filters">
                        <label className="account-field">
                          <span className="account-field__label">{t("account.resources.filters.search")}</span>
                          <input
                            type="text"
                            placeholder={t("account.resources.filters.searchPlaceholder")}
                            value={resourceSearch}
                            onChange={(event) => setResourceSearch(event.target.value)}
                          />
                        </label>
                        <label className="account-field">
                          <span className="account-field__label">{t("account.resources.filters.provider")}</span>
                          <select value={providerFilter} onChange={(event) => setProviderFilter(event.target.value)}>
                            {providerOptions.map((provider) => (
                              <option key={provider} value={provider}>
                                {provider === "all" ? t("account.resources.filters.allProviders") : provider}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="account-field">
                          <span className="account-field__label">{t("account.resources.filters.type")}</span>
                          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
                            {typeOptions.map((type) => (
                              <option key={type} value={type}>
                                {type === "all" ? t("account.resources.filters.allTypes") : type}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <div className="account-actions">
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={() => loadResources(resourceSearch)}
                          disabled={resourceLoading}
                        >
                          {resourceLoading ? t("account.resources.actions.refreshing") : t("common.refresh")}
                        </button>
                      </div>
                    </div>

                  <div className="account-resource-table-wrap">
                    {resourceError && <p className="error">{resourceError}</p>}
                    {resourceLoading && <p className="text-subtle">{t("account.resources.messages.loading")}</p>}
                    {!resourceLoading && filteredResources.length === 0 && (
                      <p className="text-subtle">{t("account.resources.messages.empty")}</p>
                    )}
                    {!resourceLoading && filteredResources.length > 0 && (
                      <table className="data-table account-resource-table">
                        <thead>
                          <tr>
                            <th>{t("account.resources.table.file")}</th>
                            <th>{t("account.resources.table.resourceId")}</th>
                            <th>{t("account.resources.table.provider")}</th>
                            <th>{t("account.resources.table.type")}</th>
                            <th>{t("account.resources.table.size")}</th>
                            <th>{t("account.resources.table.created")}</th>
                            <th>{t("account.resources.table.actions")}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredResources.map((resource) => {
                            const previewKind = inferPreviewKind(resource);
                            const preview = previews[resource.resourceId];
                            return (
                              <Fragment key={resource.resourceId}>
                                <tr>
                                  <td>{resource.filename || resource.resourceId}</td>
                                  <td className="account__mono">{resource.resourceId}</td>
                                  <td>
                                    <span className="account-pill">{resource.provider}</span>
                                  </td>
                                  <td>{resource.type}</td>
                                  <td>{formatResourceSize(resource.sizeBytes)}</td>
                                  <td>{formatDate(resource.createdAt)}</td>
                                  <td>
                                    <div className="account-resource-actions">
                                      {previewKind && (
                                        <button
                                          type="button"
                                          className={`btn btn--ghost account-resource-preview-toggle${
                                            preview ? " is-active" : ""
                                          }`}
                                          onClick={() => handleTogglePreview(resource)}
                                        >
                                          {preview?.status === "loading"
                                            ? t("account.resources.preview.loading")
                                            : preview
                                              ? t("account.resources.preview.hide")
                                              : t("account.resources.preview.show")}
                                        </button>
                                      )}
                                      <button
                                        type="button"
                                        className="btn btn--ghost"
                                        onClick={() =>
                                          resourcesGateway.download(resource.resourceId, resource.filename ?? undefined)
                                        }
                                      >
                                        {t("account.resources.actions.download")}
                                      </button>
                                      <button
                                        type="button"
                                        className="btn btn--ghost"
                                        onClick={() => handleDeleteResource(resource.resourceId)}
                                      >
                                        {t("account.resources.actions.delete")}
                                      </button>
                                    </div>
                                  </td>
                                </tr>
                                {preview && (
                                  <tr className="account-resource-preview-row">
                                    <td colSpan={7}>
                                      <div className="account-resource-preview">
                                        {preview.status === "loading" && <span>{t("account.resources.preview.loadingDetail")}</span>}
                                        {preview.status === "error" && (
                                          <span className="account-resource-preview__error">{preview.error}</span>
                                        )}
                                        {preview.status === "ready" && preview.url && preview.kind === "image" && (
                                          <img
                                            src={preview.url}
                                            alt={resource.filename ?? t("account.resources.preview.altFallback")}
                                          />
                                        )}
                                        {preview.status === "ready" && preview.url && preview.kind === "video" && (
                                          <video src={preview.url} controls preload="metadata" />
                                        )}
                                        {preview.status === "ready" && preview.url && preview.kind === "audio" && (
                                          <audio src={preview.url} controls preload="metadata" />
                                        )}
                                      </div>
                                    </td>
                                  </tr>
                                )}
                              </Fragment>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
          {activeSection === "packages" && (
            <div className="card account-section account-section--packages">
              <header className="card__header account-section__header">
                <div>
                  <span className="account-section__eyebrow">{t("account.packages.eyebrow")}</span>
                  <h3>{t("account.packages.title")}</h3>
                  <p className="text-subtle account-section__description">{t("account.packages.subtitle")}</p>
                </div>
              </header>
              <div className="account-package">
                <aside className="account-package__sidebar">
                  <div className="account-package__sidebar-header">
                    <div>
                      <h4>{t("account.packages.listTitle")}</h4>
                      <p className="text-subtle">{t("account.packages.listSubtitle")}</p>
                    </div>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={loadPackages}
                      disabled={packagesLoading}
                    >
                      {packagesLoading ? t("account.packages.actions.refreshing") : t("common.refresh")}
                    </button>
                  </div>
                  {packagesError && <p className="error">{packagesError}</p>}
                  {packagesLoading && <p className="text-subtle">{t("account.packages.messages.loading")}</p>}
                  {!packagesLoading && packages.length === 0 && (
                    <p className="text-subtle">{t("account.packages.messages.empty")}</p>
                  )}
                  <div className="account-package__list">
                    {packages.map((pkg) => {
                      const version = pkg.defaultVersion || pkg.latestVersion || "latest";
                      const packageRef = resolvePackageRef(pkg);
                      const ownerLabel = resolvePackageOwner(pkg);
                      return (
                        <button
                          key={packageRef}
                          type="button"
                          className={`account-package__item${selectedPackage === packageRef ? " is-active" : ""}`}
                          onClick={() => setSelectedPackage(packageRef)}
                        >
                          <span className="account-package__identity">
                            <span className="account-package__name">{pkg.name}</span>
                            {ownerLabel && <span className="account-package__owner">@{ownerLabel}</span>}
                          </span>
                          <span className="account-package__version">{version}</span>
                        </button>
                      );
                    })}
                  </div>
                </aside>
                <div className="account-package__content">
                  {!selectedPackage && (
                    <p className="text-subtle">{t("account.packages.messages.selectPackage")}</p>
                  )}
                  {selectedPackage && (
                    <div className="stack">
                      <div className="account-package__header">
                        <div>
                          <h4>{selectedPackageSummary?.name ?? selectedPackage}</h4>
                          {selectedPackageOwner && <p className="text-subtle">@{selectedPackageOwner}</p>}
                          {selectedPackageDescription && (
                            <p className="text-subtle">{selectedPackageDescription}</p>
                          )}
                        </div>
                        <span className="account-pill account-pill--muted">
                          {selectedPackageSummary?.defaultVersion ||
                            selectedPackageSummary?.latestVersion ||
                            t("account.packages.latest")}
                        </span>
                      </div>
                      {packageDetailLoading && (
                        <p className="text-subtle">{t("account.packages.messages.loadingRequirements")}</p>
                      )}
                      {packageDetailError && <p className="error">{packageDetailError}</p>}
                      {!packageDetailLoading &&
                        !packageDetailError &&
                        vaultRequirements.length === 0 &&
                        permissionRequirements.length === 0 && (
                          <p className="text-subtle">{t("account.packages.messages.noRequirements")}</p>
                        )}
                      {vaultRequirements.length > 0 && (
                        <div className="account-package__panel">
                          <div className="account-package__panel-header">
                            <div>
                              <h4>{t("account.packages.vault.title")}</h4>
                              <p className="text-subtle">{t("account.packages.vault.subtitle")}</p>
                            </div>
                            <div className="account-actions">
                              <button
                                type="button"
                                className="btn btn--primary"
                                onClick={handleSaveVault}
                                disabled={vaultLoading}
                              >
                                {vaultLoading
                                  ? t("account.packages.vault.actions.saving")
                                  : t("account.packages.vault.actions.save")}
                              </button>
                              <button
                                type="button"
                                className="btn btn--ghost"
                                onClick={() => loadPackageVault(selectedPackage)}
                                disabled={vaultLoading}
                              >
                                {t("common.refresh")}
                              </button>
                            </div>
                          </div>
                          <div className="account-package__rows">
                            {vaultRequirements.map((requirement) => {
                              const value = vaultDrafts[requirement.key] ?? "";
                              const stored = vaultItems.find((item) => item.key === requirement.key);
                              const isSecret = requirement.type?.toLowerCase() === "secret";
                              const isJson = requirement.type?.toLowerCase() === "json";
                              const isRequired = requirement.required !== false;
                              const requirementLabel = resolveLocalizedText(requirement.label);
                              const requirementDescription = resolveLocalizedText(requirement.description);
                              return (
                                <div key={requirement.key} className="account-package__row">
                                  <div className="account-package__meta">
                                    <div className="account-package__title">
                                      <span className="account-pill">{requirement.key}</span>
                                      <span className="account-pill account-pill--muted">{requirement.type}</span>
                                      <span
                                        className={`account-pill ${
                                          isRequired ? "" : "account-pill--muted"
                                        }`}
                                      >
                                        {isRequired
                                          ? t("account.packages.requirement.required")
                                          : t("account.packages.requirement.optional")}
                                      </span>
                                    </div>
                                    {requirementLabel && requirementLabel !== requirement.key && (
                                      <div className="account-package__label">{requirementLabel}</div>
                                    )}
                                    {requirementDescription && (
                                      <p className="text-subtle">{requirementDescription}</p>
                                    )}
                                  </div>
                                  <div className="account-package__input">
                                    {isJson ? (
                                      <textarea
                                        rows={3}
                                        value={value}
                                        placeholder={t("account.packages.vault.jsonPlaceholder")}
                                        onChange={(event) =>
                                          setVaultDrafts((prev) => ({
                                            ...prev,
                                            [requirement.key]: event.target.value,
                                          }))
                                        }
                                      />
                                    ) : (
                                      <input
                                        type={isSecret ? "password" : "text"}
                                        value={value}
                                        placeholder={requirement.key}
                                        onChange={(event) =>
                                          setVaultDrafts((prev) => ({
                                            ...prev,
                                            [requirement.key]: event.target.value,
                                          }))
                                        }
                                      />
                                    )}
                                  </div>
                                  <div className="account-package__actions">
                                    {stored && !isRequired && (
                                      <button
                                        type="button"
                                        className="btn btn--ghost"
                                        onClick={() => handleDeleteVaultItem(requirement.key)}
                                        disabled={vaultLoading}
                                      >
                                        {t("account.packages.vault.actions.remove")}
                                      </button>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                          {vaultStatus.type !== "idle" && (
                            <p
                              className={`account-note ${
                                vaultStatus.type === "error" ? "account-status--error" : "account-status--success"
                              }`}
                            >
                              {vaultStatus.message}
                            </p>
                          )}
                        </div>
                      )}
                      {permissionRequirements.length > 0 && (
                        <div className="account-package__panel">
                          <div className="account-package__panel-header">
                            <div>
                              <h4>{t("account.packages.permissions.title")}</h4>
                              <p className="text-subtle">{t("account.packages.permissions.subtitle")}</p>
                            </div>
                            <button
                              type="button"
                              className="btn btn--ghost"
                              onClick={() => loadPackagePermissions(selectedPackage)}
                              disabled={permissionLoading}
                            >
                              {t("common.refresh")}
                            </button>
                          </div>
                          <div className="account-package__rows">
                            {permissionRequirements.map((requirement) => {
                              const granted = permissionByKey.get(requirement.key);
                              const actions =
                                requirement.actions && requirement.actions.length
                                  ? requirement.actions.join(", ")
                                  : t("account.packages.permissions.defaultAction");
                              const types = requirement.types?.join(", ") ?? "-";
                              const isRequired = requirement.required !== false;
                              const requirementDescription = resolveLocalizedText(requirement.description);
                              return (
                                <div key={requirement.key} className="account-package__row">
                                  <div className="account-package__meta">
                                    <div className="account-package__title">
                                      <span className="account-pill">{requirement.key}</span>
                                      <span className="account-pill account-pill--muted">{types}</span>
                                      <span
                                        className={`account-pill ${
                                          isRequired ? "" : "account-pill--muted"
                                        }`}
                                      >
                                        {isRequired
                                          ? t("account.packages.requirement.required")
                                          : t("account.packages.requirement.optional")}
                                      </span>
                                    </div>
                                    {requirementDescription && (
                                      <p className="text-subtle">{requirementDescription}</p>
                                    )}
                                    <div className="account-package__hint">
                                      {t("account.packages.permissions.actionsLabel", { actions })}
                                    </div>
                                  </div>
                                  <div className="account-package__actions">
                                    {granted ? (
                                      <button
                                        type="button"
                                        className="btn btn--ghost"
                                        onClick={() => handleRevokePermission(granted)}
                                        disabled={permissionLoading}
                                      >
                                        {t("account.packages.permissions.actions.revoke")}
                                      </button>
                                    ) : (
                                      <button
                                        type="button"
                                        className="btn btn--primary"
                                        onClick={() => handleGrantPermission(requirement)}
                                        disabled={permissionLoading}
                                      >
                                        {t("account.packages.permissions.actions.grant")}
                                      </button>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                          {permissionStatus.type !== "idle" && (
                            <p
                              className={`account-note ${
                                permissionStatus.type === "error"
                                  ? "account-status--error"
                                  : "account-status--success"
                              }`}
                            >
                              {permissionStatus.message}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default AccountPage;
