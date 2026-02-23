import type { JobStatus } from "../lib/types";

interface StatusIndicatorProps {
  status: JobStatus;
}

const STATUS_CONFIG: Record<JobStatus, { label: string; color: string; animate: boolean }> = {
  idle: { label: "", color: "", animate: false },
  submitted: { label: "Submitting to Nostr...", color: "text-blue-500", animate: true },
  payment_required: { label: "Payment required", color: "text-amber-500", animate: false },
  paying: { label: "Processing payment...", color: "text-amber-500", animate: true },
  processing: { label: "AI is thinking...", color: "text-purple-500", animate: true },
  completed: { label: "Complete", color: "text-green-500", animate: false },
  error: { label: "Error", color: "text-red-500", animate: false },
};

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const config = STATUS_CONFIG[status];
  if (!config.label) return null;

  return (
    <div className={`flex items-center gap-2 text-sm font-medium ${config.color}`}>
      {config.animate && (
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-current" />
        </span>
      )}
      {!config.animate && status === "completed" && (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.857-9.809a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5Z" clipRule="evenodd" />
        </svg>
      )}
      {config.label}
    </div>
  );
}
