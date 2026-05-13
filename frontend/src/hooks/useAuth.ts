import { useMemo, useState } from "react";

export type AuthRole = "operator" | "ciso";

export function useAuth() {
  const [token, setTokenState] = useState<string | null>(
    () => localStorage.getItem("agentforge_token"),
  );
  const [role, setRoleState] = useState<AuthRole | null>(
    () => (localStorage.getItem("agentforge_role") as AuthRole | null) ?? null,
  );

  const setAuth = (nextToken: string, nextRole: AuthRole) => {
    localStorage.setItem("agentforge_token", nextToken);
    localStorage.setItem("agentforge_role", nextRole);
    setTokenState(nextToken);
    setRoleState(nextRole);
  };

  const clearAuth = () => {
    localStorage.removeItem("agentforge_token");
    localStorage.removeItem("agentforge_role");
    setTokenState(null);
    setRoleState(null);
  };

  const isAuthenticated = useMemo(() => Boolean(token), [token]);

  return {
    token,
    role,
    isAuthenticated,
    setAuth,
    clearAuth,
  };
}
