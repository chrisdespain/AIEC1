import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: "human" | "ai";
};

export function Message({ from, className, ...props }: MessageProps) {
  return (
    <div
      data-role={from}
      className={cn(
        "group/message flex w-full items-start gap-3",
        from === "human" && "flex-row-reverse",
        className
      )}
      {...props}
    />
  );
}

export function MessageAvatar({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & { children: ReactNode }) {
  return (
    <div
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-2xl border bg-card text-muted-foreground shadow-sm",
        "group-data-[role=human]/message:border-primary/20 group-data-[role=human]/message:bg-primary group-data-[role=human]/message:text-primary-foreground",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function MessageContent({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "max-w-[min(82%,44rem)] rounded-3xl rounded-tl-md border border-border/70 bg-card px-4 py-3 text-[0.9375rem] leading-7 text-card-foreground shadow-sm",
        "group-data-[role=human]/message:rounded-tl-3xl group-data-[role=human]/message:rounded-tr-md group-data-[role=human]/message:border-primary group-data-[role=human]/message:bg-primary group-data-[role=human]/message:text-primary-foreground",
        className
      )}
      {...props}
    />
  );
}

export function MessageResponse({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("whitespace-pre-wrap", className)} {...props} />;
}
