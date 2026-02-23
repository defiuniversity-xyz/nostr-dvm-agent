import { useState } from "react";
import { hasNip07Extension, getNip07PublicKey } from "../lib/keys";

interface HeaderProps {
  compact?: boolean;
}

export function Header({ compact = false }: HeaderProps) {
  const [connectedPubkey, setConnectedPubkey] = useState<string | null>(null);

  const connectWallet = async () => {
    const pk = await getNip07PublicKey();
    if (pk) {
      setConnectedPubkey(pk);
    }
  };

  const hasExtension = hasNip07Extension();

  return (
    <header className={`w-full ${compact ? "py-4" : "pt-24 pb-8"}`}>
      <div className={compact ? "flex items-center justify-between max-w-2xl mx-auto px-4" : "text-center"}>
        <h1
          className={`font-bold tracking-tight text-zinc-900 dark:text-white ${
            compact ? "text-2xl" : "text-5xl"
          }`}
        >
          sats<span className="text-amber-500">.ai</span>
        </h1>

        {compact && hasExtension && !connectedPubkey && (
          <button
            onClick={connectWallet}
            className="text-xs px-3 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            Connect Wallet
          </button>
        )}

        {compact && connectedPubkey && (
          <span className="text-xs text-zinc-400 font-mono">
            {connectedPubkey.slice(0, 8)}...
          </span>
        )}

        {!compact && (
          <p className="mt-3 text-zinc-500 dark:text-zinc-400 text-lg">
            AI for the open web
          </p>
        )}
      </div>
    </header>
  );
}
