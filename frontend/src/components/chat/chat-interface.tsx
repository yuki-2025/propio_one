"use client";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AnimatePresence, motion } from "framer-motion";
import { Send, Bot, User, Loader2, Mic, MicOff, Phone, PhoneOff } from "lucide-react";
import { useState, useRef, useEffect, memo } from "react";
import ReactMarkdown from "react-markdown";

interface Message {
    id: string;
    role: "user" | "agent";
    content: string;
    timestamp: Date;
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
                    h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2 text-foreground">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-semibold mt-4 mb-2 text-foreground">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-1.5 text-foreground">{children}</h3>,
                    p: ({ children }) => <p className="mb-2 leading-relaxed text-foreground/90">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                    li: ({ children }) => <li className="text-foreground/90">{children}</li>,
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
            content: "Hello! I'm your AI Assistant. Click the phone button to start a voice conversation, or type your message below.",
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const scrollAreaRef = useRef<HTMLDivElement>(null);

    // Voice chat state
    const [isVoiceActive, setIsVoiceActive] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [audioLevel, setAudioLevel] = useState(0);

    // Voice chat refs
    const wsRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const processorRef = useRef<ScriptProcessorNode | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const isRecordingRef = useRef(false);

    // Audio playback refs
    const playbackContextRef = useRef<AudioContext | null>(null);
    const audioQueueRef = useRef<AudioBuffer[]>([]);
    const isPlayingRef = useRef(false);
    const nextPlayTimeRef = useRef(0);

