const variants = {
  error: {
    box: "border-danger/30 bg-danger/5",
    icon: "bg-danger/15 text-danger",
    path: "M12 8v5m0 3.5h.01",
    role: "alert",
  },
  success: {
    box: "border-success/30 bg-success/5",
    icon: "bg-success/15 text-success",
    path: "M5 12.5l4.5 4.5L19 7.5",
    role: "status",
  },
  info: {
    box: "border-info/30 bg-info/5",
    icon: "bg-info/15 text-info",
    path: "M12 11v5m0-8.5h.01",
    role: "status",
  },
};

export default function Alert({ variant = "error", title, children, onClose }) {
  if (!children) return null;
  const v = variants[variant];

  return (
    <div
      role={v.role}
      className={`flex animate-fade-in items-start gap-3 rounded-sm border p-3.5 ${v.box}`}
    >
      <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${v.icon}`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"
          strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5" aria-hidden="true">
          <path d={v.path} />
        </svg>
      </span>

      <div className="min-w-0 flex-1 text-sm">
        {title && <p className="font-medium text-foreground">{title}</p>}
        <p className={`leading-relaxed text-foreground-muted ${title ? "mt-0.5" : ""}`}>{children}</p>
      </div>

      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Dismiss"
          className="-mr-1 shrink-0 cursor-pointer p-1 text-foreground-subtle hover:text-foreground"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" className="h-4 w-4" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      )}
    </div>
  );
}