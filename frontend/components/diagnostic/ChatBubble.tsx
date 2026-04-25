interface ChatBubbleProps {
  role: "assistant" | "user";
  text: string;
}

export function ChatBubble({ role, text }: ChatBubbleProps) {
  const isAssistant = role === "assistant";

  return (
    <div
      className={`flex gap-3 animate-fade-in ${isAssistant ? "" : "flex-row-reverse"}`}
    >
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
          isAssistant
            ? "bg-indigo-600 text-white shadow-sm shadow-indigo-950/60"
            : "bg-slate-700 text-slate-300"
        }`}
      >
        {isAssistant ? "B" : "V"}
      </div>

      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isAssistant
            ? "rounded-tl-sm bg-slate-800/80 text-slate-200"
            : "rounded-tr-sm border border-indigo-500/20 bg-indigo-600/15 text-indigo-100"
        }`}
      >
        {text}
      </div>
    </div>
  );
}
