export const keys = {
  workflows: (filters?: object) => ["workflows", filters] as const,
  workflow: (id: string) => ["workflows", id] as const,
  trace: (id: string) => ["workflows", id, "trace"] as const,
  services: (filters?: object) => ["services", filters] as const,
  twin: (region?: string) => ["twin", region] as const,
  topology: (region?: string) => ["topology", region] as const,
  simStatus: () => ["simulation", "status"] as const,
  scenarios: () => ["simulation", "scenarios"] as const,
  logs: (cid?: string) => ["logs", cid] as const,
  policies: () => ["policies"] as const,
  models: () => ["models"] as const,
  settings: () => ["settings"] as const,
};
