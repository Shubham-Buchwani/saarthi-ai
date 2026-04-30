"use client"
import * as React from "react"
import { useAuth, API_URL } from "../lib/auth"
import { Sidebar } from "@/components/Sidebar"
import { ChatWindow } from "@/components/ChatWindow"
import { Message } from "@/types"
import { useRouter } from "next/navigation"
import { Menu, X } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

export default function Home() {
  const { user, token, logout, loading } = useAuth()
  const router = useRouter()
  const [messages, setMessages] = React.useState<Message[]>([])
  const [isLoading, setIsLoading] = React.useState(false)
  const [sessionId, setSessionId] = React.useState("")
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false)

  React.useEffect(() => {
    if (!sessionId) {
      setSessionId(Math.random().toString(36).substring(2, 15))
    }
  }, [sessionId])

  const handleNewChat = () => {
    setMessages([])
    setSessionId(Math.random().toString(36).substring(2, 15))
    setIsSidebarOpen(false)
  }

  const handleSendMessage = async (content: string, language: string) => {
    if (!token) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ message: content, session_id: sessionId, language }),
      })

      if (!response.ok) throw new Error("API responded with an error")
      
      const reader = response.body?.getReader()
      if (!reader) throw new Error("Could not read response stream")

      const krishnaMsgId = (Date.now() + 1).toString()
      const initialKrishnaMsg: Message = {
        id: krishnaMsgId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, initialKrishnaMsg])

      const decoder = new TextDecoder()
      let accumulatedContent = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split("\n")
        
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith("data: ")) continue
          
          try {
            const data = JSON.parse(trimmed.slice(6))
            
            if (data.text) {
              accumulatedContent += data.text
              setMessages((prev) => 
                prev.map(m => m.id === krishnaMsgId ? { ...m, content: accumulatedContent } : m)
              )
            }
            
            if (data.sources) {
              setMessages((prev) => 
                prev.map(m => m.id === krishnaMsgId ? { ...m, sources: data.sources } : m)
              )
            }

            if (data.session_id && !sessionId) {
              setSessionId(data.session_id)
            }

            if (data.error) {
              throw new Error(data.error)
            }
          } catch (e) {
            console.error("Error parsing stream chunk:", e)
          }
        }
      }
      
    } catch (error) {
      console.error("Chat error:", error)
      const errorMsg: Message = {
        id: (Date.now() + 2).toString(),
        role: "assistant",
        content: "I am having trouble connecting right now, Parth. Please try sharing that with me again in a moment.",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  const handleChatSelect = async (chatId: string) => {
    if (!token) return
    setIsLoading(true)
    setIsSidebarOpen(false)
    try {
      const res = await fetch(`${API_URL}/api/chats/${chatId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error("Failed to fetch chat messages")
      
      const data = await res.json()
      
      const mappedMessages: Message[] = data.map((m: any) => ({
        id: m.id?.toString() || Math.random().toString(36).substring(7),
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at)
      }))

      setMessages(mappedMessages)
      setSessionId(chatId)
    } catch (error) {
      console.error("Error loading chat:", error)
    } finally {
      setIsLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-background text-center">
        <div className="space-y-4">
          <div className="text-4xl">🕉️</div>
          <div className="text-[#b8860b] animate-pulse font-serif text-xl italic">
            Preparing your journey with Saarthi AI...
          </div>
        </div>
      </div>
    )
  }


  return (
    <main className="flex h-screen w-full overflow-hidden bg-background font-sans text-foreground relative">
      <AnimatePresence>
        {isSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsSidebarOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 w-72 z-50 md:hidden"
            >
              <Sidebar 
                onNewChat={handleNewChat} 
                onChatSelect={handleChatSelect}
                onClose={() => setIsSidebarOpen(false)}
                className="w-full" 
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <Sidebar 
        onNewChat={handleNewChat} 
        onChatSelect={handleChatSelect}
        className="hidden md:flex" 
      />

      <div className="flex-1 flex flex-col min-w-0 relative">
        <header className="md:hidden flex h-14 items-center justify-between px-4 border-b border-[#b8860b]/10 bg-background/80 backdrop-blur-md sticky top-0 z-30">
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="h-9 w-9 flex items-center justify-center text-[#b8860b] hover:bg-[#b8860b]/10 rounded-lg transition-colors border border-[#b8860b]/20"
          >
            <Menu className="h-5 w-5" />
          </button>
          
          <div className="font-serif font-bold text-[#b8860b] text-sm">
             Saarthi AI
          </div>
          
          <div className="w-9" />
        </header>

        <ChatWindow 
          messages={messages} 
          isLoading={isLoading} 
          onSendMessage={handleSendMessage} 
        />
      </div>
    </main>
  )
}

