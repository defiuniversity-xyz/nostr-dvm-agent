export type JobStatus =
  | "idle"
  | "submitted"
  | "payment_required"
  | "paying"
  | "processing"
  | "completed"
  | "error";

export interface DVMService {
  kind: number;
  name: string;
  label: string;
  description: string;
}

export interface JobResult {
  eventId: string;
  content: string;
  kind: number;
  timestamp: number;
}

export interface PaymentInfo {
  bolt11: string;
  amountMsats: number;
}

export const DVM_SERVICES: DVMService[] = [
  { kind: 5001, name: "generate", label: "Generate", description: "AI text generation" },
  { kind: 5000, name: "translate", label: "Translate", description: "Text translation" },
  { kind: 5001, name: "summarize", label: "Summarize", description: "Text summarization (uses task=summarize param)" },
  { kind: 5100, name: "image", label: "Image", description: "Image generation" },
  { kind: 5002, name: "extract", label: "Extract", description: "Extract content from URLs" },
];

export const RELAY_URLS = (import.meta.env.VITE_RELAY_URLS || "wss://relay.damus.io,wss://nos.lol,wss://relay.nostr.band")
  .split(",")
  .map((u: string) => u.trim());

export const DVM_PUBKEY: string = import.meta.env.VITE_DVM_PUBKEY || "";
