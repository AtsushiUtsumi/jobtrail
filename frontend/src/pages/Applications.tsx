import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, unwrap, type Schemas } from "@/api/client";
import {
  AdvanceStageDialog,
  applyNow,
  CloseApplicationDialog,
} from "@/components/ApplicationDialogs";
import { PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select } from "@/components/ui/input";
import { useAction } from "@/hooks/useAction";
import { formatDate, formatDateTime, text, textOrNull } from "@/lib/format";
import { outcomeOf, planDrop, stageTypeOf } from "@/lib/kanban";
import {
  CHANNEL_LABELS,
  STATUS_LABELS,
  type ApplicationChannel,
  type ApplicationStatus,
} from "@/lib/labels";
import { cn } from "@/lib/utils";

type Summary = Schemas["ApplicationSummary"];
type ApplicationSort = Schemas["ApplicationSort"];

function KanbanCard({ item }: { item: Summary }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: item.id,
    data: item,
  });
  const style = transform
    ? { transform: `translate(${transform.x}px, ${transform.y}px)` }
    : undefined;
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={cn(
        "cursor-grab rounded-md border bg-card p-2.5 text-sm shadow-xs",
        isDragging && "relative z-10 shadow-md",
      )}
    >
      <Link to={`/applications/${item.id}`} className="font-medium hover:underline">
        {item.company_name}
      </Link>
      <div className="text-xs text-muted-foreground">
        {item.position}
        <span className="tabular-nums"> ・ 志望度 {item.priority}</span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-1">
        <StatusBadge item={item} />
        {item.next_scheduled_at && (
          <span className="text-xs text-muted-foreground tabular-nums">
            {formatDateTime(item.next_scheduled_at)}
          </span>
        )}
      </div>
    </div>
  );
}

function KanbanColumn({ column }: { column: Schemas["PipelineColumn"] }) {
  const { setNodeRef, isOver } = useDroppable({ id: column.status });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex min-h-96 w-60 shrink-0 flex-col gap-2 rounded-lg bg-muted p-2",
        isOver && "outline-2 outline-ring",
      )}
    >
      <div className="flex items-center justify-between px-1 text-xs font-medium">
        {STATUS_LABELS[column.status]}
        <span className="text-muted-foreground tabular-nums">{column.count}</span>
      </div>
      {column.items.map((item) => (
        <KanbanCard key={item.id} item={item} />
      ))}
    </div>
  );
}

function Kanban({ sort }: { sort: ApplicationSort }) {
  const pipeline = useQuery({
    queryKey: ["pipeline", sort],
    queryFn: () =>
      unwrap(
        api.GET("/api/analytics/pipeline", { params: { query: { include_closed: true, sort } } }),
      ),
  });
  const [advancing, setAdvancing] = useState<{ item: Summary; target: ApplicationStatus }>();
  const [closing, setClosing] = useState<{ item: Summary; target: ApplicationStatus }>();
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));
  const apply = useAction((item: Summary) => applyNow(item));

  function onDragEnd(event: DragEndEvent) {
    const item = event.active.data.current as Summary | undefined;
    const target = event.over?.id as ApplicationStatus | undefined;
    if (!item || !target) return;
    const action = planDrop(item.status, target);
    if (action === "apply") apply.mutate(item);
    else if (action === "advance") setAdvancing({ item, target });
    else if (action === "close") setClosing({ item, target });
    else if (item.status !== target) {
      toast.info(
        item.outcome !== "in_progress"
          ? "終了した応募は詳細画面から再開してください。"
          : "この列へは移動できません。",
      );
    }
  }

  return (
    <>
      <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <div className="flex items-start gap-3 overflow-x-auto pb-3">
          {pipeline.data?.columns
            .filter((column) => column.status !== "closed")
            .map((column) => (
              <KanbanColumn key={column.status} column={column} />
            ))}
        </div>
      </DndContext>
      {advancing && (
        <AdvanceStageDialog
          application={advancing.item}
          defaultType={stageTypeOf(advancing.target)}
          passStageId={
            advancing.item.current_stage_result === "pending"
              ? (advancing.item.current_stage_id ?? undefined)
              : undefined
          }
          onClose={() => setAdvancing(undefined)}
        />
      )}
      {closing && (
        <CloseApplicationDialog
          application={closing.item}
          defaultOutcome={outcomeOf(closing.target)}
          onClose={() => setClosing(undefined)}
        />
      )}
    </>
  );
}

/** 欄を離れるか Enter で保存する。不正な値や保存の失敗は元の点数へ戻す。 */
function PriorityInput({ item }: { item: Summary }) {
  const update = useAction((priority: number) =>
    unwrap(
      api.PATCH("/api/applications/{application_id}", {
        params: { path: { application_id: item.id } },
        body: { priority, expected_version: item.version },
      }),
    ),
  );

  function save(input: HTMLInputElement) {
    const priority = input.valueAsNumber;
    if (priority === item.priority) return;
    const reset = () => {
      input.value = String(item.priority);
    };
    if (!Number.isInteger(priority) || priority < 0 || priority > 100) {
      reset();
      toast.error("志望度は 0〜100 の整数で入力してください。");
      return;
    }
    update.mutate(priority, { onError: reset });
  }

  return (
    <Input
      key={item.version}
      aria-label={`${item.company_name} ${item.position} の志望度`}
      className="h-8 w-20 tabular-nums"
      type="number"
      min={0}
      max={100}
      defaultValue={item.priority}
      disabled={update.isPending}
      onBlur={(e) => save(e.target)}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
      }}
    />
  );
}

