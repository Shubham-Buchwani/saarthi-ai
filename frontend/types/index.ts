export interface ShlokaSource {
  chapter: number
  verse_start: number
  verse_end: number
  source_file: string
  core_lesson: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  sources?: ShlokaSource[]
  timestamp: Date
}

export interface DailyWisdom {
  chapter: number
  verse_start: number
  verse_end: number
  shloka_sanskrit: string
  simple_summary: string
  core_lesson: string
  everyday_analogy: string
  theme: string
  krishna_message: string
}
