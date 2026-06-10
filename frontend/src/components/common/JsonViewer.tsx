export function JsonViewer({ data }: { data: unknown }) {
  let text: string;
  try {
    text = JSON.stringify(data, null, 2);
  } catch {
    text = String(data);
  }
  return (
    <pre className="max-h-[480px] overflow-auto rounded-md border border-border bg-background/60 p-3 text-xs leading-relaxed text-muted-foreground">
      <code>{text}</code>
    </pre>
  );
}
