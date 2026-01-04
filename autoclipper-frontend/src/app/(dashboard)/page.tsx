export default function OverviewPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Overview</h1>
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Active Channels</div>
          <div className="mt-2 text-2xl font-semibold">—</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Videos Today</div>
          <div className="mt-2 text-2xl font-semibold">—</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Clips Ready</div>
          <div className="mt-2 text-2xl font-semibold">—</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Upload Success</div>
          <div className="mt-2 text-2xl font-semibold">—</div>
        </div>
      </div>

      <div className="rounded-lg border p-4">
        <div className="text-sm font-medium">Recent Activity</div>
        <div className="mt-3 text-sm text-muted-foreground">
          No recent activity.
        </div>
      </div>
    </div>
  );
}
