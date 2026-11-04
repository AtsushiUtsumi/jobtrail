export function formatDate(value?: string | null): string {
  return value ? new Date(value).toLocaleDateString("ja-JP") : "—";
}

export function formatDateTime(value?: string | null): string {
  return value
    ? new Date(value).toLocaleString("ja-JP", { dateStyle: "short", timeStyle: "short" })
    : "—";
}

/** ISO 文字列を <input type="datetime-local"> の値（ローカル時刻）へ変換する。 */
export function toLocalInput(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function fromLocalInput(value: FormDataEntryValue | null): string | null {
  return value ? new Date(String(value)).toISOString() : null;
}

export function text(form: FormData, name: string): string {
  return String(form.get(name) ?? "").trim();
}

export function textOrNull(form: FormData, name: string): string | null {
  return text(form, name) || null;
}

export function numberOrNull(form: FormData, name: string): number | null {
  const value = text(form, name);
  return value === "" ? null : Number(value);
}

export function list(form: FormData, name: string): string[] {
  return text(form, name)
    .split(/[,、\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
