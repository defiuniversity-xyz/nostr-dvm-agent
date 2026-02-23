interface HeaderProps {
  compact?: boolean;
}

export function Header({ compact = false }: HeaderProps) {
  return (
    <header className={compact ? "py-4" : "pt-24 pb-8"}>
      <div className="text-center">
        <h1
          className={`font-bold tracking-tight text-zinc-900 dark:text-white ${
            compact ? "text-2xl" : "text-5xl"
          }`}
        >
          sats<span className="text-amber-500">.ai</span>
        </h1>
        {!compact && (
          <p className="mt-3 text-zinc-500 dark:text-zinc-400 text-lg">
            AI for the open web
          </p>
        )}
      </div>
    </header>
  );
}
