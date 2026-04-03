"use client"
import * as React from "react"
import { useAuth, API_URL } from "../lib/auth"
import { Sidebar } from "@/components/Sidebar"
import { ChatWindow } from "@/components/ChatWindow"
import { Message } from "@/types"
import { useRouter } from "next/navigation"



export default function Home() {
  const { user, token, logout, loading } = useAuth()
  const router = useRouter()
  const [messages, setMessages] = React.useState<Message[]>([])
  const [isLoading, setIsLoading] = React.useState(false)
  const [sessionId, setSessionId] = React.useState("")

  // Auth checking is now disabled to allow Guest access.
  // React.useEffect(() => {
  //   if (!loading && !user) {
  //     router.push("/login")
  //   }
  // }, [user, loading, router])


  React.useEffect(() => {
    // Generate a unique session ID on mount if not already set
    if (!sessionId) {
      setSessionId(Math.random().toString(36).substring(2, 15))
    }
  }, [sessionId])

  const handleNewChat = () => {
    setMessages([])
    setSessionId(Math.random().toString(36).substring(2, 15))
  }

  const handleSendMessage = async (content: string) => {
    if (!token) return

    // 1. Add user message to UI
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    // 2. Fetch from backend with Token
    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ message: content, session_id: sessionId }),
      })

      if (!res.ok) throw new Error("API responded with an error")
      
      const data = await res.json()

      // 3. Add Krishna's response to UI
      const krishnaMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.reply,
        sources: data.sources,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, krishnaMsg])
      
    } catch (error) {
      console.error("Chat error:", error)
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I am having trouble connecting right now. Please try sharing that with me again in a moment.",
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
    try {
      const res = await fetch(`${API_URL}/api/chats/${chatId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error("Failed to fetch chat messages")
      
      const data = await res.json()
      
      // Map database messages to UI Message type
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
    <main className="flex h-screen w-full overflow-hidden bg-background font-sans text-foreground">
      {/* Desktop Sidebar */}
      <Sidebar 
        onNewChat={handleNewChat} 
        onChatSelect={handleChatSelect}
        className="hidden md:flex" 
      />


      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatWindow 
          messages={messages} 
          isLoading={isLoading} 
          onSendMessage={handleSendMessage} 
        />
      </div>
    </main>
  )
}
