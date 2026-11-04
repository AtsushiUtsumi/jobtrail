import { Badge } from "@/components/ui/badge";
import { statusLabel, type ApplicationStatus, type Outcome, type StageType } from "@/lib/labels";
import { cn } from "@/lib/utils";

const OFFER_OUTCOMES: Outcome[] = ["offer_accepted", "offer_declined"];

export function StatusBadge({
  item,
}: {
  item: { status: ApplicationStatus; stage_type?: StageType | null; outcome: Outcome };
}) {
  const positive = item.status === "offer_pending" || OFFER_OUTCOMES.includes(item.outcome);
  const active = item.status === "in_stage";
  return (
    <Badge
      className={cn(
        active && "border-primary/40 text-primary",
        positive && "border-emerald-500/50 text-emerald-600 dark:text-emerald-400",
        item.status === "closed" && !positive && "text-muted-foreground",
      )}
    >
      {statusLabel(item)}
    </Badge>
  );
}
