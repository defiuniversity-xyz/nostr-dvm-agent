import { DVM_SERVICES, type DVMService } from "../lib/types";

interface ServicePickerProps {
  selected: DVMService;
  onSelect: (service: DVMService) => void;
}

export function ServicePicker({ selected, onSelect }: ServicePickerProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2 mt-4">
      {DVM_SERVICES.map((service) => (
        <button
          key={service.name}
          onClick={() => onSelect(service)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
            selected.name === service.name
              ? "bg-amber-500 text-white shadow-md"
              : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700"
          }`}
        >
          {service.label}
        </button>
      ))}
    </div>
  );
}
