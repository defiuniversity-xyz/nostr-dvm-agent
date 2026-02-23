import { generateSecretKey, getPublicKey } from "nostr-tools/pure";

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

const STORAGE_KEY = "sats_ai_secret_key";

export interface KeyPair {
  secretKey: Uint8Array;
  publicKey: string;
}

declare global {
  interface Window {
    nostr?: {
      getPublicKey: () => Promise<string>;
      signEvent: (event: unknown) => Promise<unknown>;
    };
  }
}

export function hasNip07Extension(): boolean {
  return typeof window !== "undefined" && !!window.nostr;
}

export function getOrCreateKeys(): KeyPair {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    const secretKey = hexToBytes(stored);
    const publicKey = getPublicKey(secretKey);
    return { secretKey, publicKey };
  }

  const secretKey = generateSecretKey();
  const publicKey = getPublicKey(secretKey);
  localStorage.setItem(STORAGE_KEY, bytesToHex(secretKey));
  return { secretKey, publicKey };
}

export async function getNip07PublicKey(): Promise<string | null> {
  if (!hasNip07Extension()) return null;
  try {
    return await window.nostr!.getPublicKey();
  } catch {
    return null;
  }
}
