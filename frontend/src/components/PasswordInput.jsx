import { useState } from "react";

const fieldClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 pr-10 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const EyeIcon = ({ off }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4.5 w-4.5" aria-hidden="true">
    {off ? (
      <>
        <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
        <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
        <path d="M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
        <line x1="2" y1="2" x2="22" y2="22" />
      </>
    ) : (
      <>
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    )}
  </svg>
);

export default function PasswordInput({ id, ...props }) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative">
      <input id={id} type={show ? "text" : "password"} className={fieldClass} {...props} />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "Hide password" : "Show password"}
        className="absolute inset-y-0 right-0 flex cursor-pointer items-center px-3 text-foreground-subtle hover:text-foreground"
      >
        <EyeIcon off={show} />
      </button>
    </div>
  );
}