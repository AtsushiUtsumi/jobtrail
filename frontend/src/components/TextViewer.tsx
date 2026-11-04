import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";

/** 本文は一覧に含めていないので、開いたときに取得する。 */
export function TextViewer({
  title,
  queryKey,
  load,
}: {
  title: string;
  queryKey: unknown[];
  load: () => Promise<string>;
}) {
  const [open, setOpen] = useState(false);
  const body = useQuery({ queryKey, queryFn: load, enabled: open, refetchInterval: false });
  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title={title}
      trigger={
        <Button size="sm" variant="ghost">
          本文
        </Button>
      }
    >
      <pre className="text-sm break-words whitespace-pre-wrap">{body.data ?? "読み込み中…"}</pre>
    </Dialog>
  );
}
