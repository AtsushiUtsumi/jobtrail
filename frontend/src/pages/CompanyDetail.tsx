import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, unwrap, type Schemas } from "@/api/client";
import { PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { TextViewer } from "@/components/TextViewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Field, Input, Textarea } from "@/components/ui/input";
import { useAction } from "@/hooks/useAction";
import { formatDate, numberOrNull, text, textOrNull } from "@/lib/format";
import { SOURCE_TYPE_LABELS } from "@/lib/labels";
import { NewApplicationDialog } from "@/pages/Applications";

type Company = Schemas["CompanyOutput"];

function CompanyForm({ company }: { company: Company }) {
  const update = useAction((form: FormData) =>
    unwrap(
      api.PATCH("/api/companies/{company_id}", {
        params: { path: { company_id: company.id } },
        body: {
          name: text(form, "name"),
          url: textOrNull(form, "url"),
          priority: numberOrNull(form, "priority"),
          memo: text(form, "memo"),
          expected_version: company.version,
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
      <CardTitle>基本情報</CardTitle>
      <form key={company.version} onSubmit={submit} className="grid gap-3">
        <fieldset disabled={!!company.deleted_at} className="grid gap-3">
          <Field label="社名">
            <Input name="name" defaultValue={company.name} required />
          </Field>
          <Field label="URL">
            <Input name="url" type="url" defaultValue={company.url ?? ""} />
          </Field>
          <Field label="志望度（1〜5）">
            <Input
              name="priority"
              type="number"
              min={1}
              max={5}
              defaultValue={company.priority ?? ""}
            />
          </Field>
          <Field label="メモ">
            <Textarea name="memo" defaultValue={company.memo} />
          </Field>
          <Button type="submit" variant="outline" disabled={update.isPending}>
            保存
          </Button>
        </fieldset>
      </form>
    </Card>
  );
}

function Sources({ company }: { company: Company }) {
  const [latestOnly, setLatestOnly] = useState(true);
  const sources = useQuery({
    queryKey: ["company-sources", company.id, latestOnly],
    queryFn: () =>
      unwrap(
        api.GET("/api/companies/{company_id}/sources", {
          params: {
            path: { company_id: company.id },
            query: { latest_only: latestOnly, limit: 200 },
          },
        }),
      ),
  });
  const summarize = useAction(({ id, summary }: { id: string; summary: string }) =>
    unwrap(
      api.PATCH("/api/company-sources/{source_id}", {
        params: { path: { source_id: id } },
        body: { summary },
      }),
    ),
  );

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>保存済みソース</CardTitle>
        <div className="flex items-center gap-3 text-xs">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={!latestOnly}
              onChange={(e) => setLatestOnly(!e.target.checked)}
            />
            過去の版も表示
          </label>
          <Link className="hover:underline" to={`/paste?company=${company.id}`}>
            貼り付けて保存
          </Link>
        </div>
      </div>
      {sources.data?.items.length === 0 && (
        <p className="text-sm text-muted-foreground">保存済みのページはありません。</p>
      )}
      <ul className="space-y-3">
        {sources.data?.items.map((source) => (
          <li key={source.id} className="text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge>{SOURCE_TYPE_LABELS[source.source_type]}</Badge>
              <a href={source.url} target="_blank" rel="noreferrer" className="truncate underline">
                {source.url}
              </a>
              <span className="text-xs text-muted-foreground tabular-nums">
                第 {source.revision} 版 ・ {formatDate(source.fetched_at)}
              </span>
              <TextViewer
                title={source.url}
                queryKey={["company-source", source.id]}
                load={async () =>
                  (
                    await unwrap(
                      api.GET("/api/company-sources/{source_id}", {
                        params: { path: { source_id: source.id } },
                      }),
                    )
                  ).raw_text
                }
              />
            </div>
            <Textarea
              key={source.summary}
              aria-label="要約"
              className="mt-1"
              placeholder="要約"
              defaultValue={source.summary}
              onBlur={(e) => {
                if (e.target.value !== source.summary) {
                  summarize.mutate({ id: source.id, summary: e.target.value });
                }
              }}
            />
          </li>
        ))}
      </ul>
    </Card>
  );
}

function RelatedApplications({ company }: { company: Company }) {
  const applications = useQuery({
    queryKey: ["applications", "company", company.id],
    queryFn: () =>
      unwrap(
        api.GET("/api/applications", {
          params: { query: { company_id: company.id, limit: 200 } },
        }),
      ),
  });
  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardTitle>関連する応募</CardTitle>
        {!company.deleted_at && <NewApplicationDialog companyId={company.id} />}
      </div>
      {applications.data?.items.length === 0 && (
        <p className="text-sm text-muted-foreground">応募はありません。</p>
      )}
      <ul className="space-y-2">
        {applications.data?.items.map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-2 text-sm">
            <Link to={`/applications/${item.id}`} className="hover:underline">
              {item.position}
            </Link>
            <StatusBadge item={item} />
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function CompanyDetailPage() {
  const { id = "" } = useParams();
  const detail = useQuery({
    queryKey: ["company", id],
    queryFn: () =>
      unwrap(api.GET("/api/companies/{company_id}", { params: { path: { company_id: id } } })),
  });
  const remove = useAction((company: Company) =>
    unwrap(
      api.DELETE("/api/companies/{company_id}", {
        params: {
          path: { company_id: company.id },
          query: { expected_version: company.version },
        },
      }),
    ),
  );
  const restore = useAction((company: Company) =>
    unwrap(
      api.POST("/api/companies/{company_id}/restore", {
        params: { path: { company_id: company.id } },
        body: { expected_version: company.version },
      }),
    ),
  );

  const company = detail.data;
  if (!company) {
    return (
      <p className="text-sm text-muted-foreground">{detail.error?.message ?? "読み込み中…"}</p>
    );
  }

  return (
    <>
      <PageHeader title={company.name}>
        {company.deleted_at ? (
          <>
            <Badge>削除済み</Badge>
            <Button variant="outline" onClick={() => restore.mutate(company)}>
              復元
            </Button>
          </>
        ) : (
          <Button variant="destructive" onClick={() => remove.mutate(company)}>
            削除
          </Button>
        )}
      </PageHeader>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="grid content-start gap-4">
          <CompanyForm company={company} />
          <RelatedApplications company={company} />
        </div>
        <Sources company={company} />
      </div>
    </>
  );
}
