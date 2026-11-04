import { useQuery } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { api, unwrap, type Schemas } from "@/api/client";
import { PageHeader } from "@/components/Layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { useAction } from "@/hooks/useAction";
import { formatDate, list, numberOrNull, text, textOrNull } from "@/lib/format";
import { DISCLOSURE_LABELS, SUBMISSION_KIND_LABELS, type Disclosure } from "@/lib/labels";

type Profile = Schemas["SkillProfileOutput"];
type Career = Schemas["CareerOutput"];
type Project = Schemas["ProjectOutput"];
type Skill = Schemas["SkillOutput"];
type Qualification = Schemas["QualificationOutput"];

function FormDialog({
  title,
  trigger,
  onSubmit,
  children,
}: {
  title: string;
  trigger: ReactNode;
  onSubmit: (form: FormData) => Promise<unknown>;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const action = useAction(onSubmit);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    action.mutate(new FormData(event.currentTarget), { onSuccess: () => setOpen(false) });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen} title={title} trigger={trigger}>
      <form onSubmit={submit} className="grid gap-3">
        {children}
        <Button type="submit" disabled={action.isPending}>
          保存
        </Button>
      </form>
    </Dialog>
  );
}

function Section<T extends { id: string }>({
  title,
  items,
  renderItem,
  form,
  onAdd,
  onUpdate,
  onRemove,
}: {
  title: string;
  items: T[];
  renderItem: (item: T) => ReactNode;
  form: (item?: T) => ReactNode;
  onAdd: (form: FormData) => Promise<unknown>;
  onUpdate: (item: T, form: FormData) => Promise<unknown>;
  onRemove: (item: T) => Promise<unknown>;
}) {
  const remove = useAction(onRemove);
  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardTitle>{title}</CardTitle>
        <FormDialog
          title={`${title}を追加`}
          onSubmit={onAdd}
          trigger={
            <Button size="sm" variant="outline">
              <Plus className="size-3.5" />
              追加
            </Button>
          }
        >
          {form()}
        </FormDialog>
      </div>
      {items.length === 0 && <p className="text-sm text-muted-foreground">未登録</p>}
      <ul className="divide-y">
        {items.map((item) => (
          <li key={item.id} className="flex items-start justify-between gap-2 py-2 text-sm">
            <div className="min-w-0">{renderItem(item)}</div>
            <div className="flex shrink-0">
              <FormDialog
                title={`${title}を編集`}
                onSubmit={(values) => onUpdate(item, values)}
                trigger={
                  <Button size="icon" variant="ghost" aria-label="編集">
                    <Pencil className="size-3.5" />
                  </Button>
                }
              >
                {form(item)}
              </FormDialog>
              <Button
                size="icon"
                variant="ghost"
                aria-label="削除"
                onClick={() => remove.mutate(item)}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function BasicCard({ profile }: { profile: Profile }) {
  const update = useAction((form: FormData) =>
    unwrap(
      api.PATCH("/api/skill-profile/basic", {
        body: {
          full_name: text(form, "full_name"),
          birth_date: textOrNull(form, "birth_date"),
          age: numberOrNull(form, "age"),
          nearest_station: text(form, "nearest_station"),
          desired_conditions: text(form, "desired_conditions"),
          self_pr: text(form, "self_pr"),
          strengths_summary: text(form, "strengths_summary"),
          expected_version: profile.version,
        },
      }),
    ),
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    update.mutate(new FormData(event.currentTarget));
  }

  const basic = profile.basic;
  return (
    <Card>
      <CardTitle>基本情報</CardTitle>
      <form key={profile.version} onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <Field label="氏名">
          <Input name="full_name" defaultValue={basic.full_name} />
        </Field>
        <Field label="最寄り">
          <Input name="nearest_station" defaultValue={basic.nearest_station} />
        </Field>
        <Field label="生年月日">
          <Input name="birth_date" type="date" defaultValue={basic.birth_date ?? ""} />
        </Field>
        <Field label="年齢">
          <Input name="age" type="number" min={0} defaultValue={basic.age ?? ""} />
        </Field>
        <Field label="希望条件" className="sm:col-span-2">
          <Textarea name="desired_conditions" defaultValue={basic.desired_conditions} />
        </Field>
        <Field label="自己 PR" className="sm:col-span-2">
          <Textarea name="self_pr" defaultValue={basic.self_pr} />
        </Field>
        <Field label="強みの要約" className="sm:col-span-2">
          <Textarea name="strengths_summary" defaultValue={basic.strengths_summary} />
        </Field>
        <Button type="submit" variant="outline" disabled={update.isPending}>
          保存
        </Button>
      </form>
    </Card>
  );
}

function CareerFields({ item }: { item?: Career }) {
  return (
    <>
      <Field label="会社名">
        <Input name="company_name" defaultValue={item?.company_name} required />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="開始（YYYY-MM）">
          <Input name="start" defaultValue={item?.start ?? ""} placeholder="2020-04" />
        </Field>
        <Field label="終了（YYYY-MM）">
          <Input name="end" defaultValue={item?.end ?? ""} placeholder="在籍中は空欄" />
        </Field>
      </div>
      <Field label="雇用形態">
        <Input name="employment_type" defaultValue={item?.employment_type} />
      </Field>
      <Field label="役割">
        <Input name="role" defaultValue={item?.role} />
      </Field>
      <Field label="概要">
        <Textarea name="summary" defaultValue={item?.summary} />
      </Field>
    </>
  );
}

function careerValues(form: FormData) {
  return {
    company_name: text(form, "company_name"),
    start: textOrNull(form, "start"),
    end: textOrNull(form, "end"),
    employment_type: text(form, "employment_type"),
    role: text(form, "role"),
    summary: text(form, "summary"),
  };
}

function ProjectFields({ item }: { item?: Project }) {
  return (
    <>
      <Field label="案件概要">
        <Textarea name="summary" defaultValue={item?.summary} required />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="開始（YYYY-MM）">
          <Input name="start" defaultValue={item?.start ?? ""} />
        </Field>
        <Field label="終了（YYYY-MM）">
          <Input name="end" defaultValue={item?.end ?? ""} placeholder="継続中は空欄" />
        </Field>
        <Field label="役割">
          <Input name="role" defaultValue={item?.role} />
        </Field>
        <Field label="規模（人数）">
          <Input name="team_size" type="number" min={0} defaultValue={item?.team_size ?? ""} />
        </Field>
      </div>
      <Field label="言語（カンマ区切り）">
        <Input name="languages" defaultValue={item?.languages.join(", ")} />
      </Field>
      <Field label="フレームワーク">
        <Input name="frameworks" defaultValue={item?.frameworks.join(", ")} />
      </Field>
      <Field label="データベース">
        <Input name="databases" defaultValue={item?.databases.join(", ")} />
      </Field>
      <Field label="インフラ">
        <Input name="infrastructure" defaultValue={item?.infrastructure.join(", ")} />
      </Field>
      <Field label="担当工程">
        <Input name="phases" defaultValue={item?.phases.join(", ")} />
      </Field>
      <Field label="成果">
        <Textarea name="achievements" defaultValue={item?.achievements} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="公開可否">
          <Select name="disclosure" defaultValue={item?.disclosure ?? "public"}>
            {Object.entries(DISCLOSURE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="匿名化後の表記">
          <Input name="anonymized_name" defaultValue={item?.anonymized_name ?? ""} />
        </Field>
      </div>
    </>
  );
}

function projectValues(form: FormData) {
  return {
    summary: text(form, "summary"),
    start: textOrNull(form, "start"),
    end: textOrNull(form, "end"),
    role: text(form, "role"),
    team_size: numberOrNull(form, "team_size"),
    languages: list(form, "languages"),
    frameworks: list(form, "frameworks"),
    databases: list(form, "databases"),
    infrastructure: list(form, "infrastructure"),
    phases: list(form, "phases"),
    achievements: text(form, "achievements"),
    disclosure: text(form, "disclosure") as Disclosure,
    anonymized_name: textOrNull(form, "anonymized_name"),
  };
}

function SkillFields({ item }: { item?: Skill }) {
  return (
    <>
      <Field label="技術名">
        <Input name="name" defaultValue={item?.name} required />
      </Field>
      <Field label="カテゴリ">
        <Input name="category" defaultValue={item?.category} />
      </Field>
      <Field label="経験年数">
        <Input name="years" type="number" min={0} step={0.5} defaultValue={item?.years ?? ""} />
      </Field>
      <Field label="習熟度">
        <Input name="proficiency" defaultValue={item?.proficiency} />
      </Field>
    </>
  );
}

function skillValues(form: FormData) {
  return {
    name: text(form, "name"),
    category: text(form, "category"),
    years: numberOrNull(form, "years"),
    proficiency: text(form, "proficiency"),
  };
}

function QualificationFields({ item }: { item?: Qualification }) {
  return (
    <>
      <Field label="資格名">
        <Input name="name" defaultValue={item?.name} required />
      </Field>
      <Field label="取得日（YYYY-MM）">
        <Input name="acquired_on" defaultValue={item?.acquired_on ?? ""} />
      </Field>
    </>
  );
}

function qualificationValues(form: FormData) {
  return { name: text(form, "name"), acquired_on: textOrNull(form, "acquired_on") };
}

function ImportDialog() {
  const [open, setOpen] = useState(false);
  const action = useAction(async (form: FormData) => {
    const payload = JSON.parse(text(form, "json"));
    await unwrap(
      api.POST("/api/skill-profile/import", {
        body: { ...payload, overwrite: form.get("overwrite") === "on" },
      }),
    );
    setOpen(false);
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    action.mutate(new FormData(event.currentTarget));
  }

  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title="一括インポート"
      trigger={<Button variant="outline">一括インポート</Button>}
    >
      <form onSubmit={submit} className="grid gap-3">
        <Field label="構造化 JSON（basic / careers / projects / skills / qualifications）">
          <Textarea name="json" className="min-h-64 font-mono" required />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="overwrite" />
          既存の内容を置き換える
        </label>
        <Button type="submit" disabled={action.isPending}>
          インポート
        </Button>
      </form>
    </Dialog>
  );
}

function Submissions() {
  const submissions = useQuery({
    queryKey: ["submissions"],
    queryFn: () => unwrap(api.GET("/api/submissions", { params: { query: { limit: 200 } } })),
  });
  return (
    <Card>
      <CardTitle>提出記録</CardTitle>
      {submissions.data?.items.length === 0 && (
        <p className="text-sm text-muted-foreground">
          提出記録はありません。応募詳細から記録できます。
        </p>
      )}
      <ul className="space-y-1">
        {submissions.data?.items.map((submission) => (
          <li key={submission.id} className="flex flex-wrap items-center gap-2 text-sm">
            <Link to={`/applications/${submission.application_id}`} className="hover:underline">
              {SUBMISSION_KIND_LABELS[submission.kind]}
            </Link>
            <span className="text-xs text-muted-foreground tabular-nums">
              {formatDate(submission.submitted_at)}
            </span>
            {submission.template_file_name && (
              <span className="text-xs">{submission.template_file_name}</span>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function SkillProfilePage() {
  const [technology, setTechnology] = useState("");
  const query = useQuery({
    queryKey: ["skill-profile", technology],
    queryFn: () =>
      unwrap(
        api.GET("/api/skill-profile", {
          params: { query: { technology: technology || undefined } },
        }),
      ),
  });
  const profile = query.data;
  if (!profile) {
    return <p className="text-sm text-muted-foreground">{query.error?.message ?? "読み込み中…"}</p>;
  }
  const expected_version = profile.version;

  return (
    <>
      <PageHeader title="スキルシート">
        <Input
          aria-label="技術名で絞り込み"
          className="w-48"
          placeholder="技術名で絞り込み"
          value={technology}
          onChange={(e) => setTechnology(e.target.value)}
        />
        <ImportDialog />
      </PageHeader>
      <div className="grid gap-4 lg:grid-cols-2">
        <BasicCard profile={profile} />
        <div className="grid content-start gap-4">
          <Section<Career>
            title="職歴"
            items={profile.careers}
            form={(item) => <CareerFields item={item} />}
            renderItem={(career) => (
              <>
                <div className="font-medium">{career.company_name}</div>
                <div className="text-xs text-muted-foreground">
                  {career.start ?? "?"} 〜 {career.end ?? "現在"} ・ {career.role}
                </div>
              </>
            )}
            onAdd={(form) =>
              unwrap(
                api.POST("/api/skill-profile/careers", {
                  body: { ...careerValues(form), expected_version },
                }),
              )
            }
            onUpdate={(item, form) =>
              unwrap(
                api.PATCH("/api/skill-profile/careers/{career_id}", {
                  params: { path: { career_id: item.id } },
                  body: { ...careerValues(form), expected_version },
                }),
              )
            }
            onRemove={(item) =>
              unwrap(
                api.DELETE("/api/skill-profile/careers/{career_id}", {
                  params: { path: { career_id: item.id }, query: { expected_version } },
                }),
              )
            }
          />
          <Section<Skill>
            title="スキル"
            items={profile.skills}
            form={(item) => <SkillFields item={item} />}
            renderItem={(skill) => (
              <>
                <span className="font-medium">{skill.name}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {skill.category} {skill.years != null && `${skill.years} 年`} {skill.proficiency}
                </span>
              </>
            )}
            onAdd={(form) =>
              unwrap(
                api.POST("/api/skill-profile/skills", {
                  body: { ...skillValues(form), expected_version },
                }),
              )
            }
            onUpdate={(item, form) =>
              unwrap(
                api.PATCH("/api/skill-profile/skills/{skill_id}", {
                  params: { path: { skill_id: item.id } },
                  body: { ...skillValues(form), expected_version },
                }),
              )
            }
            onRemove={(item) =>
              unwrap(
                api.DELETE("/api/skill-profile/skills/{skill_id}", {
                  params: { path: { skill_id: item.id }, query: { expected_version } },
                }),
              )
            }
          />
          <Section<Qualification>
            title="資格"
            items={profile.qualifications}
            form={(item) => <QualificationFields item={item} />}
            renderItem={(qualification) => (
              <>
                <span className="font-medium">{qualification.name}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {qualification.acquired_on}
                </span>
              </>
            )}
            onAdd={(form) =>
              unwrap(
                api.POST("/api/skill-profile/qualifications", {
                  body: { ...qualificationValues(form), expected_version },
                }),
              )
            }
            onUpdate={(item, form) =>
              unwrap(
                api.PATCH("/api/skill-profile/qualifications/{qualification_id}", {
                  params: { path: { qualification_id: item.id } },
                  body: { ...qualificationValues(form), expected_version },
                }),
              )
            }
            onRemove={(item) =>
              unwrap(
                api.DELETE("/api/skill-profile/qualifications/{qualification_id}", {
                  params: { path: { qualification_id: item.id }, query: { expected_version } },
                }),
              )
            }
          />
        </div>
        <div className="lg:col-span-2">
          <Section<Project>
            title="案件"
            items={profile.projects}
            form={(item) => <ProjectFields item={item} />}
            renderItem={(project) => (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{project.summary}</span>
                  <Badge>{DISCLOSURE_LABELS[project.disclosure]}</Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  {project.start ?? "?"} 〜 {project.end ?? "現在"} ・{" "}
                  {[...project.languages, ...project.frameworks].join(", ")}
                </div>
              </>
            )}
            onAdd={(form) =>
              unwrap(
                api.POST("/api/skill-profile/projects", {
                  body: { ...projectValues(form), expected_version },
                }),
              )
            }
            onUpdate={(item, form) =>
              unwrap(
                api.PATCH("/api/skill-profile/projects/{project_id}", {
                  params: { path: { project_id: item.id } },
                  body: { ...projectValues(form), expected_version },
                }),
              )
            }
            onRemove={(item) =>
              unwrap(
                api.DELETE("/api/skill-profile/projects/{project_id}", {
                  params: { path: { project_id: item.id }, query: { expected_version } },
                }),
              )
            }
          />
        </div>
        <div className="lg:col-span-2">
          <Submissions />
        </div>
      </div>
    </>
  );
}
