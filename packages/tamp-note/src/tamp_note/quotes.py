"""
tamp_note.quotes
~~~~~~~~~~~~~~~~
Shown briefly when a todo is marked done.
Voice: dry, precise, slightly wry. Never loud. Written by hand.
"""

import random

QUOTES: list[str] = [
    "Done. The others will come around eventually.",
    "One less thing pretending it doesn't exist.",
    "Closed. The file is now at peace.",
    "That one's been watching you. Not anymore.",
    "Marked done. The feeling lasts about four seconds.",
    "Finished. You may now pretend it was easy.",
    "Off the list. On to the next list.",
    "Resolved. Somewhere a log file sighs with relief.",
    "Done. Your future self owes you nothing for this one.",
    "Complete. The backlog blinks, recalibrates.",
    "Filed. Not everything deserves a ceremony.",
    "Gone. It was never as hard as it looked.",
    "Done. You had it in you the whole time, apparently.",
    "Closed. The cursor moves on.",
    "That one's been in the queue since before you remembered it. Good.",
    "Done. The log gets shorter. Briefly.",
    "Resolved. Add it to the list of things you didn't fail at.",
    "Finished. The machine doesn't care but it noticed.",
    "One down. The rest are probably fine.",
    "Done. Small victories are still victories.",
    "Committed. No undo.",
    "Marked. The day gets a little lighter.",
    "Closed out. On to what's next.",
    "Done. That's the one you kept skipping.",
    "Complete. It only took however long it took.",
    "Filed away. The list exhales.",
    "Resolved. You were always going to do this.",
    "Done. Write the next one. It's waiting.",
    "Off the stack. Clean.",
    "That one's gone. The others are paying attention.",
]


def get_quote() -> str:
    return random.choice(QUOTES)
