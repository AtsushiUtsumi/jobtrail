import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, unwrap, type Schemas } from "@/api/client";
import {
  AdvanceStageDialog,
  applyNow,
  CloseApplicationDialog,
} from "@/components/ApplicationDialogs";
import { PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { TextViewer } from "@/components/TextViewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { useAction } from "@/hooks/useAction";
import {
  formatDate,
  formatDateTime,
  fromLocalInput,
  text,
  textOrNull,
  toLocalInput,
} from "@/lib/format";
import {
  CHANNEL_LABELS,
  STAGE_RESULT_LABELS,
  STAGE_TYPE_LABELS,
  SUBMISSION_KIND_LABELS,
  type ApplicationChannel,
  type StageResult,
  type SubmissionKind,
} from "@/lib/labels";

type Application = Schemas["ApplicationDetail"];
type Stage = Schemas["StageOutput"];

function StageItem({
  application,
  stage,
  latest,
}: {
  application: Application;
  stage: Stage;
  latest: boolean;
}) {
  const closed = application.outcome !== "in_progress";
  const path = { application_id: application.id, stage_id: stage.id };
  const expected_version = application.version;
  const record = useAction((result: StageResult) =>
    unwrap(
      api.POST("/api/applications/{application_id}/stages/{stage_id}/result", {
        params: { path },
        body: { result, expected_version },
      }),
    ),
  );
  const reschedule = useAction((scheduled_at: string | null) =>
    unwrap(
      api.POST("/api/applications/{application_id}/stages/{stage_id}/schedule", {
        params: { path },
        body: { scheduled_at, expected_version },
      }),
    ),
  );
  const saveMemo = useAction((memo: string) =>
    unwrap(
      api.POST("/api/applications/{application_id}/stages/{stage_id}/memo", {
        params: { path },
        body: { memo, expected_version },
      }),
    ),
  );

  return (
    <li className="border-l-2 py-1 pl-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{stage.label || STAGE_TYPE_LABELS[stage.type]}</span>
        <Badge>{STAGE_RESULT_LABELS[stage.result]}</Badge>
        <span className="text-xs text-muted-foreground tabular-nums">
          {formatDateTime(stage.scheduled_at)}
        </span>
      </div>
      {closed ? (
        stage.memo && <p className="mt-1 text-sm whitespace-pre-wrap">{stage.memo}</p>
      ) : (
        <div key={application.version} className="mt-2 grid gap-2">
          <Textarea
            aria-label="メモ"
            placeholder="メモ（面接で聞かれたことなど）"
            defaultValue={stage.memo}
            onBlur={(e) => {
              if (e.target.value !== stage.memo) saveMemo.mutate(e.target.value);
            }}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Input
              aria-label="予定日時"
              className="w-52"
              type="datetime-local"
              defaultValue={toLocalInput(stage.scheduled_at)}
              onBlur={(e) => {
                if (e.target.value !== toLocalInput(stage.scheduled_at)) {
                  reschedule.mutate(fromLocalInput(e.target.value));
                }
              }}
            />
            {latest &&
              (["passed", "rejected", "declined"] as const).map((result) => (
                <Button
                  key={result}
                  size="sm"
                  variant={result === "passed" ? "default" : "outline"}
                  disabled={record.isPending || stage.result === result}
                  onClick={() => record.mutate(result)}
                >
                  {STAGE_RESULT_LABELS[result]}
                </Button>
              ))}
          </div>
        </div>
      )}
    </li>
  );
}

function DetailsForm({ application }: { application: Application }) {
  const update = useAction((form: FormData) =>
    unwrap(
      api.PATCH("/api/applications/{application_id}", {
        params: { path: { application_id: application.id } },
        body: {
          position: text(form, "position"),
          channel: text(form, "channel") as ApplicationChannel,
          agent_name: textOrNull(form, "agent_name"),
          memo: text(form, "memo"),
          expected_version: application.version,
        },
      }),
    ),
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    update.mutate(new FormData(event.currentTarget));
  }

  return (
    <Card>
      <CardTitle>応募情報</CardTitle>
      <form key={application.version} onSubmit={submit} className="grid gap-3">
        <Field label="職種">
          <Input name="position" defaultValue={application.position} required />
        </Field>
        <Field label="経路">
          <Select name="channel" defaultValue={application.channel}>
            {Object.entries(CHANNEL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="エージェント名">
          <Input name="agent_name" defaultValue={application.agent_name ?? ""} />
        </Field>
        <Field label="メモ">
          <Textarea name="memo" defaultValue={application.memo} />
        </Field>
        <Button type="submit" variant="outline" disabled={update.isPending}>
          保存
        </Button>
      </form>
    </Card>
  );
}

function JobPostings({ application }: { application: Application }) {
  const summarize = useAction(({ id, summary }: { id: string; summary: string }) =>
    unwrap(
      api.PATCH("/api/job-postings/{posting_id}", {
        params: { path: { posting_id: id } },
        body: { summary },
      }),
    ),
  );

  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardTitle>求人票</CardTitle>
        <Link className="text-xs hover:underline" to={`/paste?application=${application.id}`}>
          貼り付けて保存
        </Link>
      </div>
      {application.job_postings.length === 0 && (
        <p className="text-sm text-muted-foreground">求人票はまだありません。</p>
      )}
      <ul className="space-y-3">
        {application.job_postings.map((posting) => (
          <li key={posting.id} className="text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">第 {posting.revision} 版</span>
              <span className="text-xs text-muted-foreground">
                {formatDate(posting.fetched_at)}
              </span>
              {posting.url && (
                <a
                  href={posting.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs underline"
                >
                  元のページ
                </a>
              )}
              <TextViewer
                title={`求人票 第 ${posting.revision} 版`}
                queryKey={["posting", posting.id]}
                load={async () =>
                  (
                    await unwrap(
                      api.GET("/api/job-postings/{posting_id}", {
                        params: { path: { posting_id: posting.id } },
                      }),
                    )
                  ).raw_text
                }
              />
            </div>
            <Textarea
              key={posting.summary}
              aria-label="要約"
              className="mt-1"
              placeholder="要約"
              defaultValue={posting.summary}
              onBlur={(e) => {
                if (e.target.value !== posting.summary) {
                  summarize.mutate({ id: posting.id, summary: e.target.value });
                }
              }}
            />
          </li>
        ))}
      </ul>
    </Card>
  );
}

function SubmittedDocument({ application }: { application: Application }) {
  const [documentId, setDocumentId] = useState("");
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => unwrap(api.GET("/api/documents", { params: { query: { limit: 200 } } })),
  });
  const detail = useQuery({
    queryKey: ["document", documentId],
    queryFn: () =>
      unwrap(
        api.GET("/api/documents/{document_id}", {
          params: { path: { document_id: documentId } },
        }),
      ),
    enabled: !!documentId,
  });
  const attach = useAction((document_version_id: string) =>
    unwrap(
      api.POST("/api/applications/{application_id}/document", {
        params: { path: { application_id: application.id } },
        body: { document_version_id, expected_version: application.version },
      }),
    ),
  );

  return (
    <Card>
      <CardTitle>提出書類</CardTitle>
      <p className="mb-2 text-sm">
        {application.submitted_document_version_id ? "紐づけ済み" : "未紐づけ"}
      </p>
      {application.outcome === "in_progress" && (
        <div className="grid gap-2">
          <Select
            aria-label="書類"
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
          >
            <option value="">書類を選択</option>
            {documents.data?.items.map((document) => (
              <option key={document.id} value={document.id}>
                {document.name}
              </option>
            ))}
          </Select>
          <div className="flex flex-wrap gap-2">
            {detail.data?.versions.map((version) => (
              <Button
                key={version.id}
                size="sm"
                variant="outline"
                disabled={version.id === application.submitted_document_version_id}
                onClick={() => attach.mutate(version.id)}
              >
                第 {version.number} 版を紐づけ
              </Button>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function SubmissionRecords({ application }: { application: Application }) {
  const [open, setOpen] = useState(false);
  const record = useAction((form: FormData) =>
    unwrap(
      api.POST("/api/submissions", {
        body: {
          application_id: application.id,
          submitted_at: fromLocalInput(form.get("submitted_at")) ?? new Date().toISOString(),
          kind: text(form, "kind") as SubmissionKind,
          template_file_name: textOrNull(form, "template_file_name"),
          received_at: fromLocalInput(form.get("received_at")),
          memo: text(form, "memo"),
        },
      }),
    ),
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    record.mutate(new FormData(event.currentTarget), { onSuccess: () => setOpen(false) });
  }

  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardTitle>提出記録</CardTitle>
        <Dialog
          open={open}
          onOpenChange={setOpen}
          title="提出を記録"
          trigger={
            <Button size="sm" variant="outline">
              記録
            </Button>
          }
        >
          <form onSubmit={submit} className="grid gap-3">
            <p className="text-sm text-muted-foreground">
              現在のスキルシートの内容が提出時点のスナップショットとして保存されます。
            </p>
            <Field label="種別">
              <Select name="kind" defaultValue="skill_sheet">
                {Object.entries(SUBMISSION_KIND_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="提出日時">
              <Input name="submitted_at" type="datetime-local" required />
            </Field>
            <Field label="様式のファイル名（任意）">
              <Input name="template_file_name" />
            </Field>
            <Field label="様式の受領日時（任意）">
              <Input name="received_at" type="datetime-local" />
            </Field>
            <Field label="メモ">
              <Textarea name="memo" />
            </Field>
            <Button type="submit" disabled={record.isPending}>
              記録
            </Button>
          </form>
        </Dialog>
      </div>
      {application.submissions.length === 0 && (
        <p className="text-sm text-muted-foreground">提出記録はまだありません。</p>
      )}
      <ul className="space-y-1">
        {application.submissions.map((submission) => (
          <li key={submission.id} className="flex flex-wrap items-center gap-2 text-sm">
            <span>{SUBMISSION_KIND_LABELS[submission.kind]}</span>
            <span className="text-xs text-muted-foreground tabular-nums">
              {formatDate(submission.submitted_at)}
            </span>
            {submission.template_file_name && (
              <span className="text-xs">{submission.template_file_name}</span>
            )}
            <TextViewer
              title="提出時点の内容"
              queryKey={["submission", submission.id]}
              load={async () =>
                JSON.stringify(
                  (
                    await unwrap(
                      api.GET("/api/submissions/{submission_id}", {
                        params: { path: { submission_id: submission.id } },
                      }),
                    )
                  ).snapshot,
                  null,
                  2,
                )
              }
            />
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function ApplicationDetailPage() {
  const { id = "" } = useParams();
  const [dialog, setDialog] = useState<"advance" | "close">();
  const detail = useQuery({
    queryKey: ["application", id],
    queryFn: () =>
      unwrap(
        api.GET("/api/applications/{application_id}", {
          params: { path: { application_id: id } },
        }),
      ),
  });
  const apply = useAction((application: Application) => applyNow(application));
  const reopen = useAction((application: Application) =>
    unwrap(
      api.POST("/api/applications/{application_id}/reopen", {
        params: { path: { application_id: application.id } },
        body: { expected_version: application.version },
      }),
    ),
  );

  const application = detail.data;
  if (!application) {
    return (
      <p className="text-sm text-muted-foreground">{detail.error?.message ?? "読み込み中…"}</p>
    );
  }
  const closed = application.outcome !== "in_progress";

  return (
    <>
      <PageHeader title={`${application.company_name} / ${application.position}`}>
        <StatusBadge item={application} />
        {application.status === "considering" && (
          <Button disabled={apply.isPending} onClick={() => apply.mutate(application)}>
            応募した
          </Button>
        )}
        {!closed && application.status !== "considering" && (
          <Button onClick={() => setDialog("advance")}>ステージを追加</Button>
        )}
        {!closed && (
          <Button variant="outline" onClick={() => setDialog("close")}>
            終了
          </Button>
        )}
        {closed && (
          <Button
            variant="outline"
            disabled={reopen.isPending}
            onClick={() => reopen.mutate(application)}
          >
            再開
          </Button>
        )}
      </PageHeader>
      <p className="mb-4 text-sm text-muted-foreground">
        <Link to={`/companies/${application.company_id}`} className="hover:underline">
          企業ページ
        </Link>
        {" ・ "}応募日 {formatDate(application.applied_at)}
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="grid content-start gap-4">
          <Card>
            <CardTitle>選考ステージ</CardTitle>
            {application.stages.length === 0 && (
              <p className="text-sm text-muted-foreground">ステージはまだありません。</p>
            )}
            <ol className="space-y-3">
              {application.stages.map((stage, index) => (
                <StageItem
                  key={stage.id}
                  application={application}
                  stage={stage}
                  latest={index === application.stages.length - 1}
                />
              ))}
            </ol>
          </Card>
          <JobPostings application={application} />
        </div>
        <div className="grid content-start gap-4">
          <DetailsForm application={application} />
          <SubmittedDocument application={application} />
          <SubmissionRecords application={application} />
        </div>
      </div>

      {dialog === "advance" && (
        <AdvanceStageDialog application={application} onClose={() => setDialog(undefined)} />
      )}
      {dialog === "close" && (
        <CloseApplicationDialog application={application} onClose={() => setDialog(undefined)} />
      )}
    </>
  );
}
