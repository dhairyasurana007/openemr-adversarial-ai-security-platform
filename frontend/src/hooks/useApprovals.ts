import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  decideAttackApproval,
  decideReportApproval,
  fetchApprovalQueue,
} from "../api/service";

export function useApprovals() {
  const queryClient = useQueryClient();

  const queue = useQuery({ queryKey: ["approval-queue"], queryFn: fetchApprovalQueue });

  const attackDecision = useMutation({
    mutationFn: ({ attackId, decision }: { attackId: string; decision: string }) =>
      decideAttackApproval(attackId, decision),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["approval-queue"] });
    },
  });

  const reportDecision = useMutation({
    mutationFn: ({ reportId, decision }: { reportId: string; decision: string }) =>
      decideReportApproval(reportId, decision),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["findings"] });
    },
  });

  return { queue, attackDecision, reportDecision };
}
