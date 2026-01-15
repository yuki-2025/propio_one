"use client";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AnimatePresence, motion } from "framer-motion";
import { Send, Bot, User, Loader2, CheckCircle } from "lucide-react";
import { useState, useRef, useEffect, memo } from "react";
import ReactMarkdown from "react-markdown";

interface Message {
    id: string;
    role: "user" | "agent";
    content: string;
    timestamp: Date;
    actions?: string[]; // Step-by-step actions (thinking, etc.)
}

// Message content renderer - memoized to prevent re-renders on input change
const MessageContent = memo(function MessageContent({ content, isAgent }: { content: string; isAgent: boolean }) {
    if (!isAgent) {
        return <span>{content}</span>;
    }

    return (
        <div className="prose prose-sm prose-invert max-w-none">
            <ReactMarkdown
                components={{
                    // Style headings
                    h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2 text-foreground">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-semibold mt-4 mb-2 text-foreground">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-1.5 text-foreground">{children}</h3>,
                    // Style paragraphs
                    p: ({ children }) => <p className="mb-2 leading-relaxed text-foreground/90">{children}</p>,
                    // Style lists
                    ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                    li: ({ children }) => <li className="text-foreground/90">{children}</li>,
                    // Style bold and italic
                    strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                    em: ({ children }) => <em className="italic">{children}</em>,
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
});

export function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: "1",
            role: "agent",
            content: "Hello! I'm your AI Assistant. How can I help you today?",
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [threadId, setThreadId] = useState<string | null>(null);
    const scrollAreaRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        if (scrollAreaRef.current) {
            const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollContainer) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        }
    }, [messages]);

    const sampleQuestions = [
        "Hello!",
        "What can you do?",
        "Tell me a joke",
    ];

    const handleSend = async (text?: string) => {
        const messageContent = typeof text === 'string' ? text : input;
        if (!messageContent.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: messageContent,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);

        // Create a placeholder for the agent's response
        const agentMessageId = (Date.now() + 1).toString();
        const agentMessage: Message = {
            id: agentMessageId,
            role: "agent",
            content: "",
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, agentMessage]);

        try {
            console.log('[Chat] Sending request with thread_id:', threadId);
            const response = await fetch("http://localhost:8000/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    message: userMessage.content,
                    user_id: "1",
                    thread_id: threadId,
                }),
            });

            // Capture thread_id from response headers
            const newThreadId = response.headers.get('X-Thread-ID');
            if (newThreadId) {
                setThreadId(newThreadId);
            }

            if (!response.ok) {
                throw new Error("Failed to send message");
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) return;

            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                let eventEnd: number;
                while ((eventEnd = buffer.indexOf("\n\n")) !== -1) {
                    const eventData = buffer.slice(0, eventEnd);
                    buffer = buffer.slice(eventEnd + 2);

                    const lines = eventData.split("\n");
                    for (const line of lines) {
                        if (line.startsWith("data: ")) {
                            const data = line.slice(6);
                            if (data === "[DONE]") {
                                break;
                            } else if (data.startsWith("[ACTION]") && data.endsWith("[/ACTION]")) {
                                const action = data.slice(8, -9);
                                setMessages((prev) =>
                                    prev.map((msg) =>
                                        msg.id === agentMessageId
                                            ? { ...msg, actions: [...(msg.actions || []), action] }
                                            : msg
                                    )
                                );
                            } else if (data.startsWith("[ERROR:")) {
                                setMessages((prev) =>
                                    prev.map((msg) =>
                                        msg.id === agentMessageId
                                            ? { ...msg, content: msg.content + `\n⚠️ Error: ${data.slice(8, -1)}` }
                                            : msg
                                    )
                                );
                            } else if (data.startsWith("[TEXT]") && data.endsWith("[/TEXT]")) {
                                try {
                                    const jsonContent = data.slice(6, -7);
                                    const decodedContent = JSON.parse(jsonContent);
                                    setMessages((prev) =>
                                        prev.map((msg) =>
                                            msg.id === agentMessageId
                                                ? { ...msg, content: msg.content + decodedContent }
                                                : msg
                                        )
                                    );
                                } catch {
                                    setMessages((prev) =>
                                        prev.map((msg) =>
                                            msg.id === agentMessageId
                                                ? { ...msg, content: msg.content + data }
                                                : msg
                                        )
                                    );
                                }
                            } else {
                                // Legacy format
                                setMessages((prev) =>
                                    prev.map((msg) =>
                                        msg.id === agentMessageId
                                            ? { ...msg, content: msg.content + data }
                                            : msg
                                    )
                                );
                            }
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Error sending message:", error);
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.id === agentMessageId
                        ? { ...msg, content: msg.content + "\n⚠️ Sorry, something went wrong. Please try again." }
                        : msg
                )
            );
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card className="flex flex-col h-full bg-card border-border/50 shadow-sm">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Bot className="w-5 h-5 text-primary" />
                    AI Assistant
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden">
                <ScrollArea className="h-full p-4" ref={scrollAreaRef}>
                    <div className="space-y-4">
                        <AnimatePresence>
                            {messages.map((message) => (
                                <motion.div
                                    key={message.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    className={`flex items-start gap-3 ${message.role === "user" ? "flex-row-reverse" : ""
                                        }`}
                                >
                                    <Avatar className="w-8 h-8 border border-border/50">
                                        {message.role === "agent" ? (
                                            <AvatarFallback className="bg-primary/10 text-primary">AI</AvatarFallback>
                                        ) : (
                                            <AvatarFallback className="bg-secondary text-secondary-foreground">
                                                <User className="w-4 h-4" />
                                            </AvatarFallback>
                                        )}
                                    </Avatar>
                                    <div
                                        className={`rounded-lg p-3 max-w-[85%] text-sm overflow-hidden ${message.role === "user"
                                            ? "bg-primary text-primary-foreground"
                                            : "bg-muted/50 text-foreground border border-border/50"
                                            }`}
                                    >
                                        {/* Action steps - show progress */}
                                        {message.role === "agent" && message.actions && message.actions.length > 0 && (
                                            <div className="mb-2 pb-2 border-b border-border/30 space-y-1">
                                                {message.actions.map((action, idx) => {
                                                    const isLast = idx === message.actions!.length - 1;
                                                    const actionLabels: Record<string, string> = {
                                                        'thinking': 'Thinking...',
                                                    };
                                                    const label = actionLabels[action] || action;
                                                    const isComplete = !isLoading || !isLast;

                                                    return (
                                                        <div key={idx} className="flex items-center gap-2 text-xs text-cyan-400">
                                                            {isComplete ? (
                                                                <CheckCircle className="w-3 h-3" />
                                                            ) : (
                                                                <Loader2 className="w-3 h-3 animate-spin" />
                                                            )}
                                                            <span className={isComplete ? "text-cyan-400/70" : "font-medium"}>
                                                                {label}
                                                            </span>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                        {message.role === "agent" && message.content === "" && isLoading ? (
                                            <span className="flex items-center gap-1">
                                                <span className="w-1.5 h-1.5 bg-foreground/50 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                                <span className="w-1.5 h-1.5 bg-foreground/50 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                                <span className="w-1.5 h-1.5 bg-foreground/50 rounded-full animate-bounce" />
                                            </span>
                                        ) : (
                                            <MessageContent content={message.content} isAgent={message.role === "agent"} />
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </ScrollArea>
            </CardContent>
            <CardFooter className="flex-col gap-4 p-4 pt-0">
                <div className="flex flex-wrap gap-2 w-full">
                    {sampleQuestions.map((q, i) => (
                        <Button
                            key={i}
                            variant="outline"
                            size="sm"
                            className="text-xs h-auto py-1.5 bg-background/50"
                            onClick={() => handleSend(q)}
                            disabled={isLoading}
                        >
                            {q}
                        </Button>
                    ))}
                </div>
                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        handleSend();
                    }}
                    className="flex w-full gap-2"
                >
                    <Input
                        placeholder="Type your message..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        className="bg-background/50 border-border/50 focus-visible:ring-primary"
                        disabled={isLoading}
                    />
                    <Button type="submit" size="icon" disabled={!input.trim() || isLoading}>
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        <span className="sr-only">Send</span>
                    </Button>
                </form>
            </CardFooter>
        </Card>
    );
}
