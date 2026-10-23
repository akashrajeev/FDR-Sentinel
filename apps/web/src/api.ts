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
const pending = new Map<string, string>();
export function setToken(value: string) {
  if (value !== token) pending.clear();
  token = value;
}
async function fingerprint(body: unknown) {
  let text: string;
  if (body instanceof FormData) {
    const fields = [];
    for (const [name, value] of body.entries()) {
      if (typeof value === "string") fields.push([name, value]);
      else {
        if (value.size > 10 * 1024 * 1024)
          throw new Error("PDF exceeds 10 MiB limit");
        const hash = await crypto.subtle.digest(
          "SHA-256",
          await value.arrayBuffer(),
        );
        fields.push([
          name,
          Array.from(new Uint8Array(hash), (x) =>
            x.toString(16).padStart(2, "0"),
          ).join(""),
        ]);
      }
    }
    text = JSON.stringify(fields.sort((a, b) => a[0].localeCompare(b[0])));
  } else text = JSON.stringify(body);
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(text),
  );
  return Array.from(new Uint8Array(hash), (x) =>
    x.toString(16).padStart(2, "0"),
  ).join("");
}
export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
  key?: string,
): Promise<T> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  const operation = `${method ?? (body === undefined ? "GET" : "POST")} ${path}`;
  const pendingKey =
    body === undefined ? "" : operation + ":" + (await fingerprint(body));
  if (body !== undefined) {
    headers["Idempotency-Key"] =
      key ?? pending.get(pendingKey) ?? crypto.randomUUID();
    pending.set(pendingKey, headers["Idempotency-Key"]);
    if (!(body instanceof FormData))
      headers["Content-Type"] = "application/json";
  }
  let response: Response | undefined;
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      response = await fetch(`/api/v1${path}`, {
        method: method ?? (body === undefined ? "GET" : "POST"),
        headers,
        body:
          body === undefined
            ? undefined
            : body instanceof FormData
              ? body
              : JSON.stringify(body),
      });
      if (![502, 503, 504].includes(response.status) || attempt === 3) break;
    } catch (error) {
      if (attempt === 3) throw error;
    }
    await new Promise((resolve) =>
      setTimeout(resolve, [500, 1500, 3500][attempt]),
    );
  }
  if (!response)
    throw new Error("Service unavailable; retry preserves this operation key.");
  if (response.status < 500) pending.delete(pendingKey);
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

export async function previewUrl(id: string, page: number) {
  const response = await fetch(`/api/v1/documents/${id}/preview/${page}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok)
    throw new Error(
      "Preview unavailable for this processed document; download the original.",
    );
  return URL.createObjectURL(await response.blob());
}

export async function exportCsv() {
  const response = await fetch("/api/v1/reports/deposits.csv", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Scoped export unavailable");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "synthetic-deposits.csv";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
