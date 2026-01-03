import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
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
      setProfileStatus({ type: "error", message: "Unable to load profile." });
    }
  }, [updateUser]);

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
        setResourceError("Unable to load resources.");
      } finally {
        setResourceLoading(false);
      }
    },
    []
  );

  const loadPackages = useCallback(async () => {
    setPackagesLoading(true);
    setPackagesError(null);
    try {
      const items = await listPackages();
      const sorted = [...items].sort((a, b) => a.name.localeCompare(b.name));
      setPackages(sorted);
      setSelectedPackage((prev) => {
        if (prev && sorted.some((item) => item.name === prev)) {
          return prev;
        }
        return sorted[0]?.name ?? "";
      });
    } catch (error) {
      console.error("Failed to load packages", error);
      setPackages([]);
      setPackagesError("Unable to load packages.");
    } finally {
      setPackagesLoading(false);
    }
  }, []);

  const loadPackageDetail = useCallback(async (packageName: string) => {
    setPackageDetailLoading(true);
    setPackageDetailError(null);
    try {
      const detail = await getPackage(packageName);
      setPackageDetail(detail);
    } catch (error) {
      console.error("Failed to load package detail", error);
      setPackageDetail(null);
      setPackageDetailError("Unable to load package requirements.");
    } finally {
      setPackageDetailLoading(false);
    }
  }, []);

  const loadPackageVault = useCallback(async (packageName: string) => {
    setVaultLoading(true);
    setVaultStatus({ type: "idle" });
    try {
      const items = await packageAccessGateway.listVault(packageName);
      setVaultItems(items);
    } catch (error) {
      console.error("Failed to load package vault", error);
      setVaultItems([]);
      setVaultStatus({ type: "error", message: "Unable to load vault entries." });
    } finally {
      setVaultLoading(false);
    }
  }, []);

  const loadPackagePermissions = useCallback(async (packageName: string) => {
    setPermissionLoading(true);
    setPermissionStatus({ type: "idle" });
    try {
      const items = await packageAccessGateway.listPermissions(packageName);
      setPermissionItems(items);
    } catch (error) {
      console.error("Failed to load package permissions", error);
      setPermissionItems([]);
      setPermissionStatus({ type: "error", message: "Unable to load permissions." });
    } finally {
      setPermissionLoading(false);
    }
  }, []);

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
      setProfileStatus({ type: "error", message: "Display name is required." });
      return;
    }
    setSaving(true);
    setProfileStatus({ type: "idle" });
    try {
      const updated = await accountGateway.updateProfile({ displayName: nextName });
      setProfile(updated);
      setDisplayName(updated.displayName);
      updateUser(updated);
      setProfileStatus({ type: "success", message: "Profile updated." });
    } catch (error) {
      console.error("Failed to update profile", error);
      setProfileStatus({ type: "error", message: "Unable to update profile." });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteResource = async (resourceId: string) => {
    if (!window.confirm("Delete this resource?")) {
      return;
    }
    try {
      await resourcesGateway.delete(resourceId);
      setResources((prev) => prev.filter((item) => item.resourceId !== resourceId));
    } catch (error) {
      console.error("Failed to delete resource", error);
      setResourceError("Unable to delete resource.");
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
          const message = (error as { message?: string })?.message ?? "Upload failed.";
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
    [loadResources, resourceSearch, uploadProvider, uploading],
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
      setUploadError(`Duplicate keys: ${payload.duplicates.join(", ")}`);
      return;
    }
    if (!payload.json || !payload.keys.length) {
      setUploadError("Add at least one key-value pair.");
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
      const message = (error as { message?: string })?.message ?? "Failed to load preview.";
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
        message: `Missing required entries: ${missingRequired.map((item) => item.key).join(", ")}`,
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
      setVaultStatus({ type: "success", message: "Vault entries updated." });
    } catch (error) {
      console.error("Failed to update vault", error);
      setVaultStatus({ type: "error", message: "Unable to update vault." });
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
      setVaultStatus({ type: "success", message: "Vault entry deleted." });
    } catch (error) {
      console.error("Failed to delete vault entry", error);
      setVaultStatus({ type: "error", message: "Unable to delete vault entry." });
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
      setPermissionStatus({ type: "success", message: "Permission granted." });
    } catch (error) {
      console.error("Failed to grant permission", error);
      setPermissionStatus({ type: "error", message: "Unable to grant permission." });
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
      setPermissionStatus({ type: "success", message: "Permission revoked." });
    } catch (error) {
      console.error("Failed to revoke permission", error);
      setPermissionStatus({ type: "error", message: "Unable to revoke permission." });
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
    return packages.find((item) => item.name === selectedPackage) ?? null;
  }, [packages, selectedPackage]);

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
  const displayNameLabel = profile?.displayName || "AstraFlow User";
  const usernameLabel = profile?.username || "unknown";
  const userIdLabel = profile?.userId || "-";
  const roleCountLabel = profile ? `${profile.roles.length}` : "-";
  const statusLabel = profile ? (profile.isActive ? "Active" : "Disabled") : "Checking...";
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
          <span className="account-kicker">Personal Console</span>
          <h2>Account</h2>
          <p className="text-subtle">Manage your profile and personal resources.</p>
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
                <span>ID {userIdLabel}</span>
              </div>
              <div className={`account-hero__status ${statusClass}`}>
                <span className="account-hero__status-dot" aria-hidden="true" />
                {statusLabel}
              </div>
            </div>
          </div>
          <div className="account-hero__stats">
            <div className="account-hero__stat">
              <span className="account-hero__stat-label">Resources</span>
              <span className="account-hero__stat-value">{resourceCountLabel}</span>
            </div>
            <div className="account-hero__stat">
              <span className="account-hero__stat-label">Packages</span>
              <span className="account-hero__stat-value">{packagesCountLabel}</span>
            </div>
            <div className="account-hero__stat">
              <span className="account-hero__stat-label">Roles</span>
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
              Personal Panel
            </button>
            <button
              type="button"
              className={`account-menu__button${activeSection === "resources" ? " is-active" : ""}`}
              onClick={() => setActiveSection("resources")}
            >
              Resource Center
            </button>
            <button
              type="button"
              className={`account-menu__button${activeSection === "packages" ? " is-active" : ""}`}
              onClick={() => setActiveSection("packages")}
            >
              Package Vault
            </button>
          </nav>
        </aside>

        <section className="account-content">
          {activeSection === "profile" && (
            <div className="card account-section account-section--profile">
              <header className="card__header account-section__header">
                <div>
                  <span className="account-section__eyebrow">Profile</span>
                  <h3>Identity &amp; Access</h3>
                  <p className="text-subtle account-section__description">
                    Update your display name and review the access assigned to your account.
                  </p>
                </div>
              </header>
              {profile ? (
                <div className="stack">
                  <div className="account-field">
                    <span className="account-field__label">Display name</span>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                    />
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">Username</span>
                    <div className="account__mono">{profile.username}</div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">User id</span>
                    <div className="account__mono">{profile.userId}</div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">Roles</span>
                    <div className="account-inline">
                      {profile.roles.map((role) => (
                        <span key={role} className="account-pill account-pill--muted">
                          {role}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">Status</span>
                    <div className={`account-status ${profile.isActive ? "" : "account-status--error"}`}>
                      {profile.isActive ? "Active" : "Disabled"}
                    </div>
                  </div>
                  <div className="account-actions">
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={handleSaveProfile}
                      disabled={saving || !hasProfileChanges}
                    >
                      {saving ? "Saving..." : "Save changes"}
                    </button>
                    <button type="button" className="btn btn--ghost" onClick={loadProfile}>
                      Refresh
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
                <p className="text-subtle">No profile loaded.</p>
              )}
            </div>
          )}

          {activeSection === "resources" && (
            <div className="card account-section account-section--resources">
              <header className="card__header account-section__header">
                <div>
                  <span className="account-section__eyebrow">Resources</span>
                  <h3>Resource Library</h3>
                  <p className="text-subtle account-section__description">
                    Upload files, manage key-value assets, and preview stored artifacts.
                  </p>
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
                      <span className="account-upload-title">Upload files</span>
                      <span className="account-upload-subtitle">Drag &amp; drop or click to browse.</span>
                    </label>
                    <div className="account-upload-options">
                      <label className="account-field account-resource-upload__field">
                        <span className="account-field__label">Provider</span>
                        <select
                          value={uploadProvider}
                          onChange={(event) => setUploadProvider(event.target.value)}
                          disabled={uploading}
                        >
                          <option value="default">Default provider</option>
                          {uploadProviderOptions.map((provider) => (
                            <option key={provider} value={provider}>
                              {provider}
                            </option>
                          ))}
                        </select>
                      </label>
                      {uploading && <span className="account-upload-status">Uploading...</span>}
                    </div>
                  </div>
                  <div className="account-kv-resource">
                    <div className="account-kv-resource__header">
                      <div>
                        <h4>Key-value resource</h4>
                        <p className="text-subtle">Store secrets and configuration pairs without uploading files.</p>
                      </div>
                      <span className="account-kv-resource__size">{formatBytes(kvResourceSize)}</span>
                    </div>
                    <div className="account-kv-resource__meta">
                      <label className="account-field">
                        <span className="account-field__label">Resource name</span>
                        <input
                          type="text"
                          value={kvResourceName}
                          onChange={(event) => setKvResourceName(event.target.value)}
                          placeholder="key-values.json"
                          disabled={uploading}
                        />
                      </label>
                    </div>
                    <div className="account-kv-resource__table">
                      <div className="account-kv-resource__row account-kv-resource__row--header">
                        <span>Key</span>
                        <span>Value</span>
                        <span />
                      </div>
                      {kvEntries.map((entry, index) => (
                        <div key={entry.id} className="account-kv-resource__row">
                          <input
                            className="account-kv-resource__input"
                            type="text"
                            value={entry.key}
                            onChange={(event) => updateKvEntry(entry.id, { key: event.target.value })}
                            placeholder={index === 0 ? "OPENAI_API_KEY" : "KEY"}
                            disabled={uploading}
                          />
                          <textarea
                            className="account-kv-resource__textarea"
                            rows={2}
                            value={entry.value}
                            onChange={(event) => updateKvEntry(entry.id, { value: event.target.value })}
                            placeholder="Value"
                            disabled={uploading}
                          />
                          {kvEntries.length > 1 ? (
                            <button
                              type="button"
                              className="btn btn--ghost"
                              onClick={() => handleRemoveKvEntry(entry.id)}
                              disabled={uploading}
                            >
                              Remove
                            </button>
                          ) : (
                            <span className="account-kv-resource__spacer" />
                          )}
                        </div>
                      ))}
                    </div>
                    {kvPayload.duplicates.length > 0 && (
                      <p className="account-kv-resource__warning">
                        Duplicate keys: {kvPayload.duplicates.join(", ")}
                      </p>
                    )}
                    <div className="account-kv-resource__actions">
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={handleAddKvEntry}
                        disabled={uploading}
                      >
                        Add row
                      </button>
                      <button
                        type="button"
                        className="btn btn--primary"
                        onClick={handleCreateKeyValueResource}
                        disabled={uploading || !kvPayload.keys.length || kvPayload.duplicates.length > 0}
                      >
                        Create resource
                      </button>
                    </div>
                    <p className="account-kv-resource__hint">Uses the provider selected above.</p>
                  </div>
                  {uploadError && <p className="error">{uploadError}</p>}
                  {uploadEntries.length > 0 && (
                    <ul className="account-upload-list">
                      {uploadEntries.map((entry) => {
                        const progressPct = Math.round(Math.min(100, Math.max(0, entry.progress * 100)));
                        const statusLabel =
                          entry.status === "error"
                            ? "Failed"
                            : entry.status === "queued"
                              ? "Queued"
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
                                  Remove
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
                        <span className="account-field__label">Search</span>
                        <input
                          type="text"
                          placeholder="filename or id"
                          value={resourceSearch}
                          onChange={(event) => setResourceSearch(event.target.value)}
                        />
                      </label>
                      <label className="account-field">
                        <span className="account-field__label">Provider</span>
                        <select value={providerFilter} onChange={(event) => setProviderFilter(event.target.value)}>
                          {providerOptions.map((provider) => (
                            <option key={provider} value={provider}>
                              {provider === "all" ? "All providers" : provider}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="account-field">
                        <span className="account-field__label">Type</span>
                        <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
                          {typeOptions.map((type) => (
                            <option key={type} value={type}>
                              {type === "all" ? "All types" : type}
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
                        {resourceLoading ? "Refreshing..." : "Refresh"}
                      </button>
                    </div>
                  </div>

                  <div className="account-resource-table-wrap">
                    {resourceError && <p className="error">{resourceError}</p>}
                    {resourceLoading && <p className="text-subtle">Loading resources...</p>}
                    {!resourceLoading && filteredResources.length === 0 && (
                      <p className="text-subtle">No resources found.</p>
                    )}
                    {!resourceLoading && filteredResources.length > 0 && (
                      <table className="data-table account-resource-table">
                        <thead>
                          <tr>
                            <th>File</th>
                            <th>Resource Id</th>
                            <th>Provider</th>
                            <th>Type</th>
                            <th>Size</th>
                            <th>Created</th>
                            <th>Actions</th>
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
                                          {preview?.status === "loading" ? "Loading" : preview ? "Hide" : "Preview"}
                                        </button>
                                      )}
                                      <button
                                        type="button"
                                        className="btn btn--ghost"
                                        onClick={() =>
                                          resourcesGateway.download(resource.resourceId, resource.filename ?? undefined)
                                        }
                                      >
                                        Download
                                      </button>
                                      <button
                                        type="button"
                                        className="btn btn--ghost"
                                        onClick={() => handleDeleteResource(resource.resourceId)}
                                      >
                                        Delete
                                      </button>
                                    </div>
                                  </td>
                                </tr>
                                {preview && (
                                  <tr className="account-resource-preview-row">
                                    <td colSpan={7}>
                                      <div className="account-resource-preview">
                                        {preview.status === "loading" && <span>Loading preview...</span>}
                                        {preview.status === "error" && (
                                          <span className="account-resource-preview__error">{preview.error}</span>
                                        )}
                                        {preview.status === "ready" && preview.url && preview.kind === "image" && (
                                          <img src={preview.url} alt={resource.filename ?? "preview"} />
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
                  <span className="account-section__eyebrow">Packages</span>
                  <h3>Package Vault</h3>
                  <p className="text-subtle account-section__description">
                    Manage secrets and permissions required by your packages.
                  </p>
                </div>
              </header>
              <div className="account-package">
                <aside className="account-package__sidebar">
                  <div className="account-package__sidebar-header">
                    <div>
                      <h4>Packages</h4>
                      <p className="text-subtle">Select a package to manage access.</p>
                    </div>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={loadPackages}
                      disabled={packagesLoading}
                    >
                      {packagesLoading ? "Refreshing..." : "Refresh"}
                    </button>
                  </div>
                  {packagesError && <p className="error">{packagesError}</p>}
                  {packagesLoading && <p className="text-subtle">Loading packages...</p>}
                  {!packagesLoading && packages.length === 0 && (
                    <p className="text-subtle">No packages found.</p>
                  )}
                  <div className="account-package__list">
                    {packages.map((pkg) => {
                      const version = pkg.defaultVersion || pkg.latestVersion || "latest";
                      return (
                        <button
                          key={pkg.name}
                          type="button"
                          className={`account-package__item${selectedPackage === pkg.name ? " is-active" : ""}`}
                          onClick={() => setSelectedPackage(pkg.name)}
                        >
                          <span className="account-package__name">{pkg.name}</span>
                          <span className="account-package__version">{version}</span>
                        </button>
                      );
                    })}
                  </div>
                </aside>
                <div className="account-package__content">
                  {!selectedPackage && (
                    <p className="text-subtle">Select a package from the list to configure its access.</p>
                  )}
                  {selectedPackage && (
                    <div className="stack">
                      <div className="account-package__header">
                        <div>
                          <h4>{selectedPackage}</h4>
                          {selectedPackageSummary?.description && (
                            <p className="text-subtle">{selectedPackageSummary.description}</p>
                          )}
                        </div>
                        <span className="account-pill account-pill--muted">
                          {selectedPackageSummary?.defaultVersion ||
                            selectedPackageSummary?.latestVersion ||
                            "latest"}
                        </span>
                      </div>
                      {packageDetailLoading && <p className="text-subtle">Loading package requirements...</p>}
                      {packageDetailError && <p className="error">{packageDetailError}</p>}
                      {!packageDetailLoading &&
                        !packageDetailError &&
                        vaultRequirements.length === 0 &&
                        permissionRequirements.length === 0 && (
                          <p className="text-subtle">This package does not request vault entries or permissions.</p>
                        )}
                      {vaultRequirements.length > 0 && (
                        <div className="account-package__panel">
                          <div className="account-package__panel-header">
                            <div>
                              <h4>Vault entries</h4>
                              <p className="text-subtle">Secrets and config stored per package.</p>
                            </div>
                            <div className="account-actions">
                              <button
                                type="button"
                                className="btn btn--primary"
                                onClick={handleSaveVault}
                                disabled={vaultLoading}
                              >
                                {vaultLoading ? "Saving..." : "Save"}
                              </button>
                              <button
                                type="button"
                                className="btn btn--ghost"
                                onClick={() => loadPackageVault(selectedPackage)}
                                disabled={vaultLoading}
                              >
                                Refresh
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
                                        {isRequired ? "Required" : "Optional"}
                                      </span>
                                    </div>
                                    {requirement.label && requirement.label !== requirement.key && (
                                      <div className="account-package__label">{requirement.label}</div>
                                    )}
                                    {requirement.description && (
                                      <p className="text-subtle">{requirement.description}</p>
                                    )}
                                  </div>
                                  <div className="account-package__input">
                                    {isJson ? (
                                      <textarea
                                        rows={3}
                                        value={value}
                                        placeholder="{}"
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
                                        Remove
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
                              <h4>Permissions</h4>
                              <p className="text-subtle">Grant packages access to resource types.</p>
                            </div>
                            <button
                              type="button"
                              className="btn btn--ghost"
                              onClick={() => loadPackagePermissions(selectedPackage)}
                              disabled={permissionLoading}
                            >
                              Refresh
                            </button>
                          </div>
                          <div className="account-package__rows">
                            {permissionRequirements.map((requirement) => {
                              const granted = permissionByKey.get(requirement.key);
                              const actions =
                                requirement.actions && requirement.actions.length
                                  ? requirement.actions.join(", ")
                                  : "read";
                              const types = requirement.types?.join(", ") ?? "-";
                              const isRequired = requirement.required !== false;
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
                                        {isRequired ? "Required" : "Optional"}
                                      </span>
                                    </div>
                                    {requirement.description && (
                                      <p className="text-subtle">{requirement.description}</p>
                                    )}
                                    <div className="account-package__hint">Actions: {actions}</div>
                                  </div>
                                  <div className="account-package__actions">
                                    {granted ? (
                                      <button
                                        type="button"
                                        className="btn btn--ghost"
                                        onClick={() => handleRevokePermission(granted)}
                                        disabled={permissionLoading}
                                      >
                                        Revoke
                                      </button>
                                    ) : (
                                      <button
                                        type="button"
                                        className="btn btn--primary"
                                        onClick={() => handleGrantPermission(requirement)}
                                        disabled={permissionLoading}
                                      >
                                        Grant
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
