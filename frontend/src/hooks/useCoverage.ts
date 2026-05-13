import { useQuery } from "@tanstack/react-query";

import { fetchCoverage, fetchCost, fetchTrends, fetchUncertain } from "../api/service";

export function useCoverage() {
  const coverage = useQuery({ queryKey: ["coverage"], queryFn: fetchCoverage });
  const trends = useQuery({ queryKey: ["trends"], queryFn: fetchTrends });
  const cost = useQuery({ queryKey: ["cost"], queryFn: fetchCost });
  const uncertain = useQuery({ queryKey: ["uncertain"], queryFn: fetchUncertain });

  return { coverage, trends, cost, uncertain };
}
