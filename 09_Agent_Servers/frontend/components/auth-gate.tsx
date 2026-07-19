"use client";

import { useState, useEffect } from "react";
import { Cat, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [code, setCode] = useState("");
  const [error, setError] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("auth");
      if (stored === "1") {
        setAuthenticated(true);
        setChecking(false);
        return;
      }
    }
    // Check if auth is even required (server-side check with empty code)
    fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: "" }),
    })
      .then((res) => {
        if (res.ok) {
          // No access code configured — skip gate
          setAuthenticated(true);
        }
      })
      .finally(() => setChecking(false));
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code.trim() }),
    });
    if (res.ok) {
      sessionStorage.setItem("auth", "1");
      setAuthenticated(true);
      setError(false);
    } else {
      setError(true);
    }
  };

  if (checking) return null;

  if (authenticated) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-background px-4">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,oklch(0.94_0.07_170_/_0.72),transparent_68%)]" />
      <div className="relative z-10 w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/15">
            <Cat className="size-6" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight">Whisker Health</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter the access code to continue
          </p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="password"
                value={code}
                onChange={(e) => {
                  setCode(e.target.value);
                  setError(false);
                }}
                placeholder="Access code"
                autoFocus
                className="h-11 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-primary/40 focus:ring-4 focus:ring-primary/10"
              />
            </div>
            {error && (
              <p className="mt-2 text-xs text-destructive">
                Incorrect code. Please try again.
              </p>
            )}
          </div>
          <Button
            type="submit"
            className="w-full rounded-xl"
            disabled={code.trim().length === 0}
          >
            Continue
          </Button>
        </form>
      </div>
    </div>
  );
}
