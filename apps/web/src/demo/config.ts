declare const __DEMO_ONLY__: boolean;

// This selects a browser simulation, never an API authentication mode.
export const demoOnly = __DEMO_ONLY__;
export const isDemo =
  new URLSearchParams(window.location.search).get("demo") === "1";
export const enterDemo = () => window.location.assign("/?demo=1");
