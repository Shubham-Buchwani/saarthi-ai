"use client"

import * as React from "react"
import { Message } from "@/types"
import { MessageBubble } from "./MessageBubble"
import { Textarea } from "./ui/textarea"
import { Button } from "./ui/button"
import { SendHorizontal, Loader2, ChevronDown, Sparkles } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

export function ChatWindow({
  messages,
  isLoading,
  onSendMessage,
}: {
  messages: Message[]
  isLoading: boolean
  onSendMessage: (msg: string, language: string) => void
}) {
  const [input, setInput] = React.useState("")
  const [language, setLanguage] = React.useState("auto")
  const [isLangMenuOpen, setIsLangMenuOpen] = React.useState(false)
  const scrollRef = React.useRef<HTMLDivElement>(null)

  const languages = [
    { id: "auto", label: "Hindi + English" },
    { id: "english", label: "English Only" },
    { id: "hindi", label: "Hindi Only" },
    { id: "sanskrit", label: "Sanskrit" },
    { id: "marathi", label: "Marathi" },
    { id: "gujarati", label: "Gujarati" },
    { id: "telugu", label: "Telugu" },
    { id: "tamil", label: "Tamil" },
    { id: "kannada", label: "Kannada" },
    { id: "malayalam", label: "Malayalam" },
  ]

  const currentLang = languages.find(l => l.id === language) || languages[0]

  // Auto-scroll to bottom
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    onSendMessage(input, language)
    setInput("")
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full bg-background relative" onClick={() => setIsLangMenuOpen(false)}>
      {/* Messages Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto w-full pb-64 md:pb-56"
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
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background via-background to-transparent pt-8 pb-4 md:pt-10 md:pb-6 px-4">
        <div className="max-w-3xl mx-auto relative group">
          <form 
            onSubmit={handleSubmit}
            className="relative flex flex-col w-full rounded-2xl border border-[#b8860b]/20 bg-background/80 backdrop-blur-sm shadow-lg focus-within:ring-1 focus-within:ring-[#b8860b]/30 transition-all duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Share what's troubling you..."
              className="min-h-[56px] w-full resize-none border-0 bg-transparent pt-4 pb-2 px-4 focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none text-[15px] placeholder:text-muted-foreground/50"
              rows={1}
            />
            
            <div className="flex items-center justify-between px-3 pb-2 pt-1 w-full relative">
              {/* Custom Language Selector */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setIsLangMenuOpen(!isLangMenuOpen)}
                  className="flex items-center gap-2 text-xs font-medium bg-amber-50 dark:bg-amber-900/20 hover:bg-amber-100 dark:hover:bg-amber-900/40 text-[#b8860b] rounded-lg px-3 py-1.5 border border-[#b8860b]/20 transition-all active:scale-95"
                >
                  <Sparkles className="h-3 w-3" />
                  <span>{currentLang.label}</span>
                  <ChevronDown className={`h-3 w-3 transition-transform duration-200 ${isLangMenuOpen ? 'rotate-180' : ''}`} />
                </button>

                <AnimatePresence>
                  {isLangMenuOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: -8, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      className="absolute bottom-full left-0 mb-2 w-48 bg-white dark:bg-[#1a1a1a] border border-[#b8860b]/20 rounded-xl shadow-2xl overflow-hidden z-50 p-1"
                    >
                      {languages.map((lang) => (
                        <button
                          key={lang.id}
                          type="button"
                          onClick={() => {
                            setLanguage(lang.id)
                            setIsLangMenuOpen(false)
                          }}
                          className={`w-full flex items-center gap-3 px-3 py-2 text-sm rounded-lg transition-colors ${
                            language === lang.id 
                              ? 'bg-amber-50 dark:bg-amber-900/30 text-[#b8860b]' 
                              : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                          }`}
                        >
                          <span className="flex-1 text-left font-medium">{lang.label}</span>
                          {language === lang.id && (
                             <div className="h-1.5 w-1.5 rounded-full bg-[#b8860b]" />
                          )}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <Button 
                type="submit" 
                disabled={!input.trim() || isLoading}
                className="h-9 w-9 p-0 rounded-xl bg-[#b8860b] hover:bg-[#a67a0a] text-white shadow-md transition-all active:scale-90 disabled:bg-muted disabled:text-muted-foreground ml-2 shrink-0"
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
