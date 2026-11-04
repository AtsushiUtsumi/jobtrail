import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, unwrap } from "@/api/client";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { useAction } from "@/hooks/useAction";
import { text, textOrNull } from "@/lib/format";
import { SOURCE_TYPE_LABELS, type SourceType } from "@/lib/labels";

const RESULT_MESSAGES = {
  created: "保存しました。",
  new_revision: "内容が変わっていたため、新しい版として保存しました。",
  unchanged: "内容に変更はありませんでした。",
};

function CompanySourceForm({ initialCompany }: { initialCompany: string }) {
  const companies = useQuery({
    queryKey: ["companies", "paste"],
    queryFn: () => unwrap(api.GET("/api/companies", { params: { query: { limit: 200 } } })),
  });
  const save = useAction(async (form: FormData) => {
    const saved = await unwrap(
      api.POST("/api/companies/{company_id}/sources", {
        params: { path: { company_id: text(form, "company_id") } },
        body: {
          source_type: text(form, "source_type") as SourceType,
          url: text(form, "url"),
          raw_text: text(form, "raw_text"),
          summary: text(form, "summary"),
          acquired_by: "user_paste",
        },
      }),
    );
    toast.success(RESULT_MESSAGES[saved.result]);
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = event.currentTarget;
    save.mutate(new FormData(target), { onSuccess: () => target.reset() });
  }

  return (
    <form onSubmit={submit} className="grid gap-3">
      <Field label="企業">
        <Select
          key={companies.data ? "ready" : "loading"}
          name="company_id"
          defaultValue={initialCompany}
          required
        >
          <option value="">選択してください</option>
          {companies.data?.items.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="種別">
        <Select name="source_type" defaultValue="recruit">
          {Object.entries(SOURCE_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="URL">
        <Input name="url" type="url" required />
      </Field>
      <Field label="本文">
        <Textarea name="raw_text" className="min-h-64" required />
      </Field>
      <Field label="要約（任意）">
        <Textarea name="summary" />
      </Field>
      <Button type="submit" disabled={save.isPending}>
        保存
      </Button>
    </form>
  );
}

function JobPostingForm({ initialApplication }: { initialApplication: string }) {
  const applications = useQuery({
    queryKey: ["applications", "paste"],
    queryFn: () => unwrap(api.GET("/api/applications", { params: { query: { limit: 200 } } })),
  });
  const save = useAction(async (form: FormData) => {
    const saved = await unwrap(
      api.POST("/api/applications/{application_id}/postings", {
        params: { path: { application_id: text(form, "application_id") } },
        body: {
          url: textOrNull(form, "url"),
          raw_text: text(form, "raw_text"),
          summary: text(form, "summary"),
          acquired_by: "user_paste",
        },
      }),
    );
    toast.success(RESULT_MESSAGES[saved.result]);
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = event.currentTarget;
    save.mutate(new FormData(target), { onSuccess: () => target.reset() });
  }

  return (
    <form onSubmit={submit} className="grid gap-3">
      <Field label="応募">
        <Select
          key={applications.data ? "ready" : "loading"}
          name="application_id"
          defaultValue={initialApplication}
          required
        >
          <option value="">選択してください</option>
          {applications.data?.items.map((application) => (
            <option key={application.id} value={application.id}>
              {application.company_name} / {application.position}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="URL（任意）">
        <Input name="url" type="url" />
      </Field>
      <Field label="本文">
        <Textarea name="raw_text" className="min-h-64" required />
      </Field>
      <Field label="要約（任意）">
        <Textarea name="summary" />
      </Field>
      <Button type="submit" disabled={save.isPending}>
        保存
      </Button>
    </form>
  );
}

export function PastePage() {
  const [params] = useSearchParams();
  const initialApplication = params.get("application") ?? "";
  const [target, setTarget] = useState<"company" | "posting">(
    initialApplication ? "posting" : "company",
  );

  return (
    <>
      <PageHeader title="貼り付け入力">
        <div className="flex rounded-md border p-0.5">
          <Button
            size="sm"
            variant={target === "company" ? "default" : "ghost"}
            onClick={() => setTarget("company")}
          >
            企業情報
          </Button>
          <Button
            size="sm"
            variant={target === "posting" ? "default" : "ghost"}
            onClick={() => setTarget("posting")}
          >
            求人票
          </Button>
        </div>
      </PageHeader>
      <Card className="max-w-3xl">
        {target === "company" ? (
          <CompanySourceForm initialCompany={params.get("company") ?? ""} />
        ) : (
          <JobPostingForm initialApplication={initialApplication} />
        )}
      </Card>
    </>
  );
}
