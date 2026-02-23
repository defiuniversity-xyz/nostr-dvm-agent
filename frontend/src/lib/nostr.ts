import { SimplePool, finalizeEvent, type Event, type Filter } from "nostr-tools";
import { RELAY_URLS, DVM_PUBKEY, type PaymentInfo, type JobResult } from "./types";
import { type KeyPair, hasNip07Extension } from "./keys";

const pool = new SimplePool();

export function getPool(): SimplePool {
  return pool;
}

export async function publishJobRequest(
  keys: KeyPair,
  kind: number,
  inputText: string,
  params?: Record<string, string>,
): Promise<string> {
  const tags: string[][] = [
    ["i", inputText, "text"],
    ["output", "text/plain"],
  ];

  if (DVM_PUBKEY) {
    tags.push(["p", DVM_PUBKEY]);
  }

  if (params) {
    for (const [k, v] of Object.entries(params)) {
      tags.push(["param", k, v]);
    }
  }

  const eventTemplate = {
    kind,
    created_at: Math.floor(Date.now() / 1000),
    tags,
    content: "",
  };

  let signedEvent: Event;

  if (hasNip07Extension()) {
    signedEvent = (await window.nostr!.signEvent(eventTemplate)) as Event;
  } else {
    signedEvent = finalizeEvent(eventTemplate, keys.secretKey);
  }

  await Promise.any(pool.publish(RELAY_URLS, signedEvent));
  return signedEvent.id;
}

export function subscribeFeedback(
  jobEventId: string,
  onFeedback: (status: string, payment?: PaymentInfo) => void,
): () => void {
  const filter: Filter = {
    kinds: [7000],
    "#e": [jobEventId],
  };

  const sub = pool.subscribeMany(RELAY_URLS, filter, {
    onevent(event: Event) {
      let status = "";
      let bolt11 = "";
      let amountMsats = 0;

      for (const tag of event.tags) {
        if (tag[0] === "status") status = tag[1];
        if (tag[0] === "amount") {
          amountMsats = parseInt(tag[1], 10) || 0;
          if (tag.length > 2) bolt11 = tag[2];
        }
      }

      if (status === "payment-required" && bolt11) {
        onFeedback(status, { bolt11, amountMsats });
      } else {
        onFeedback(status);
      }
    },
  });

  return () => sub.close();
}

export function subscribeResult(
  jobEventId: string,
  resultKind: number,
  onResult: (result: JobResult) => void,
): () => void {
  const filter: Filter = {
    kinds: [resultKind],
    "#e": [jobEventId],
  };

  const sub = pool.subscribeMany(RELAY_URLS, filter, {
    onevent(event: Event) {
      onResult({
        eventId: event.id,
        content: event.content,
        kind: event.kind,
        timestamp: event.created_at,
      });
    },
  });

  return () => sub.close();
}
