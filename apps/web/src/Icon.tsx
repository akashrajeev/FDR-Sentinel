const paths: Record<string, string> = {
  overview: "M3 10 12 3l9 7M5 9v12h14V9M10 21v-7h4v7",
  deposits: "M6 3h9l4 4v14H6zM14 3v6h5M9 13h7m-7 4h7",
  institutions: "M3 8l9-5 9 5M4 9h16M5 11v8m5-8v8m4-8v8m5-8v8M3 21h18",
  releases: "M4 6h16v15H4zM8 3v6m8-6v6M7 13h10m-10 4h6",
  reports: "M4 21V11h4v10m4 0V4h4v17m4 0v-7h3v7",
  audit: "M12 8v5l3 2M4 6a9 9 0 1 1-1 10M3 3v5h5",
  import: "M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5",
  operator: "M4 6h16M4 12h16M4 18h16M8 3v6m8 0v6M9 15v6",
  arrow: "M4 12h16m-6-6 6 6-6 6",
  logout: "M9 4H4v16h5m5-14 6 6-6 6m-6-6h12",
  shield: "M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6zM8 12l3 3 5-6",
  search: "M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14m5-2 6 6",
  menu: "M4 6h16M4 12h16M4 18h16",
};

export function Icon({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  return (
    <svg
      className={`icon ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] ?? paths.deposits} />
    </svg>
  );
}

export function Brand({ caption = false }: { caption?: boolean }) {
  return (
    <div className="wordmark">
      <span className="logo">S</span>
      <div>FDR Sentinel{caption && <small>DEPOSIT OPERATIONS</small>}</div>
    </div>
  );
}
