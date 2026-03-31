"""
Safety layer for Saarthi AI.
Detects crisis situations and out-of-scope topics.
"""

CRISIS_KEYWORDS = [
    "kill myself", "suicide", "suicidal", "self-harm", "self harm",
    "want to die", "end my life", "not worth living", "hurt myself",
    "end it all", "no reason to live", "better off dead",
    "खुद को मारना", "आत्महत्या", "जीना नहीं चाहता",
]

OUT_OF_SCOPE_KEYWORDS = [
    "who will win the election", "politics", "stock tips", "stock market advice",
    "how to hack", "illegal", "weapon", "bomb",
]

CRISIS_RESPONSE = """I can hear that you are going through something very heavy right now.

What you are feeling is real, and I want you to know — reaching out, even here, took courage.

But right now, the most important thing is for you to speak with someone who can truly hold your hand through this.

📞 **iCall (India):** 9152987821
📞 **Vandrevala Foundation:** 1860-2662-345 (24/7)
📞 **AASRA:** 9820466627 (24/7)
📞 **Snehi:** 044-24640050

Please reach out to them. You matter more than any problem ever could.

I am still here whenever you want to talk. 🤍"""

OUT_OF_SCOPE_RESPONSE = """That is a little outside the space I am built for.

My strength is in understanding the inner battles — the stress, the confusion, the purpose, the fear. Those are the conversations I am here for.

Is there something weighing on your mind or heart that I can genuinely help you explore?"""


def check_crisis(message: str) -> bool:
    """Returns True if the message contains crisis signals."""
    lower = message.lower()
    return any(kw in lower for kw in CRISIS_KEYWORDS)


def check_out_of_scope(message: str) -> bool:
    """Returns True if the message is clearly out of scope."""
    lower = message.lower()
    return any(kw in lower for kw in OUT_OF_SCOPE_KEYWORDS)


def get_safe_response(message: str) -> str | None:
    """
    Returns a safety response if needed, or None to proceed normally.
    """
    if check_crisis(message):
        return CRISIS_RESPONSE
    if check_out_of_scope(message):
        return OUT_OF_SCOPE_RESPONSE
    return None
