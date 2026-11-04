import { useState, type FormEvent } from "react";
import { api, unwrap } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { useAction } from "@/hooks/useAction";
import { fromLocalInput, text, textOrNull } from "@/lib/format";
import {
  closableOutcomes,
  OUTCOME_LABELS,
  STAGE_TYPE_LABELS,
  type ApplicationStatus,
  type Outcome,
  type StageType,
} from "@/lib/labels";

export interface ApplicationRef {
  id: string;
  version: number;
  status: ApplicationStatus;
}

interface DialogProps {
  application: ApplicationRef;
  onClose: () => void;
}

export function AdvanceStageDialog({ application, onClose }: DialogProps) {
  const action = useAction((form: FormData) =>
    unwrap(
      api.POST("/api/applications/{application_id}/stages", {
        params: { path: { application_id: application.id } },
        body: {
          type: text(form, "type") as StageType,
          label: textOrNull(form, "label"),
          scheduled_at: fromLocalInput(form.get("scheduled_at")),
          memo: text(form, "memo"),
          expected_version: application.version,
        },
      }),
    ),
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    action.mutate(new FormData(event.currentTarget), { onSuccess: onClose });
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()} title="ステージを追加">
      <form onSubmit={submit} className="grid gap-3">
        <Field label="種別">
          <Select name="type" defaultValue="interview">
            {Object.entries(STAGE_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="表示名（任意）">
          <Input name="label" placeholder="例: 一次面接" />
        </Field>
        <Field label="予定日時（任意）">
          <Input name="scheduled_at" type="datetime-local" />
        </Field>
        <Field label="メモ">
          <Textarea name="memo" />
        </Field>
        <Button type="submit" disabled={action.isPending}>
          追加
        </Button>
      </form>
    </Dialog>
  );
}

export function CloseApplicationDialog({ application, onClose }: DialogProps) {
  const outcomes = closableOutcomes(application.status);
  const [outcome, setOutcome] = useState<Outcome>(outcomes[0]);
  const action = useAction(() =>
    unwrap(
      api.POST("/api/applications/{application_id}/close", {
        params: { path: { application_id: application.id } },
        body: { outcome, expected_version: application.version },
      }),
    ),
  );

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()} title="応募を終了">
      <div className="grid gap-3">
        <Field label="終了理由">
          <Select value={outcome} onChange={(e) => setOutcome(e.target.value as Outcome)}>
            {outcomes.map((value) => (
              <option key={value} value={value}>
                {OUTCOME_LABELS[value]}
              </option>
            ))}
          </Select>
        </Field>
        <Button
          disabled={action.isPending}
          onClick={() => action.mutate(undefined, { onSuccess: onClose })}
        >
          終了する
        </Button>
      </div>
    </Dialog>
  );
}

export function applyNow(application: { id: string; version: number }, appliedAt?: string) {
  return unwrap(
    api.POST("/api/applications/{application_id}/apply", {
      params: { path: { application_id: application.id } },
      body: {
        applied_at: appliedAt ?? new Date().toISOString(),
        expected_version: application.version,
      },
    }),
  );
}
