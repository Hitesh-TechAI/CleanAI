import { Send } from "lucide-react";
import { useState, useRef, useEffect } from "react";

type Message = {
  role: "user" | "ai";
  text: string;
};

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const ThinkingIndicator = () => (
  <div className="flex justify-start animate-fade-in">
    <div className="bg-secondary text-secondary-foreground glow-card rounded-xl px-4 py-3 flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full bg-primary animate-bounce" />
      <span
        className="w-2 h-2 rounded-full bg-primary animate-bounce"
        style={{ animationDelay: "150ms" }}
      />
      <span
        className="w-2 h-2 rounded-full bg-primary animate-bounce"
        style={{ animationDelay: "300ms" }}
      />
    </div>
  </div>
);

const ChatInterface = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  // ✅ Always scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  const handleSend = async () => {
    if (!input.trim() || isThinking) return;

    const userMessage = input.trim();

    setMessages((prev) => [
      ...prev,
      { role: "user", text: userMessage },
    ]);

    setInput("");
    setIsThinking(true);

    try {
      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      let aiMessage = "No response generated.";

      if (data?.message) {
        aiMessage = data.message;
      } else if (data?.error) {
        aiMessage = `⚠ ${data.error}`;
      } else {
        aiMessage = JSON.stringify(data, null, 2);
      }

      setMessages((prev) => [
        ...prev,
        { role: "ai", text: aiMessage },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: "⚠ Backend connection failed or server error occurred.",
        },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="glass rounded-lg gradient-border flex flex-col h-full min-h-[500px]">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border">
        <h2 className="text-sm font-semibold text-foreground">
          AI Chat Assistant
        </h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Ask me to clean, transform, or analyze your data
        </p>
      </div>

      {/* Messages Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 flex flex-col justify-end"
      >
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${
                msg.role === "user"
                  ? "justify-end"
                  : "justify-start"
              } animate-fade-in`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "ai"
                    ? "bg-secondary text-secondary-foreground glow-card"
                    : "bg-primary text-primary-foreground"
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          {isThinking && <ThinkingIndicator />}
        </div>
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            disabled={isThinking}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && handleSend()
            }
            placeholder="Ask CleanAI to clean your data..."
            className="flex-1 bg-secondary rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 transition-shadow"
          />
          <button
            onClick={handleSend}
            disabled={isThinking}
            className="bg-primary text-primary-foreground rounded-lg px-4 py-2.5 hover:opacity-90 transition-opacity flex items-center gap-2 text-sm font-medium disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;