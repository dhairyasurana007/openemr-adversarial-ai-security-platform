import { useQuery } from "@tanstack/react-query";

import { fetchFindings } from "../api/service";

export function useFindings(filters: { severity?: string; status?: string }) {
  return useQuery({
    queryKey: ["findings", filters],
    queryFn: () => fetchFindings(filters),
  });
}
