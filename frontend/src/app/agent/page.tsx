import { ChatInterface } from "@/components/chat/chat-interface";
import { ModeToggle } from "@/components/mode-toggle";

export default function AgentPage() {
    return (
        <main className="min-h-screen p-8 space-y-8">
            <header className="flex items-center justify-between mb-4">
                <div>
                    <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">
                        Conversational Analytics Agent
                    </h1>
                    <p className="text-muted-foreground mt-2">
                        Real-time monitoring and AI-assisted analysis
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    <ModeToggle />
                    <div className="flex items-center gap-2 px-4 py-2 bg-card/50 rounded-full border border-border/50">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-sm font-medium">System Online</span>
                    </div>
                </div>
            </header>

            <div className="h-[calc(100vh-12rem)]">
                <ChatInterface />
            </div>
        </main>
    );
}
