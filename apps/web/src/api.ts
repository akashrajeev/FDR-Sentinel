import {
  InMemoryWebStorage,
  UserManager,
  WebStorageStateStore,
} from "oidc-client-ts";
import type { components } from "./contracts";
export type Schemas = components["schemas"];
export const identity = new UserManager({
  authority: "http://localhost:8081/realms/sentinel",
  client_id: "sentinel-web",
  redirect_uri: `${window.location.origin}/callback`,
  post_logout_redirect_uri: window.location.origin,
  response_type: "code",
  scope: "openid profile",
  automaticSilentRenew: false,
  userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
});
let token = "";
export function setToken(value: string) {
  token = value;
}
export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
  key?: string,
): Promise<T> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (body !== undefined) {
    headers["Idempotency-Key"] = key ?? crypto.randomUUID();
    if (!(body instanceof FormData))
      headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`/api/v1${path}`, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    headers,
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Service unavailable" }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.json() as Promise<T>;
}
export async function download(id: string) {
  const response = await fetch(`/api/v1/documents/${id}/content`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Document unavailable or quarantined");
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = `${id}.pdf`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
