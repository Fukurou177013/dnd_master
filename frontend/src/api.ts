import type {
  Campaign,
  CampaignExchange,
  CampaignMessage,
  CampaignSummary,
  Character,
  CharacterCreatePayload,
  CharacterOptions,
  MessageRequest,
  User,
} from "./types";

const API_ROOT = "/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function formatError(payload: unknown): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return "Ошибка валидации";
        })
        .join("; ");
    }
  }
  return "Не удалось выполнить запрос";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const isJson = response.headers
      .get("content-type")
      ?.includes("application/json");
    const payload = isJson ? await response.json() : null;
    throw new ApiError(formatError(payload), response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }

  const isJson = response.headers
    .get("content-type")
    ?.includes("application/json");
  const payload = isJson ? await response.json() : null;
  return payload as T;
}

function postJson(body: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body) };
}

export const api = {
  register: (body: {
    email: string;
    password: string;
    display_name: string;
  }) => request<User>("/auth/register", postJson(body)),

  login: (body: { email: string; password: string }) =>
    request<User>("/auth/login", postJson(body)),

  logout: () => request<void>("/auth/logout", { method: "POST" }),

  me: () => request<User>("/auth/me"),

  characterOptions: () => request<CharacterOptions>("/rules/character-options"),

  characters: () => request<Character[]>("/characters"),

  createCharacter: (body: CharacterCreatePayload) =>
    request<Character>("/characters", postJson(body)),

  deleteCharacter: (id: string) =>
    request<void>(`/characters/${id}`, { method: "DELETE" }),

  campaigns: () => request<Campaign[]>("/campaigns"),

  campaign: (id: string) => request<Campaign>(`/campaigns/${id}`),

  createCampaign: (body: {
    name: string;
    character_id: string;
    premise: string | null;
  }) => request<Campaign>("/campaigns", postJson(body)),

  deleteCampaign: (id: string) =>
    request<void>(`/campaigns/${id}`, { method: "DELETE" }),

  messages: (campaignId: string) =>
    request<CampaignMessage[]>(`/campaigns/${campaignId}/messages`),

  sendMessage: (campaignId: string, body: MessageRequest) =>
    request<CampaignExchange>(
      `/campaigns/${campaignId}/messages`,
      postJson(body),
    ),
};

export type { CampaignSummary };
