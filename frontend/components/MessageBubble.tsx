"use client"

import { Message } from "@/types"
import { cn } from "@/lib/utils"
import { ShlokaCard } from "./ShlokaCard"
import { User, Sparkles } from "lucide-react"
import { motion } from "framer-motion"

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user"

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "flex w-full gap-4 p-4 md:p-6",
        isUser ? "bg-background" : "bg-muted/30"
      )}
    >
      <div className="flex-shrink-0">
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full border shadow-sm",
            isUser
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-amber-100 border-amber-200 text-amber-700 dark:bg-amber-900/50 dark:border-amber-800 dark:text-amber-400"
          )}
        >
          {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
        </div>
      </div>

      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="font-semibold text-sm text-muted-foreground flex items-center gap-2">
          {isUser ? "You" : "Krishna"}
        </div>
        
        <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-relaxed">
          {message.content.split('\n').map((paragraph, i) => (
            paragraph.trim() ? <p key={i} className="mb-2 last:mb-0">{paragraph}</p> : <br key={i} />
          ))}
        </div>

        {/* Display source citations if any */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-4 pt-2">
            {message.sources.map((source, i) => (
              <ShlokaCard key={i} source={source} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
