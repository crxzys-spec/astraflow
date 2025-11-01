import clsx from "clsx";

interface StatusBadgeProps {
  status: string;
}

const COLORS: Record<string, string> = {
  succeeded: "badge--success",
  failed: "badge--danger",
  cancelled: "badge--warning",
  running: "badge--info",
  queued: "badge--muted"
};

export const StatusBadge = ({ status }: StatusBadgeProps) => {
  const normalized = status?.toLowerCase?.() ?? "unknown";
  return <span className={clsx("badge", COLORS[normalized] ?? "badge--muted")}>{status}</span>;
};

export default StatusBadge;
