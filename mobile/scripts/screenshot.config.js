// ─── screenshot.config.js ────────────────────────────────────────────────────
// Config for screenshot.js (screenshot-ui skill)
// ─────────────────────────────────────────────────────────────────────────────

export default {
  // ── Targets ──────────────────────────────────────────────────────────────
  targets: {
    localhost: "http://localhost:8081",
  },

  // Which target(s) to run
  run: "localhost",

  // ── Output ───────────────────────────────────────────────────────────────
  outputDir: "screenshots",

  // ── Viewport ─────────────────────────────────────────────────────────────
  viewport: { width: 1440, height: 900 },

  // ── Timing ───────────────────────────────────────────────────────────────
  extraDelayMs: 2000,

  // No login needed for local dev
  loginDelaySeconds: 0,

  // ── Route discovery ───────────────────────────────────────────────────────
  // Use obscure selectors to force fallback to manual routes
  navSelectors: [
    '_x_nonexistent_selector_xyz_',
  ],

  // ── Manual routes (primary source since DOM nav link texts are unreliable) ─
  manualRoutes: [
    { path: "/",              name: "Home" },
    { path: "/history",       name: "History" },
    { path: "/login",         name: "Login" },
    { path: "/capture",       name: "Capture" },
    { path: "/options",       name: "Options" },
    { path: "/preview",       name: "Preview" },
    { path: "/result-view",   name: "Result-View" },
    { path: "/recharge",      name: "Recharge" },
    { path: "/membership",    name: "Membership" },
  ],
};
