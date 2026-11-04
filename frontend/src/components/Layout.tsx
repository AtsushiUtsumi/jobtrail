import {
  Building2,
  FileText,
  KanbanSquare,
  LayoutDashboard,
  ClipboardPaste,
  IdCard,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/utils";

const LINKS = [
  { to: "/", label: "ダッシュボード", icon: LayoutDashboard },
  { to: "/applications", label: "応募", icon: KanbanSquare },
  { to: "/companies", label: "企業", icon: Building2 },
  { to: "/documents", label: "書類", icon: FileText },
  { to: "/skill-profile", label: "スキルシート", icon: IdCard },
  { to: "/paste", label: "貼り付け入力", icon: ClipboardPaste },
];

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <nav className="flex shrink-0 gap-1 overflow-x-auto border-b p-3 md:w-52 md:flex-col md:border-r md:border-b-0">
        <div className="mr-3 px-2 py-1.5 font-semibold md:mb-3">JOBTRAIL</div>
        {LINKS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm whitespace-nowrap hover:bg-muted",
                isActive && "bg-muted font-medium",
              )
            }
          >
            <Icon className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="min-w-0 flex-1 p-4 md:p-6">
        <Outlet />
      </main>
    </div>
  );
}

export function PageHeader({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-xl font-semibold">{title}</h1>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </header>
  );
}
