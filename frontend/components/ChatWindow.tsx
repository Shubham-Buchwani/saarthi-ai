"use client"

import * as React from "react"
import { Message } from "@/types"
import { MessageBubble } from "./MessageBubble"
import { Textarea } from "./ui/textarea"
import { Button } from "./ui/button"
import { SendHorizontal, Loader2 } from "lucide-react"

export function ChatWindow({
  messages,
  isLoading,
  onSendMessage,
}: {
  messages: Message[]
  isLoading: boolean
  onSendMessage: (msg: string) => void
}) {
  const [input, setInput] = React.useState("")
  const scrollRef = React.useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    onSendMessage(input)
    setInput("")
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full bg-background relative">
      {/* Messages Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto w-full pb-32"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-700">
            <div className="h-16 w-16 mb-6 rounded-full bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center border border-amber-200 dark:border-amber-800">
              {isLoading ? <Loader2 className="h-7 w-7 animate-spin text-amber-600" /> : <span className="text-3xl">🦚</span>}
            </div>
            {isLoading ? (
              <>
                <h2 className="text-2xl font-semibold mb-2">Krishna is reflecting...</h2>
                <p className="text-muted-foreground max-w-md">Seeking wisdom from the Gita for you...</p>
              </>
            ) : (
              <>
                <h2 className="text-2xl font-semibold mb-2">How can I guide you today?</h2>
                <p className="text-muted-foreground max-w-md">
                  Share what's on your mind. I am here to listen and offer perspective from the wisdom of the Gita.
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="max-w-3xl mx-auto w-full divide-y">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && (
              <div className="p-6 flex items-center gap-3 text-muted-foreground animate-pulse">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Krishna is reflecting...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input Area (Claude style - floating at bottom) */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background via-background to-transparent pt-10 pb-6 px-4">
        <div className="max-w-3xl mx-auto relative group">
          <form 
            onSubmit={handleSubmit}
            className="relative flex items-end w-full overflow-hidden rounded-2xl border bg-background shadow-sm focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all duration-200"
          >
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Share what's troubling you..."
              className="min-h-[56px] w-full resize-none border-0 bg-transparent py-[18px] pr-14 pl-4 focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none text-[15px]"
              rows={1}
            />
            <div className="absolute right-2 bottom-2">
              <Button 
                type="submit" 
                disabled={!input.trim() || isLoading}
                className="h-10 w-10 p-0 rounded-xl bg-primary text-primary-foreground shadow-sm transition-transform active:scale-95 disabled:bg-muted disabled:text-muted-foreground"
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
              </Button>
            </div>
          </form>
          <div className="text-center mt-2 text-[11px] text-muted-foreground/60">
            For severe emotional distress, please seek professional help immediately.
          </div>
        </div>
      </div>
    </div>
  )
}
