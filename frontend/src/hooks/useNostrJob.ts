import { useState, useCallback, useRef, useEffect } from "react";
import { publishJobRequest, subscribeFeedback, subscribeResult } from "../lib/nostr";
import { getOrCreateKeys, type KeyPair } from "../lib/keys";
import type { JobStatus, PaymentInfo, JobResult } from "../lib/types";

const PAYMENT_TIMEOUT_MS = 5 * 60 * 1000;

interface UseNostrJobReturn {
  submit: (kind: number, input: string, params?: Record<string, string>) => Promise<void>;
  status: JobStatus;
  payment: PaymentInfo | null;
  result: JobResult | null;
  error: string | null;
  paymentTimedOut: boolean;
  reset: () => void;
}

export function useNostrJob(): UseNostrJobReturn {
  const [status, setStatus] = useState<JobStatus>("idle");
  const [payment, setPayment] = useState<PaymentInfo | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paymentTimedOut, setPaymentTimedOut] = useState(false);

  const cleanupRef = useRef<(() => void)[]>([]);
  const keysRef = useRef<KeyPair | null>(null);
  const paymentTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      for (const cleanup of cleanupRef.current) cleanup();
      if (paymentTimerRef.current) clearTimeout(paymentTimerRef.current);
    };
  }, []);

  const reset = useCallback(() => {
    for (const cleanup of cleanupRef.current) cleanup();
    cleanupRef.current = [];
    if (paymentTimerRef.current) {
      clearTimeout(paymentTimerRef.current);
      paymentTimerRef.current = null;
    }
    setStatus("idle");
    setPayment(null);
    setResult(null);
    setError(null);
    setPaymentTimedOut(false);
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
          setPaymentTimedOut(false);

          if (paymentTimerRef.current) clearTimeout(paymentTimerRef.current);
          paymentTimerRef.current = setTimeout(() => {
            setPaymentTimedOut(true);
          }, PAYMENT_TIMEOUT_MS);
        } else if (fbStatus === "processing") {
          setStatus("processing");
          setPaymentTimedOut(false);
          if (paymentTimerRef.current) {
            clearTimeout(paymentTimerRef.current);
            paymentTimerRef.current = null;
          }
        } else if (fbStatus === "error") {
          setStatus("error");
          setError("Job failed on the agent side.");
        }
      });

      const unsubResult = subscribeResult(jobEventId, resultKind, (jobResult) => {
        setResult(jobResult);
        setStatus("completed");
        if (paymentTimerRef.current) {
          clearTimeout(paymentTimerRef.current);
          paymentTimerRef.current = null;
        }
      });

      cleanupRef.current.push(unsubFeedback, unsubResult);
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Failed to submit job request to relays");
    }
  }, [reset]);

  return { submit, status, payment, result, error, paymentTimedOut, reset };
}
