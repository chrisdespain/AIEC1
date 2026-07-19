"use client";

import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/react";
import {
  AlertCircle,
  ArrowUp,
  BookOpenText,
  Bot,
  ChevronDown,
  Droplets,
  FileText,
  HeartPulse,
  Loader2,
  Search,
  ShieldCheck,
  Sparkles,
  Syringe,
  User,
  Wrench,
} from "lucide-react";

import {
  Message,
  MessageAvatar,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getMessageText, toolLabel } from "@/lib/messages";

function resolveApiUrl() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") return `${window.location.origin}/api`;
  return "/api";
}

type StreamMessage = ReturnType<typeof useStream>["messages"][number];

const SUGGESTIONS = [
  {
    title: "Kitten vaccines",
    prompt: "What vaccinations does my kitten need and when?",
    icon: Syringe,
  },
  {
    title: "Hydration signs",
    prompt: "What are the signs of dehydration in cats?",
    icon: Droplets,
  },
  {
    title: "Preventive care",
    prompt: "How often should I deworm my cat?",
    icon: HeartPulse,
  },
];

function toolIcon(name?: string) {
  if (name === "retrieve_information") return <FileText className="size-3.5" />;
  if (name?.startsWith("tavily")) return <Search className="size-3.5" />;
  return <Wrench className="size-3.5" />;
}

export function Chat({ assistantId }: { assistantId: string }) {
  const stream = useStream({ apiUrl: resolveApiUrl(), assistantId });
  const { messages, isLoading, error } = stream;
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  useEffect(() => {
    const inputElement = inputRef.current;
    if (!inputElement) return;
    inputElement.style.height = "0px";
    inputElement.style.height = `${Math.min(inputElement.scrollHeight, 144)}px`;
  }, [input]);

  const send = (text: string) => {
    const content = text.trim();
    if (!content || isLoading) return;
    stream.submit({ messages: [{ type: "human", content }] });
    setInput("");
  };

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    send(input);
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(input);
    }
  };

  return (
    <div className="relative z-10 flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <div
          className="mx-auto flex min-h-full w-full max-w-4xl flex-col px-4 sm:px-6"
          aria-live="polite"
        >
          {messages.length === 0 ? (
            <WelcomeState onSelect={send} />
          ) : (
            <div className="flex flex-1 flex-col gap-6 py-8 sm:py-10">
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <BookOpenText className="size-3.5 text-primary" />
                Conversation grounded in your cat health guide
              </div>
              {messages.map((message, index) => (
                <MessageRow key={message.id ?? index} message={message} />
              ))}
              {isLoading && <ThinkingRow />}
              {error != null && <ErrorRow error={error} />}
              <div ref={endRef} className="h-px" />
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border/60 bg-background/80 px-4 py-3 backdrop-blur-xl sm:px-6 sm:py-4">
        <form onSubmit={onSubmit} className="mx-auto w-full max-w-4xl">
          <div className="rounded-[1.4rem] border border-border/80 bg-card p-2 shadow-[0_16px_50px_-24px_oklch(0.25_0.04_170_/_0.35)] transition-shadow focus-within:border-primary/35 focus-within:ring-4 focus-within:ring-primary/8">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask about symptoms, nutrition, vaccines, or preventive care..."
              disabled={isLoading}
              rows={1}
              autoFocus
              aria-label="Message Whisker Health"
              className="max-h-36 min-h-12 w-full resize-none bg-transparent px-3 py-3 text-[0.9375rem] leading-6 outline-none placeholder:text-muted-foreground/75 disabled:cursor-not-allowed disabled:opacity-60"
            />
            <div className="flex items-center justify-between gap-3 px-2 pb-1">
              <div className="flex items-center gap-1.5 text-[0.6875rem] text-muted-foreground">
                <ShieldCheck className="size-3.5 text-primary" />
                <span className="hidden sm:inline">AI guidance is not a veterinary diagnosis</span>
                <span className="sm:hidden">Not a diagnosis</span>
              </div>
              <Button
                type="submit"
                size="icon-lg"
                disabled={isLoading || input.trim().length === 0}
                aria-label={isLoading ? "Generating response" : "Send message"}
                className="rounded-full shadow-sm"
              >
                {isLoading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <ArrowUp className="size-4" />
                )}
              </Button>
            </div>
          </div>
          <p className="mt-2 hidden text-center text-[0.6875rem] text-muted-foreground sm:block">
            Press Enter to send · Shift + Enter for a new line
          </p>
        </form>
      </div>
    </div>
  );
}

