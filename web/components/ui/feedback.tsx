"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span className={`ui-spinner ${className}`} role="status" aria-label="Loading">
      <span className="ui-spinner-ring" />
    </span>
  );
}

export function LiveDot({ live = true, label }: { live?: boolean; label?: string }) {
  return (
    <span className={`ui-live ${live ? "is-live" : "is-stale"}`}>
      <span className="ui-live-dot" aria-hidden />
      {label ? <span>{label}</span> : null}
    </span>
  );
}

export function ProgressBar({
  value,
  tone = "ink",
  label,
  detail,
  indeterminate = false,
}: {
  value?: number;
  tone?: "ink" | "moss" | "oxide" | "amber";
  label?: string;
  detail?: string;
  indeterminate?: boolean;
}) {
  const clamped = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div className="ui-progress">
      {(label || detail) && (
        <div className="ui-progress-meta">
          {label ? <span className="ui-progress-label">{label}</span> : <span />}
          {detail ? <span className="ui-progress-detail">{detail}</span> : null}
        </div>
      )}
      <div
        className={`ui-progress-track tone-${tone}${indeterminate ? " is-indeterminate" : ""}`}
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="ui-progress-fill"
          style={indeterminate ? undefined : { width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`ui-skeleton ${className}`} aria-hidden />;
}

export function BusyButton({
  busy,
  busyLabel = "Working…",
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  busy?: boolean;
  busyLabel?: string;
}) {
  return (
    <button
      {...props}
      disabled={busy || props.disabled}
      aria-busy={busy || undefined}
      className={`ui-btn ${className}`}
    >
      {busy ? (
        <span className="inline-flex items-center gap-2">
          <Spinner />
          {busyLabel}
        </span>
      ) : (
        children
      )}
    </button>
  );
}

export function PageLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-5xl flex-col items-center justify-center gap-4 px-6 py-16">
      <Spinner className="ui-spinner-lg" />
      <p className="text-sm text-muted">{label}</p>
      <div className="w-full max-w-xs">
        <ProgressBar indeterminate tone="moss" />
      </div>
    </main>
  );
}

export function WorkingBanner({ show, label = "Working on that…" }: { show: boolean; label?: string }) {
  if (!show) return null;
  return (
    <div className="ui-working-banner" role="status" aria-live="polite">
      <Spinner />
      <span>{label}</span>
      <div className="ui-working-banner-bar">
        <ProgressBar indeterminate tone="oxide" />
      </div>
    </div>
  );
}

export function EmptyHint({ children }: { children: ReactNode }) {
  return <p className="ui-empty">{children}</p>;
}
