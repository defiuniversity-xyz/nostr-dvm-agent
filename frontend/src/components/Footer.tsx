export function Footer() {
  return (
    <footer className="py-8 text-center text-xs text-zinc-400 dark:text-zinc-600">
      <p>
        Powered by{" "}
        <a href="https://github.com/nostr-protocol/nips/blob/master/90.md" target="_blank" rel="noopener noreferrer" className="underline hover:text-zinc-600 dark:hover:text-zinc-400">
          NIP-90
        </a>
        {" "}&middot;{" "}
        Payments via Bitcoin Lightning
        {" "}&middot;{" "}
        <a href="https://github.com/defiuniversity-xyz/nostr-dvm-agent" target="_blank" rel="noopener noreferrer" className="underline hover:text-zinc-600 dark:hover:text-zinc-400">
          Open Source
        </a>
      </p>
    </footer>
  );
}
