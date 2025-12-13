import { AuditApi } from "../client/apis/audit-api";
import type { AuditEventList } from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";

const auditApi = createApi(AuditApi);

export const listAuditEvents = async (params?: {
  limit?: number;
  cursor?: string;
  action?: string;
  actorId?: string;
  targetType?: string;
}): Promise<AuditEventList> => {
  const response = await apiRequest(() =>
    auditApi.listAuditEvents(
      params?.limit,
      params?.cursor,
      params?.action,
      params?.actorId,
      params?.targetType,
    ),
  );
  return response.data;
};
