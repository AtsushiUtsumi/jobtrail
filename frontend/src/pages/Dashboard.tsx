import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, unwrap } from "@/api/client";
import { PageHeader } from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardTitle } from "@/components/ui/card";
import { formatDate, formatDateTime } from "@/lib/format";
import { CHANNEL_LABELS, STAGE_TYPE_LABELS, STATUS_LABELS } from "@/lib/labels";

function percent(rate?: number | null) {
  return rate === null || rate === undefined ? "—" : `${Math.round(rate * 100)}%`;
}

function Empty() {
  return <p className="text-sm text-muted-foreground">該当なし</p>;
}

export function DashboardPage() {
  const pipeline = useQuery({
    queryKey: ["pipeline"],
    queryFn: () =>
      unwrap(api.GET("/api/analytics/pipeline", { params: { query: { include_closed: true } } })),
  });
  const actions = useQuery({
    queryKey: ["next-actions"],
    queryFn: () => unwrap(api.GET("/api/analytics/next-actions")),
  });
  const stats = useQuery({
    queryKey: ["stats"],
    queryFn: () => unwrap(api.GET("/api/analytics/stats")),
  });

  return (
    <>
      <PageHeader title="ダッシュボード" />
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {pipeline.data?.columns.map((column) => (
          <Link key={column.status} to="/applications">
            <Card className="p-3 hover:bg-muted">
              <div className="text-xs text-muted-foreground">{STATUS_LABELS[column.status]}</div>
              <div className="text-2xl font-semibold tabular-nums">{column.count}</div>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle>近日の予定</CardTitle>
          {actions.data?.upcoming_stages.length === 0 && <Empty />}
          <ul className="space-y-2">
            {actions.data?.upcoming_stages.map(({ application, scheduled_at }) => (
              <li key={application.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/applications/${application.id}`} className="hover:underline">
                  {application.company_name} / {application.position}
                </Link>
                <span className="text-muted-foreground tabular-nums">
                  {formatDateTime(scheduled_at)}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>結果待ちが長い応募</CardTitle>
          {actions.data?.waiting_too_long.length === 0 && <Empty />}
          <ul className="space-y-2">
            {actions.data?.waiting_too_long.map(({ application, waiting_days }) => (
              <li key={application.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/applications/${application.id}`} className="hover:underline">
                  {application.company_name} / {application.position}
                </Link>
                <span className="text-muted-foreground tabular-nums">{waiting_days} 日</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>提出書類が未紐づけの応募</CardTitle>
          {actions.data?.missing_documents.length === 0 && <Empty />}
          <ul className="space-y-2">
            {actions.data?.missing_documents.map((application) => (
              <li key={application.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/applications/${application.id}`} className="hover:underline">
                  {application.company_name} / {application.position}
                </Link>
                <StatusBadge item={application} />
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>古い企業情報</CardTitle>
          {actions.data?.stale_sources.length === 0 && <Empty />}
          <ul className="space-y-2">
            {actions.data?.stale_sources.map((source) => (
              <li key={source.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/companies/${source.company_id}`} className="truncate hover:underline">
                  {source.url}
                </Link>
                <span className="text-muted-foreground tabular-nums">
                  {formatDate(source.fetched_at)}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>
            ステージ別通過率（応募済み {stats.data?.applied_total ?? 0} 件が母数）
          </CardTitle>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <th className="pb-1 font-normal">ステージ</th>
                <th className="pb-1 text-right font-normal">通過 / 結果確定</th>
                <th className="pb-1 text-right font-normal">通過率</th>
              </tr>
            </thead>
            <tbody>
              {stats.data?.stage_pass_rates.map((rate) => (
                <tr key={rate.stage_type} className="border-t">
                  <td className="py-1">{STAGE_TYPE_LABELS[rate.stage_type]}</td>
                  <td className="py-1 text-right tabular-nums">
                    {rate.passed} / {rate.decided}
                  </td>
                  <td className="py-1 text-right tabular-nums">{percent(rate.pass_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card>
          <CardTitle>
            経路別比較（内定までの日数: 平均 {stats.data?.days_to_offer.average ?? "—"} / 中央値{" "}
            {stats.data?.days_to_offer.median ?? "—"}）
          </CardTitle>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <th className="pb-1 font-normal">経路</th>
                <th className="pb-1 text-right font-normal">応募</th>
                <th className="pb-1 text-right font-normal">内定</th>
                <th className="pb-1 text-right font-normal">不合格</th>
                <th className="pb-1 text-right font-normal">内定率</th>
              </tr>
            </thead>
            <tbody>
              {stats.data?.channels.map((channel) => (
                <tr key={channel.channel} className="border-t">
                  <td className="py-1">{CHANNEL_LABELS[channel.channel]}</td>
                  <td className="py-1 text-right tabular-nums">{channel.applied}</td>
                  <td className="py-1 text-right tabular-nums">{channel.offers}</td>
                  <td className="py-1 text-right tabular-nums">{channel.rejected}</td>
                  <td className="py-1 text-right tabular-nums">{percent(channel.offer_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </>
  );
}
