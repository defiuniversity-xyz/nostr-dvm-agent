import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import type { PaymentInfo } from "../lib/types";

interface PaymentModalProps {
  payment: PaymentInfo;
  timedOut: boolean;
  onClose: () => void;
}

export function PaymentModal({ payment, timedOut, onClose }: PaymentModalProps) {
  const sats = Math.ceil(payment.amountMsats / 1000);
  const [copied, setCopied] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const copyInvoice = async () => {
    await navigator.clipboard.writeText(payment.bolt11);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-zinc-900 rounded-2xl max-w-md w-full p-8 shadow-2xl">
        <h2 className="text-xl font-semibold text-center mb-2 text-zinc-900 dark:text-white">
          Pay {sats.toLocaleString()} sats
        </h2>
        <p className="text-sm text-zinc-500 text-center mb-6">
          Scan with any Lightning wallet
        </p>

        <div className="flex justify-center mb-6">
          <div className="bg-white p-4 rounded-xl">
            <QRCodeSVG
              value={payment.bolt11}
              size={220}
              level="M"
            />
          </div>
        </div>

        <div className="space-y-3">
          <button
            onClick={copyInvoice}
            className="w-full py-3 bg-amber-500 hover:bg-amber-600 text-white font-medium rounded-xl transition-colors"
          >
            {copied ? "Copied!" : "Copy Invoice"}
          </button>
          <button
            onClick={onClose}
            className="w-full py-3 border border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800 rounded-xl transition-colors"
          >
            Cancel
          </button>
        </div>

        {timedOut ? (
          <div className="mt-4 text-center">
            <p className="text-sm text-amber-600 dark:text-amber-400 font-medium">
              Payment not confirmed yet.
            </p>
            <p className="text-xs text-zinc-400 mt-1">
              If you already paid, the agent may still be processing. Try refreshing.
            </p>
          </div>
        ) : (
          <p className="text-xs text-zinc-400 text-center mt-4">
            Waiting for payment confirmation... {minutes}:{seconds.toString().padStart(2, "0")}
          </p>
        )}
      </div>
    </div>
  );
}
