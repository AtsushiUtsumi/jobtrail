import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, unwrap, type Schemas } from "@/api/client";
import { PageHeader } from "@/components/Layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { useAction } from "@/hooks/useAction";
import { text, textOrNull } from "@/lib/format";

type CompanyState = Schemas["CompanyState"];

function NewCompanyDialog() {
  const [open, setOpen] = useState(false);
  const action = useAction((form: FormData) =>
    unwrap(
      api.POST("/api/companies", {
        body: {
          name: text(form, "name"),
          url: textOrNull(form, "url"),
          memo: text(form, "memo"),
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
      title="企業を登録"
      trigger={
        <Button>
          <Plus className="size-4" />
          企業を登録
        </Button>
      }
    >
      <form onSubmit={submit} className="grid gap-3">
        <Field label="社名">
          <Input name="name" required />
        </Field>
        <Field label="URL">
          <Input name="url" type="url" />
        </Field>
        <Field label="メモ">
          <Textarea name="memo" />
        </Field>
        <Button type="submit" disabled={action.isPending}>
          登録
        </Button>
      </form>
    </Dialog>
  );
}

export function CompaniesPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<CompanyState>("active");
  const companies = useQuery({
    queryKey: ["companies", query, state],
    queryFn: () =>
      unwrap(
        api.GET("/api/companies", {
          params: { query: { query: query || undefined, state, limit: 200 } },
        }),
      ),
  });

  return (
    <>
      <PageHeader title="企業">
        <NewCompanyDialog />
      </PageHeader>
      <div className="mb-3 flex flex-wrap gap-2">
        <Input
          className="w-56"
          placeholder="社名で検索"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Select
          aria-label="状態"
          className="w-36"
          value={state}
          onChange={(e) => setState(e.target.value as CompanyState)}
        >
          <option value="active">登録中</option>
          <option value="deleted">削除済み</option>
          <option value="all">すべて</option>
        </Select>
      </div>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted-foreground">
            <tr>
              <th className="p-3 font-normal">社名</th>
              <th className="p-3 font-normal">URL</th>
            </tr>
          </thead>
          <tbody>
            {companies.data?.items.map((company) => (
              <tr key={company.id} className="border-t">
                <td className="p-3">
                  <Link to={`/companies/${company.id}`} className="font-medium hover:underline">
                    {company.name}
                  </Link>
                  {company.deleted_at && <Badge className="ml-2">削除済み</Badge>}
                </td>
                <td className="max-w-80 truncate p-3 text-muted-foreground">
                  {company.url ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {companies.data?.items.length === 0 && (
          <p className="border-t p-3 text-sm text-muted-foreground">企業はありません。</p>
        )}
      </Card>
    </>
  );
}
