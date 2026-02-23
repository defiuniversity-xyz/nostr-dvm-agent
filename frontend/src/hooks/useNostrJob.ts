import { useState, useCallback, useRef, useEffect } from "react";
import { publishJobRequest, subscribeFeedback, subscribeResult } from "../lib/nostr";
import { getOrCreateKeys, type KeyPair } from "../lib/keys";
import type { JobStatus, PaymentInfo, JobResult } from "../lib/types";

interface UseNostrJobReturn {
  submit: (kind: number, input: string, params?: Record<string, string>) => Promise<void>;
  status: JobStatus;
  payment: PaymentInfo | null;
  result: JobResult | null;
  error: string | null;
  reset: () => void;
}

export function useNostrJob(): UseNostrJobReturn {
  const [status, setStatus] = useState<JobStatus>("idle");
  const [payment, setPayment] = useState<PaymentInfo | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cleanupRef = useRef<(() => void)[]>([]);
  const keysRef = useRef<KeyPair | null>(null);

  useEffect(() => {
    return () => {
      for (const cleanup of cleanupRef.current) cleanup();
    };
  }, []);

  const reset = useCallback(() => {
    for (const cleanup of cleanupRef.current) cleanup();
    cleanupRef.current = [];
    setStatus("idle");
    setPayment(null);
    setResult(null);
    setError(null);
  }, []);

  const submit = useCallback(async (kind: number, input: string, params?: Record<string, string>) => {
    reset();
    setStatus("submitted");

    if (!keysRef.current) {
      keysRef.current = getOrCreateKeys();
    }

    try {
      const jobEventId = await publishJobRequest(keysRef.current, kind, input, params);

      const resultKind = kind + 1000;

      const unsubFeedback = subscribeFeedback(jobEventId, (fbStatus, paymentInfo) => {
        if (fbStatus === "payment-required" && paymentInfo) {
          setStatus("payment_required");
          setPayment(paymentInfo);
        } else if (fbStatus === "processing") {
          setStatus("processing");
        } else if (fbStatus === "error") {
          setStatus("error");
          setError("Job failed on the agent side.");
        }
      });

      const unsubResult = subscribeResult(jobEventId, resultKind, (jobResult) => {
        setResult(jobResult);
        setStatus("completed");
      });

      cleanupRef.current.push(unsubFeedback, unsubResult);
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Failed to submit job");
    }
  }, [reset]);

  return { submit, status, payment, result, error, reset };
}
