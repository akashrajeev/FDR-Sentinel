export async function readPdf(form: FormData) {
  const file = form.get("file");
  if (
    !(file instanceof File) ||
    file.size === 0 ||
    file.size > 10 * 1024 * 1024
  )
    throw new Error("Choose a PDF between 1 byte and 10 MiB.");
  const bytes = await file.arrayBuffer();
  const text = new TextDecoder().decode(bytes);
  if (!text.startsWith("%PDF-"))
    throw new Error("PDF magic header required. No file was uploaded.");
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  const normalized = text.replace(/\\([()\\])/g, "$1");
  const sample =
    normalized.includes("FDR SENTINEL - SYNTHETIC DEMO") &&
    normalized.includes("NO FINANCIAL VALUE / NO OFFICIAL AUTHORITY");
  return {
    demo_upload: true,
    category: String(form.get("category") ?? "DEPOSIT_PROOF"),
    sha256: Array.from(new Uint8Array(hash), (n) =>
      n.toString(16).padStart(2, "0"),
    ).join(""),
    size: file.size,
    sample,
    sample_fields: sample
      ? {
          amount_paise: Number(
            normalized.match(/Amount \(integer INR paise\): (\d+)/)?.[1],
          ),
          issue_date:
            normalized.match(
              /Issue \/ deposit date: (\d{4}-\d{2}-\d{2})/,
            )?.[1] ?? null,
          maturity_date:
            normalized.match(/Maturity date: (\d{4}-\d{2}-\d{2})/)?.[1] ?? null,
        }
      : null,
  };
}

export async function readCsv(form: FormData) {
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0 || file.size > 200 * 1024)
    throw new Error("Choose a UTF-8 synthetic CSV up to 200 KiB.");
  const bytes = await file.arrayBuffer();
  const text = new TextDecoder("utf-8", { fatal: true })
    .decode(bytes)
    .replace(/^\uFEFF/, "");
  const rows: string[][] = [];
  let row: string[] = [],
    cell = "",
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') {
        cell += '"';
        i++;
      } else quoted = !quoted;
    } else if (ch === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      if (row.some((v) => v.length)) rows.push(row);
      row = [];
      cell = "";
    } else cell += ch;
  }
  if (quoted) throw new Error("Unclosed CSV quote.");
  row.push(cell);
  if (row.some((v) => v.length)) rows.push(row);
  const headers = rows.shift();
  const expected = [
    "obligation_id",
    "deposit_type",
    "bank_code",
    "reference",
    "amount_paise",
    "issue_date",
    "maturity_date",
    "deposited_on",
  ];
  if (
    !headers ||
    headers.join(",") !== expected.join(",") ||
    rows.length < 1 ||
    rows.length > 200 ||
    rows.some((row) => row.length !== headers.length)
  )
    throw new Error(
      "Use the eight-column template with 1–200 complete synthetic rows.",
    );
  const records = rows.map((row) =>
    Object.fromEntries(
      headers.map((h, i) => [
        h,
        h === "amount_paise" ? Number(row[i]) : row[i] || null,
      ]),
    ),
  );
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return {
    records,
    sha256: Array.from(new Uint8Array(digest), (n) =>
      n.toString(16).padStart(2, "0"),
    ).join(""),
  };
}
