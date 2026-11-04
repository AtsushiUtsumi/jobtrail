import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { api, unwrap } from "@/api/client";
import { PageHeader } from "@/components/Layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { useAction } from "@/hooks/useAction";
import { formatDate, text } from "@/lib/format";
import { DOCUMENT_KIND_LABELS, type DocumentKind } from "@/lib/labels";
import { cn } from "@/lib/utils";

function NewDocumentDialog() {
  const [open, setOpen] = useState(false);
  const action = useAction((form: FormData) =>
    unwrap(
      api.POST("/api/documents", {
        body: {
          name: text(form, "name"),
          kind: text(form, "kind") as DocumentKind,
          body: text(form, "body"),
        },
      }),
    ),
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    action.mutate(new FormData(event.currentTarget), { onSuccess: () => setOpen(false) });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title="書類を作成"
      trigger={
        <Button>
          <Plus className="size-4" />
          書類を作成
        </Button>
      }
    >
      <form onSubmit={submit} className="grid gap-3">
        <Field label="名前">
          <Input name="name" required />
        </Field>
        <Field label="種別">
          <Select name="kind" defaultValue="career_history">
            {Object.entries(DOCUMENT_KIND_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="本文（Markdown、任意）">
          <Textarea name="body" className="min-h-48" />
        </Field>
        <Button type="submit" disabled={action.isPending}>
          作成
        </Button>
      </form>
    </Dialog>
  );
}

function DocumentDetail({ id }: { id: string }) {
  const detail = useQuery({
    queryKey: ["document", id],
    queryFn: () =>
      unwrap(api.GET("/api/documents/{document_id}", { params: { path: { document_id: id } } })),
  });
  const addVersion = useAction((form: FormData) =>
    unwrap(
      api.POST("/api/documents/{document_id}/versions", {
        params: { path: { document_id: id } },
        body: { body: text(form, "body"), note: text(form, "note") },
      }),
    ),
  );
  const document = detail.data;
  if (!document) return null;
  const latest = document.versions.at(-1);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    addVersion.mutate(new FormData(event.currentTarget));
  }

  return (
    <div className="grid content-start gap-4">
      <Card>
        <CardTitle>新しい版を追加</CardTitle>
        <form key={latest?.id} onSubmit={submit} className="grid gap-3">
          <Field label="本文（Markdown）">
            <Textarea name="body" className="min-h-48" defaultValue={latest?.body} required />
          </Field>
          <Field label="変更メモ">
            <Input name="note" />
          </Field>
          <Button type="submit" disabled={addVersion.isPending}>
            版を追加
          </Button>
        </form>
      </Card>
      {[...document.versions].reverse().map((version) => (
        <Card key={version.id}>
          <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">第 {version.number} 版</span>
            <span className="text-xs text-muted-foreground">{formatDate(version.created_at)}</span>
            {version.submitted && <Badge>提出済み・編集不可</Badge>}
            {version.note && <span className="text-xs">{version.note}</span>}
          </div>
          <pre className="max-h-64 overflow-y-auto text-sm break-words whitespace-pre-wrap">
            {version.body}
          </pre>
        </Card>
      ))}
    </div>
  );
}

export function DocumentsPage() {
  const [selected, setSelected] = useState<string>();
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => unwrap(api.GET("/api/documents", { params: { query: { limit: 200 } } })),
  });

  return (
    <>
      <PageHeader title="書類">
        <NewDocumentDialog />
      </PageHeader>
      <div className="grid gap-4 lg:grid-cols-[16rem_1fr]">
        <Card className="content-start p-2">
          {documents.data?.items.length === 0 && (
            <p className="p-2 text-sm text-muted-foreground">書類はまだありません。</p>
          )}
          {documents.data?.items.map((document) => (
            <button
              key={document.id}
              onClick={() => setSelected(document.id)}
              className={cn(
                "block w-full cursor-pointer rounded-md p-2 text-left text-sm hover:bg-muted",
                selected === document.id && "bg-muted",
              )}
            >
              <div className="font-medium">{document.name}</div>
              <div className="text-xs text-muted-foreground">
                {DOCUMENT_KIND_LABELS[document.kind]} ・ 第 {document.latest_version_number} 版まで
              </div>
            </button>
          ))}
        </Card>
        {selected ? (
          <DocumentDetail key={selected} id={selected} />
        ) : (
          <p className="text-sm text-muted-foreground">左の一覧から書類を選択してください。</p>
        )}
      </div>
    </>
  );
}