function ApplicationList({ sort }: { sort: ApplicationSort }) {
  const [query, setQuery] = useState("");
  const [statuses, setStatuses] = useState<ApplicationStatus[]>([]);
  const [channel, setChannel] = useState<ApplicationChannel | "">("");
  const applications = useQuery({
    queryKey: ["applications", query, statuses, channel, sort],
    queryFn: () =>
      unwrap(
        api.GET("/api/applications", {
          params: {
            query: {
              query: query || undefined,
              statuses: statuses.length > 0 ? statuses : undefined,
              channel: channel || undefined,
              sort,
              limit: 200,
            },
          },
        }),
      ),
  });

  return (
    <>
      <div className="mb-3 flex flex-wrap gap-2">
        <Input
          className="w-56"
          placeholder="社名・職種で検索"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Select
          className="w-40"
          value={channel}
          onChange={(e) => setChannel(e.target.value as ApplicationChannel | "")}
        >
          <option value="">全経路</option>
          {Object.entries(CHANNEL_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>
      <fieldset className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <legend className="sr-only">ステータス</legend>
        {(Object.entries(STATUS_LABELS) as [ApplicationStatus, string][]).map(([value, label]) => (
          <label key={value} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={statuses.includes(value)}
              onChange={(e) =>
                setStatuses(
                  e.target.checked
                    ? [...statuses, value]
                    : statuses.filter((status) => status !== value),
                )
              }
            />
            {label}
          </label>
        ))}
        {statuses.length > 0 && (
          <Button size="sm" variant="ghost" onClick={() => setStatuses([])}>
            すべて解除
          </Button>
        )}
      </fieldset>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted-foreground">
            <tr>
              <th className="p-3 font-normal">企業</th>
              <th className="p-3 font-normal">職種</th>
              <th className="p-3 font-normal">志望度</th>
              <th className="p-3 font-normal">ステータス</th>
              <th className="p-3 font-normal">経路</th>
              <th className="p-3 font-normal">応募日</th>
            </tr>
          </thead>
          <tbody>
            {applications.data?.items.map((item) => (
              <tr key={item.id} className="border-t">
                <td className="p-3">
                  <Link to={`/applications/${item.id}`} className="font-medium hover:underline">
                    {item.company_name}
                  </Link>
                </td>
                <td className="p-3">{item.position}</td>
                <td className="p-3">
                  <PriorityInput item={item} />
                </td>
                <td className="p-3">
                  <StatusBadge item={item} />
                </td>
                <td className="p-3">{CHANNEL_LABELS[item.channel]}</td>
                <td className="p-3 tabular-nums">{formatDate(item.applied_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {applications.data?.items.length === 0 && (
          <p className="border-t p-3 text-sm text-muted-foreground">応募はまだありません。</p>
        )}
      </Card>
    </>
  );
}

export function NewApplicationDialog({ companyId }: { companyId?: string }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const companies = useQuery({
    queryKey: ["companies", "all-active"],
    queryFn: () => unwrap(api.GET("/api/companies", { params: { query: { limit: 200 } } })),
    enabled: open && !companyId,
  });
  const action = useAction(async (form: FormData) => {
    const selected = companyId ?? text(form, "company_id");
    const created = await unwrap(
      api.POST("/api/applications", {
        body: {
          company_id: selected || null,
          new_company: selected ? null : { name: text(form, "company_name") },
          position: text(form, "position"),
          channel: text(form, "channel") as ApplicationChannel,
          agent_name: textOrNull(form, "agent_name"),
          priority: Number(text(form, "priority")),
        },
      }),
    );
    setOpen(false);
    navigate(`/applications/${created.id}`);
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    action.mutate(new FormData(event.currentTarget));
  }

  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title="応募を追加"
      trigger={
        <Button>
          <Plus className="size-4" />
          応募を追加
        </Button>
      }
    >
      <form onSubmit={submit} className="grid gap-3">
        {!companyId && (
          <>
            <Field label="登録済みの企業">
              <Select name="company_id" defaultValue="">
                <option value="">（新しい企業を作成）</option>
                {companies.data?.items.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="新しい企業名">
              <Input name="company_name" />
            </Field>
          </>
        )}
        <Field label="職種">
          <Input name="position" required />
        </Field>
        <Field label="経路">
          <Select name="channel" defaultValue="direct">
            {Object.entries(CHANNEL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="エージェント名（任意）">
          <Input name="agent_name" />
        </Field>
        <Field label="志望度（0〜100）">
          <Input name="priority" type="number" min={0} max={100} defaultValue={50} required />
        </Field>
        <Button type="submit" disabled={action.isPending}>
          追加
        </Button>
      </form>
    </Dialog>
  );
}

export function ApplicationsPage() {
  const [view, setView] = useState<"kanban" | "list">("kanban");
  const [sort, setSort] = useState<ApplicationSort>("updated_desc");
  return (
    <>
      <PageHeader title="応募">
        <Select
          aria-label="並び順"
          className="w-40"
          value={sort}
          onChange={(e) => setSort(e.target.value as ApplicationSort)}
        >
          <option value="updated_desc">更新が新しい順</option>
          <option value="priority_desc">志望度が高い順</option>
          <option value="priority_asc">志望度が低い順</option>
        </Select>
        <div className="flex rounded-md border p-0.5">
          <Button
            size="sm"
            variant={view === "kanban" ? "default" : "ghost"}
            onClick={() => setView("kanban")}
          >
            カンバン
          </Button>
          <Button
            size="sm"
            variant={view === "list" ? "default" : "ghost"}
            onClick={() => setView("list")}
          >
            一覧
          </Button>
        </div>
        <NewApplicationDialog />
      </PageHeader>
      {view === "kanban" ? <Kanban sort={sort} /> : <ApplicationList sort={sort} />}
    </>
  );
}
