"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, MessageSquare, User } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

const navigation = [
    { name: "Agent", href: "/agent", icon: MessageSquare },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="flex flex-col w-64 bg-sidebar/50 backdrop-blur-xl border-r border-sidebar-border h-screen fixed left-0 top-0 z-50">
            <div className="p-6 flex items-center gap-3">
                <Avatar className="h-10 w-10 border border-primary/20">
                    <AvatarFallback className="bg-primary/20 text-primary">AD</AvatarFallback>
                </Avatar>
                <div className="flex flex-col">
                    <span className="text-sm font-semibold">Agent Admin</span>
                    <span className="text-xs text-muted-foreground">Admin</span>
                </div>
            </div>

            <nav className="flex-1 px-4 space-y-2 mt-4">
                {navigation.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${isActive
                                ? "bg-primary/10 text-primary"
                                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                                }`}
                        >
                            <item.icon className="w-5 h-5" />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-4 border-t border-border/50">
                <div className="text-xs text-center text-muted-foreground">
                    Powered by Analytics Agent
                </div>
            </div>
        </div>
    );
}
