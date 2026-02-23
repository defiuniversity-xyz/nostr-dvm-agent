import type { JobResult } from "../lib/types";

interface ResultCardProps {
  result: JobResult;
  amountMsats?: number;
}

function isImageDataUrl(content: string): boolean {
  return content.startsWith("data:image/");
}

export function ResultCard({ result, amountMsats }: ResultCardProps) {
  const sats = amountMsats ? Math.ceil(amountMsats / 1000) : null;
  const isImage = isImageDataUrl(result.content);

  return (
    <div className="w-full max-w-2xl mx-auto mt-6">
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm">
        {isImage ? (
          <div className="flex flex-col items-center gap-4">
            <img
              src={result.content}
              alt="Generated image"
              className="max-w-full rounded-xl shadow-md"
            />
            <a
              href={result.content}
              download="sats-ai-image.png"
              className="text-sm text-amber-600 dark:text-amber-400 hover:underline"
            >
              Download image
            </a>
          </div>
        ) : (
          <div className="prose dark:prose-invert max-w-none">
            <p className="text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap leading-relaxed">
              {result.content}
            </p>
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center gap-3 text-xs text-zinc-400">
          {sats && (
            <span className="flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-3 h-3 text-amber-500">
                <path fillRule="evenodd" d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1ZM5.404 4.404a.75.75 0 0 0 0 1.06L6.94 7H4.75a.75.75 0 0 0 0 1.5h2.19L5.404 10.04a.75.75 0 1 0 1.06 1.06l2.5-2.5a.75.75 0 0 0 0-1.06l-2.5-2.5a.75.75 0 0 0-1.06 0Z" clipRule="evenodd" />
              </svg>
              {sats.toLocaleString()} sats
            </span>
          )}
          <span>Kind {result.kind}</span>
          <span>{new Date(result.timestamp * 1000).toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}
