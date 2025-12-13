export type NodeTraceInfo = {
  nodeId: string;
  status?: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  durationMs?: number | null;
};

export type MiddlewareTrace = {
  hostId: string;
  chain: string[];
  nodes: NodeTraceInfo[];
  totalDurationMs?: number | null;
};

export const buildMiddlewareTraces = (
  nodes?: { nodeId: string; metadata?: Record<string, unknown> | null; status?: string; startedAt?: string | null; finishedAt?: string | null }[]
): MiddlewareTrace[] => {
  if (!nodes?.length) return [];
  const hostToChain = new Map<string, string[]>();
  nodes.forEach((node) => {
    const meta = node.metadata as Record<string, unknown> | undefined;
    const mids = meta?.middlewares;
    if (Array.isArray(mids) && mids.length && !hostToChain.has(node.nodeId)) {
      const chain = mids
        .map((entry) => {
          if (typeof entry === "string") {
            return entry;
          }
          if (entry && typeof entry === "object") {
            const candidate = entry as { id?: unknown };
            return typeof candidate.id === "string" ? candidate.id : undefined;
          }
          return undefined;
        })
        .filter((id): id is string => typeof id === "string" && id.length > 0);
      if (chain.length) {
        hostToChain.set(node.nodeId, chain);
      }
    }
  });

  const traces: MiddlewareTrace[] = [];
  hostToChain.forEach((chain, hostId) => {
    const chainNodes: NodeTraceInfo[] = [];
    const findNode = (nodeId: string) =>
      nodes.find((candidate) => candidate.nodeId === nodeId);
    let totalDuration = 0;
    let hasDuration = false;
    chain.forEach((mwId) => {
      const mwNode = findNode(mwId);
      const duration =
        mwNode?.startedAt && mwNode.finishedAt
          ? Date.parse(mwNode.finishedAt) - Date.parse(mwNode.startedAt)
          : null;
      if (typeof duration === "number" && Number.isFinite(duration)) {
        totalDuration += duration;
        hasDuration = true;
      }
      chainNodes.push({
        nodeId: mwId,
        status: mwNode?.status,
        startedAt: mwNode?.startedAt,
        finishedAt: mwNode?.finishedAt,
        durationMs: Number.isFinite(duration as number) ? (duration as number) : null,
      });
    });
    const hostNode = findNode(hostId);
    const hostDuration =
      hostNode?.startedAt && hostNode.finishedAt
        ? Date.parse(hostNode.finishedAt) - Date.parse(hostNode.startedAt)
        : null;
    if (typeof hostDuration === "number" && Number.isFinite(hostDuration)) {
      totalDuration += hostDuration
      hasDuration = true
    }
    chainNodes.push({
      nodeId: hostId,
      status: hostNode?.status,
      startedAt: hostNode?.startedAt,
      finishedAt: hostNode?.finishedAt,
      durationMs: Number.isFinite(hostDuration as number) ? (hostDuration as number) : null,
    });
    traces.push({
      hostId,
      chain,
      nodes: chainNodes,
      totalDurationMs: hasDuration ? totalDuration : null,
    });
  });
  return traces;
};
