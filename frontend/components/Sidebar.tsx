"use client"

import React, { useEffect, useState } from "react"
import { Button } from "./ui/button"
import { Menu, Plus, MessageSquare, LogOut, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth, API_URL } from "@/lib/auth"



interface ChatInfo {
  id: string
  title: string
  last_active: string
}

export function Sidebar({
  className,
  onNewChat,
  onChatSelect,
}: {
  className?: string
  onNewChat: () => void
  onChatSelect?: (chatId: string) => void
}) {

  const { token } = useAuth()
  const [history, setHistory] = useState<ChatInfo[]>([])

  useEffect(() => {
    if (token) {
      fetchHistory()
    }
  }, [token])

  const fetchHistory = async () => {
    try {
      const resp = await fetch(`${API_URL}/api/chats`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setHistory(data)
      }
    } catch (err) {
      console.error("Failed to fetch history:", err)
    }
  }

  return (
    <div className={cn("flex h-full w-72 flex-col bg-[#121212] border-r border-[#b8860b]/20", className)}>
      <div className="flex h-16 items-center justify-between px-4 border-b border-[#b8860b]/10">
        <div className="font-serif font-bold text-[#b8860b] flex items-center gap-2">
          <span className="text-2xl">🦚</span> Saarthi AI
        </div>
      </div>
      
      <div className="p-4">
        <Button
          onClick={onNewChat}
          className="w-full justify-start gap-2 bg-[#b8860b]/10 hover:bg-[#b8860b]/20 text-[#b8860b] border border-[#b8860b]/30 shadow-sm transition-all duration-300"
        >
          <Plus className="h-4 w-4" />
          Seek New Guidance
        </Button>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        <div>
          <div className="text-[10px] font-bold tracking-widest text-[#b8860b]/50 mb-4 uppercase">Your Journey So Far</div>
          
          <div className="space-y-2">
            {history.length > 0 ? (
              history.map((chat) => (
                <Button 
                  key={chat.id}
                  variant="ghost"
                  onClick={() => onChatSelect?.(chat.id)}
                  className="w-full justify-start gap-3 h-11 px-3 text-gray-400 hover:text-[#b8860b] hover:bg-[#b8860b]/5 border-0 shadow-none transition-colors duration-200 group"
                >
                  <MessageSquare className="h-4 w-4 shrink-0 opacity-40 group-hover:opacity-100" />
                  <span className="truncate text-sm font-medium">{chat.title}</span>
                </Button>
              ))
            ) : (
              <p className="text-xs text-gray-600 px-3 italic">No past conversations yet.</p>
            )}
          </div>
        </div>
      </div>

      {/* User Section (Removed for Guest Mode) */}


      <div className="p-3 text-[10px] text-[#b8860b]/30 text-center font-serif italic">
        "Peace resides within."
      </div>
    </div>
  )
}
