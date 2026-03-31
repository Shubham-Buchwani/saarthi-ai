"use client"

import { ShlokaSource } from "@/types"
import { motion } from "framer-motion"
import { BookOpen } from "lucide-react"

export function ShlokaCard({ source }: { source: ShlokaSource }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 mb-2 overflow-hidden rounded-xl border border-amber-900/20 bg-amber-50/50 p-4 shadow-sm dark:border-amber-700/30 dark:bg-amber-950/20"
    >
      <div className="flex items-center gap-2 mb-3 border-b border-amber-900/10 pb-2 dark:border-amber-700/20">
        <BookOpen className="h-4 w-4 text-amber-600 dark:text-amber-500" />
        <span className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-500">
          Bhagavad Gita • Chapter {source.chapter}, Verse {source.verse_start}
          {source.verse_end && source.verse_end !== source.verse_start ? `–${source.verse_end}` : ""}
        </span>
      </div>
      
      <p className="text-sm font-medium text-amber-900 dark:text-amber-200 leading-relaxed italic">
        "{source.core_lesson}"
      </p>
    </motion.div>
  )
}