function WelcomeState({ onSelect }: { onSelect: (prompt: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-10 sm:py-14">
      <div className="mb-6 flex size-16 items-center justify-center rounded-[1.4rem] border border-primary/15 bg-primary/8 text-primary shadow-lg shadow-primary/10">
        <Sparkles className="size-7" />
      </div>
      <div className="max-w-xl text-center">
        <Badge variant="secondary" className="mb-4 rounded-full px-3 py-1">
          <span className="mr-1.5 size-1.5 rounded-full bg-primary" />
          Cat care, made clearer
        </Badge>
        <h2 className="text-balance text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">
          How can I help your cat today?
        </h2>
        <p className="mx-auto mt-3 max-w-lg text-pretty text-sm leading-6 text-muted-foreground sm:text-base">
          Get clear, evidence-informed answers grounded in trusted cat health guidance.
        </p>
      </div>
      <div className="mt-8 grid w-full max-w-2xl gap-3 sm:grid-cols-3">
        {SUGGESTIONS.map(({ title, prompt, icon: Icon }) => (
          <button
            key={title}
            type="button"
            onClick={() => onSelect(prompt)}
            className="group rounded-2xl border border-border/70 bg-card/80 p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/25 hover:bg-card hover:shadow-md focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <div className="mb-4 flex size-9 items-center justify-center rounded-xl bg-primary/8 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
              <Icon className="size-4" />
            </div>
            <span className="block text-sm font-medium">{title}</span>
            <span className="mt-1 block text-xs leading-5 text-muted-foreground">
              {prompt}
            </span>
          </button>
        ))}
      </div>
      <div className="mt-8 flex max-w-lg items-start gap-2 rounded-xl border border-amber-500/15 bg-amber-500/5 px-3 py-2.5 text-xs leading-5 text-muted-foreground">
        <HeartPulse className="mt-0.5 size-3.5 shrink-0 text-amber-700" />
        For emergencies or severe symptoms, contact a veterinarian immediately.
      </div>
    </div>
  );
}

function MessageRow({ message }: { message: StreamMessage }) {
  const isHuman = message.type === "human";
  const isTool = message.type === "tool";
  const text = getMessageText(message.content);
  const toolCalls =
    message.type === "ai"
      ? (message as unknown as {
          tool_calls?: Array<{ name?: string; id?: string }>;
        }).tool_calls ?? []
      : [];

  if (isTool) {
    return <ToolResult message={message} text={text} />;
  }

  if (!text && toolCalls.length === 0) return null;

  return (
    <Message from={isHuman ? "human" : "ai"}>
      <MessageAvatar>
        {isHuman ? <User className="size-4" /> : <Bot className="size-4" />}
      </MessageAvatar>
      <div className={isHuman ? "flex flex-col items-end gap-2" : "flex flex-col gap-2"}>
        {toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {toolCalls.map((toolCall, index) => (
              <Badge
                key={toolCall.id ?? index}
                variant="secondary"
                className="rounded-full px-2.5 py-1 text-[0.6875rem]"
              >
                {toolIcon(toolCall.name)}
                Checking {toolLabel(toolCall.name).toLowerCase()}
              </Badge>
            ))}
          </div>
        )}
        {text && (
          <MessageContent>
            <MessageResponse>{text}</MessageResponse>
          </MessageContent>
        )}
      </div>
    </Message>
  );
}

function ToolResult({ message, text }: { message: StreamMessage; text: string }) {
  return (
    <details className="group/tool ml-12 rounded-2xl border border-border/60 bg-muted/35 text-sm sm:ml-12">
      <summary className="flex cursor-pointer list-none items-center gap-2.5 px-3.5 py-2.5 text-muted-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
        <span className="flex size-7 items-center justify-center rounded-lg bg-background text-primary shadow-sm">
          {toolIcon(message.name)}
        </span>
        <span className="font-medium text-foreground">{toolLabel(message.name)}</span>
        <span className="text-xs">source consulted</span>
        <ChevronDown className="ml-auto size-3.5 transition-transform group-open/tool:rotate-180" />
      </summary>
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap border-t border-border/60 px-4 py-3 font-mono text-xs leading-5 text-muted-foreground">
        {text}
      </pre>
    </details>
  );
}

function ThinkingRow() {
  return (
    <Message from="ai">
      <MessageAvatar>
        <Bot className="size-4" />
      </MessageAvatar>
      <div className="flex items-center gap-3 rounded-3xl rounded-tl-md border border-border/60 bg-card px-4 py-3 text-sm text-muted-foreground shadow-sm">
        <span className="flex gap-1" aria-hidden="true">
          <span className="size-1.5 animate-pulse rounded-full bg-primary [animation-delay:-0.3s]" />
          <span className="size-1.5 animate-pulse rounded-full bg-primary [animation-delay:-0.15s]" />
          <span className="size-1.5 animate-pulse rounded-full bg-primary" />
        </span>
        Reviewing trusted guidance
      </div>
    </Message>
  );
}

function ErrorRow({ error }: { error: unknown }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 p-4 text-sm">
      <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div>
        <p className="font-medium text-foreground">I couldn’t complete that response</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {error instanceof Error ? error.message : "Please check the local server and try again."}
        </p>
      </div>
    </div>
  );
}