    // Transcript handling
    const currentAgentMessageIdRef = useRef<string | null>(null);
    const shouldClearAgentTranscriptRef = useRef(false);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        if (scrollAreaRef.current) {
            const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollContainer) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        }
    }, [messages]);

    /**
     * Play audio from base64 PCM16 data
     */
    const playAudio = async (base64Audio: string) => {
        try {
            // Create new AudioContext if needed or if previous was closed
            if (!playbackContextRef.current || playbackContextRef.current.state === 'closed') {
                playbackContextRef.current = new AudioContext({ sampleRate: 24000 });
                nextPlayTimeRef.current = 0;  // Reset timing for new context
                console.log('🎵 New AudioContext created');
            }

            // Resume context if suspended (browser autoplay policy)
            if (playbackContextRef.current.state === 'suspended') {
                await playbackContextRef.current.resume();
            }

            // Decode base64 → PCM16 → Float32
            const binaryString = atob(base64Audio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            const pcm16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(pcm16.length);
            for (let i = 0; i < pcm16.length; i++) {
                float32[i] = pcm16[i] / (pcm16[i] < 0 ? 0x8000 : 0x7FFF);
            }

            const audioBuffer = playbackContextRef.current.createBuffer(1, float32.length, 24000);
            audioBuffer.getChannelData(0).set(float32);

            audioQueueRef.current.push(audioBuffer);

            if (!isPlayingRef.current) {
                isPlayingRef.current = true;
                playNextInQueue();
            }
        } catch (err) {
            console.error('❌ Audio play error:', err);
        }
    };

    /**
     * Play next audio buffer from queue (seamless playback)
     */
    const playNextInQueue = () => {
        if (audioQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            nextPlayTimeRef.current = 0;
            return;
        }

        const ctx = playbackContextRef.current!;
        const currentTime = ctx.currentTime;

        if (nextPlayTimeRef.current < currentTime) {
            nextPlayTimeRef.current = currentTime;
        }

        const buffer = audioQueueRef.current.shift()!;
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(ctx.destination);
        source.start(nextPlayTimeRef.current);

        nextPlayTimeRef.current += buffer.duration;

        source.onended = () => {
            // Continue to next if available
        };

        if (audioQueueRef.current.length > 0) {
            playNextInQueue();
        } else {
            isPlayingRef.current = false;
        }
    };

    /**
     * Start voice chat session
     */
    const startVoiceChat = async () => {
        console.log('📞 Starting voice chat...');
        setIsVoiceActive(true);

        try {
            // Connect WebSocket
            const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws');
            wsRef.current = ws;

            ws.onopen = async () => {
                console.log('✅ WebSocket connected');
                setIsConnected(true);

                // Start recording
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        audio: { sampleRate: 24000, channelCount: 1 }
                    });
                    streamRef.current = stream;

                    const audioContext = new AudioContext({ sampleRate: 24000 });
                    audioContextRef.current = audioContext;

                    const source = audioContext.createMediaStreamSource(stream);
                    sourceRef.current = source;

                    const processor = audioContext.createScriptProcessor(4096, 1, 1);
                    processorRef.current = processor;

                    processor.onaudioprocess = (e) => {
                        if (!isRecordingRef.current || !ws || ws.readyState !== WebSocket.OPEN) return;

                        const input = e.inputBuffer.getChannelData(0);

                        // Convert to PCM16
                        const pcm = new Int16Array(input.length);
                        for (let i = 0; i < input.length; i++) {
                            const s = Math.max(-1, Math.min(1, input[i]));
                            pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                        }

                        // Send to backend
                        ws.send(JSON.stringify({
                            type: 'audio_chunk',
                            data: btoa(String.fromCharCode(...new Uint8Array(pcm.buffer)))
                        }));

                        // Update audio level for visual feedback
                        let sum = 0;
                        for (let i = 0; i < input.length; i++) {
                            sum += input[i] * input[i];
                        }
                        const rms = Math.sqrt(sum / input.length);
                        const level = Math.min(100, Math.floor(rms * 100 * 10));
                        setAudioLevel(level);
                    };

                    source.connect(processor);
                    processor.connect(audioContext.destination);

                    isRecordingRef.current = true;
                    setIsRecording(true);
                    console.log('✅ Recording started');

                } catch (err: any) {
                    console.error('❌ Microphone error:', err);
                    alert('Cannot access microphone: ' + (err.message || ''));
                    stopVoiceChat();
                }
            };

            ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                alert('Connection failed');
                stopVoiceChat();
            };

            ws.onclose = () => {
                console.log('🔌 WebSocket closed');
                setIsConnected(false);
                if (isVoiceActive) {
                    stopVoiceChat();
                }
            };

            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    console.log('📨 Received:', data.type);

                    switch (data.type) {
                        case 'connection_established':
                            console.log('✅ Session established');
                            break;

                        case 'user_transcript':
                            // Add user message to chat
                            const userMessage: Message = {
                                id: Date.now().toString(),
                                role: 'user',
                                content: data.text,
                                timestamp: new Date(),
                            };
                            setMessages(prev => [...prev, userMessage]);
                            // Prepare for new agent response
                            shouldClearAgentTranscriptRef.current = true;
                            break;

                        case 'agent_transcript_delta':
                            // Create or update agent message
                            if (shouldClearAgentTranscriptRef.current || !currentAgentMessageIdRef.current) {
                                const newId = (Date.now() + 1).toString();
                                currentAgentMessageIdRef.current = newId;
                                const newAgentMessage: Message = {
                                    id: newId,
                                    role: 'agent',
                                    content: data.text,
                                    timestamp: new Date(),
                                };
                                setMessages(prev => [...prev, newAgentMessage]);
                                shouldClearAgentTranscriptRef.current = false;
                            } else {
                                setMessages(prev =>
                                    prev.map(msg =>
                                        msg.id === currentAgentMessageIdRef.current
                                            ? { ...msg, content: msg.content + data.text }
                                            : msg
                                    )
                                );
                            }
                            break;

                        case 'agent_transcript_complete':
                            console.log('✅ Agent transcript complete');
                            shouldClearAgentTranscriptRef.current = true;
                            currentAgentMessageIdRef.current = null;
                            break;

                        case 'audio_delta':
                            if (data.audio) {
                                playAudio(data.audio);
                            }
                            break;

                        case 'error':
                            console.error('❌ Error:', data.message);
                            const errorMessage: Message = {
                                id: Date.now().toString(),
                                role: 'agent',
                                content: `⚠️ Error: ${data.message}`,
                                timestamp: new Date(),
                            };
                            setMessages(prev => [...prev, errorMessage]);
                            break;
                    }
                } catch (err) {
                    console.error('❌ Failed to parse message:', err);
                }
            };

        } catch (error: any) {
            console.error('❌ Failed to start voice chat:', error);
            alert('Cannot start voice chat: ' + (error.message || ''));
            setIsVoiceActive(false);
        }
    };

    /**
     * Stop voice chat session
     */
    const stopVoiceChat = () => {
        console.log('🛑 Stopping voice chat...');

        isRecordingRef.current = false;
        setIsRecording(false);

        // Notify backend
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'audio_complete' }));
        }

        // Clean up audio resources
        if (processorRef.current) {
            processorRef.current.disconnect();
            processorRef.current = null;
        }
        if (sourceRef.current) {
            sourceRef.current.disconnect();
            sourceRef.current = null;
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }

        // Clean up playback
        audioQueueRef.current = [];
        isPlayingRef.current = false;
        if (playbackContextRef.current) {
            playbackContextRef.current.close();
            playbackContextRef.current = null;
        }

        // Close WebSocket
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        // Reset state
        setIsVoiceActive(false);
        setAudioLevel(0);
        setIsConnected(false);
        shouldClearAgentTranscriptRef.current = false;
        currentAgentMessageIdRef.current = null;

        console.log('✅ Voice chat stopped');
    };

    /**
     * Handle text message send (original functionality)
     */
    const handleSend = async (text?: string) => {
        const messageContent = typeof text === 'string' ? text : input;
        if (!messageContent.trim() || isLoading || isVoiceActive) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: messageContent,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);

        // For now, just show a message that text input is disabled during voice mode
        // In the future, you could add HTTP streaming back
        const agentMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: "agent",
            content: "Text chat is currently disabled. Please use the voice button to start a conversation.",
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, agentMessage]);
        setIsLoading(false);
    };

    return (
        <Card className="flex flex-col h-full bg-card border-border/50 shadow-sm">
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Bot className="w-5 h-5 text-primary" />
                        AI Voice Assistant
                    </div>
                    <div className="flex items-center gap-2">
                        {isVoiceActive && (
                            <div className="flex items-center gap-2 px-3 py-1 bg-green-500/20 rounded-full">
                                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                <span className="text-xs text-green-500">Connected</span>
                            </div>
                        )}
                    </div>
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
                                        <MessageContent content={message.content} isAgent={message.role === "agent"} />
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </ScrollArea>
            </CardContent>
            <CardFooter className="flex-col gap-4 p-4 pt-0">
                {/* Audio level indicator when recording */}
                {isVoiceActive && isRecording && (
                    <div className="w-full flex items-center gap-2">
                        <Mic className="w-4 h-4 text-red-500 animate-pulse" />
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-green-500 to-red-500 transition-all duration-100"
                                style={{ width: `${audioLevel}%` }}
                            />
                        </div>
                        <span className="text-xs text-muted-foreground">Listening...</span>
                    </div>
                )}

                {/* Voice control button */}
                <div className="flex w-full gap-2">
                    <Button
                        variant={isVoiceActive ? "destructive" : "default"}
                        size="lg"
                        className="flex-1 gap-2"
                        onClick={isVoiceActive ? stopVoiceChat : startVoiceChat}
                    >
                        {isVoiceActive ? (
                            <>
                                <PhoneOff className="w-5 h-5" />
                                End Voice Chat
                            </>
                        ) : (
                            <>
                                <Phone className="w-5 h-5" />
                                Start Voice Chat
                            </>
                        )}
                    </Button>
                </div>

                {/* Text input (disabled during voice mode) */}
                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        handleSend();
                    }}
                    className="flex w-full gap-2"
                >
                    <Input
                        placeholder={isVoiceActive ? "Voice mode active..." : "Type your message..."}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        className="bg-background/50 border-border/50 focus-visible:ring-primary"
                        disabled={isLoading || isVoiceActive}
                    />
                    <Button type="submit" size="icon" disabled={!input.trim() || isLoading || isVoiceActive}>
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        <span className="sr-only">Send</span>
                    </Button>
                </form>
            </CardFooter>
        </Card>
    );
}
