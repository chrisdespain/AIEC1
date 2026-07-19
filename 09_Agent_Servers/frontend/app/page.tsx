import { Cat, ShieldCheck } from "lucide-react";

import { Chat } from "@/components/chat";

const ASSISTANT_ID = "agent";

export default function Page() {
  return (
    <main className="relative flex h-dvh flex-col overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,oklch(0.94_0.07_170_/_0.72),transparent_68%)]" />
      <header className="relative z-10 border-b border-border/60 bg-background/75 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/15">
              <Cat className="size-5" />
            </div>
            <div className="min-w-0 leading-tight">
              <h1 className="truncate text-sm font-semibold tracking-tight sm:text-base">
                Whisker Health
              </h1>
              <p className="truncate text-xs text-muted-foreground">
                Evidence-informed cat care assistant
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 rounded-full border border-primary/15 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary">
            <ShieldCheck className="size-3.5" />
            <span className="hidden sm:inline">Knowledge base ready</span>
            <span className="sm:hidden">Ready</span>
          </div>
        </div>
      </header>

      <Chat assistantId={ASSISTANT_ID} />
    </main>
  );
}
