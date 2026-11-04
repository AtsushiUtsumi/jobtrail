import { Badge } from "@/components/ui/badge";
import { statusLabel, type ApplicationStatus, type Outcome, type StageResult } from "@/lib/labels";
import { cn } from "@/lib/utils";

const OFFER_OUTCOMES: Outcome[] = ["offer_accepted", "offer_declined"];

export function StatusBadge({
  item,
}: {
  item: {
    status: ApplicationStatus;
    outcome: Outcome;
    current_stage_result?: StageResult | null;
  };
}) {
  const positive = item.status === "offer" || OFFER_OUTCOMES.includes(item.outcome);
  const closed = item.outcome !== "in_progress";
  const active = !closed && item.status !== "considering";
  return (
    <Badge
      className={cn(
        active && "border-primary/40 text-primary",
        positive && "border-emerald-500/50 text-emerald-600 dark:text-emerald-400",
        closed && !positive && "text-muted-foreground",
      )}
    >
      {statusLabel(item)}
    </Badge>
  );
}
