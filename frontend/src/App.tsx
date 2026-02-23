import { useState } from "react";
import { Header } from "./components/Header";
import { SearchBar } from "./components/SearchBar";
import { ServicePicker } from "./components/ServicePicker";
import { StatusIndicator } from "./components/StatusIndicator";
import { PaymentModal } from "./components/PaymentModal";
import { ResultCard } from "./components/ResultCard";
import { Footer } from "./components/Footer";
import { useNostrJob } from "./hooks/useNostrJob";
import { DVM_SERVICES, type DVMService } from "./lib/types";

function App() {
  const [selectedService, setSelectedService] = useState<DVMService>(DVM_SERVICES[0]);
  const [currentQuery, setCurrentQuery] = useState("");
  const { submit, status, payment, result, error, reset } = useNostrJob();

  const hasActivity = status !== "idle";

  const handleSubmit = async (query: string) => {
    setCurrentQuery(query);
    const params: Record<string, string> = {};
    if (selectedService.name === "summarize") {
      params["task"] = "summarize";
    }
    await submit(selectedService.kind, query, params);
  };

  const handleNewQuery = () => {
    reset();
    setCurrentQuery("");
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col">
      <div className="flex-1 flex flex-col items-center px-4">
        <Header compact={hasActivity} />

        {!hasActivity && (
          <>
            <SearchBar onSubmit={handleSubmit} />
            <ServicePicker selected={selectedService} onSelect={setSelectedService} />
          </>
        )}

        {hasActivity && (
          <div className="w-full max-w-2xl mx-auto space-y-4">
            {currentQuery && (
              <div className="text-center">
                <p className="text-zinc-500 dark:text-zinc-400 text-sm">
                  {selectedService.label}
                </p>
                <p className="text-lg font-medium text-zinc-800 dark:text-zinc-200 mt-1">
                  "{currentQuery}"
                </p>
              </div>
            )}

            <div className="flex justify-center">
              <StatusIndicator status={status} />
            </div>

            {error && (
              <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 text-center">
                <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
              </div>
            )}

            {result && (
              <ResultCard result={result} amountMsats={payment?.amountMsats} />
            )}

            {(status === "completed" || status === "error") && (
              <div className="flex justify-center pt-4">
                <SearchBar
                  onSubmit={(q) => {
                    handleNewQuery();
                    setTimeout(() => handleSubmit(q), 50);
                  }}
                  placeholder="Ask something else..."
                />
              </div>
            )}
          </div>
        )}

        {payment && status === "payment_required" && (
          <PaymentModal payment={payment} onClose={handleNewQuery} />
        )}
      </div>

      <Footer />
    </div>
  );
}

export default App;
