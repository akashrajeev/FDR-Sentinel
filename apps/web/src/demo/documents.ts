import { documentLines } from "./engine";

// Tiny ASCII-only PDF writer for synthetic, non-authoritative demo downloads.
// This is not the backend's document generation or signature implementation.
export async function demoDocument(id: string): Promise<Blob> {
  const escape = (s: string) =>
    s.replace(/[^\x20-\x7e]/g, "?").replace(/[\\()]/g, "\\$&");
  const lines = documentLines(id);
  const content = `BT /F1 12 Tf 45 785 Td 25 TL ${lines.map((line, index) => `${index ? "T* " : ""}(${escape(line)}) Tj`).join("\n")} ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((obj, i) => {
    offsets.push(pdf.length);
    pdf += `${i + 1} 0 obj\n${obj}\nendobj\n`;
  });
  const start = pdf.length;
  pdf += `xref\n0 6\n0000000000 65535 f \n${offsets
    .slice(1)
    .map((n) => `${String(n).padStart(10, "0")} 00000 n \n`)
    .join("")}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${start}\n%%EOF\n`;
  return new Blob([pdf], { type: "application/pdf" });
}
export function demoPreview(id: string, page: number) {
  if (page !== 1) throw new Error("Bundled examples have one page.");
  const escape = (s: string) =>
    s
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  const lines = documentLines(id);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="595" height="842" viewBox="0 0 595 842"><rect width="595" height="842" fill="white"/><rect x="30" y="30" width="535" height="65" rx="5" fill="#e8eefb"/>${lines.map((line, i) => `<text x="45" y="${58 + i * 25}" font-family="Arial,sans-serif" font-size="${i === 0 ? 19 : 11}" fill="#172740">${escape(line)}</text>`).join("")}<text x="45" y="760" font-family="Arial,sans-serif" font-size="13" fill="#a12828">DEMONSTRATION ONLY - NOT BANK VERIFIED</text></svg>`;
  return URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
}
