"""פירוק גנרי של קובץ EDI לסגמנטים/אלמנטים.

TODO: הפורמט כרגע גנרי (separators בלבד). יש לבדוק מול הבנק/ERP את
המבנה המדויק (קודי סוג הודעה, מיפוי שדות) ואולי לעבור לספרייה ייעודית
עם תמיכה ב-schema validation (למשל pyx12, bots).
"""
from dataclasses import dataclass, field


@dataclass
class Segment:
    tag: str
    elements: list[str] = field(default_factory=list)


def parse_edi(raw_text: str, segment_sep: str = "~", element_sep: str = "*") -> list[Segment]:
    """מפרק טקסט EDI גולמי לרשימת סגמנטים, כל אחד עם tag ורשימת אלמנטים."""
    raw_text = raw_text.replace("\r\n", "").replace("\n", "")
    raw_segments = [seg.strip() for seg in raw_text.split(segment_sep) if seg.strip()]

    segments = []
    for raw_segment in raw_segments:
        elements = raw_segment.split(element_sep)
        tag, rest = elements[0], elements[1:]
        segments.append(Segment(tag=tag, elements=rest))
    return segments


def summarize(segments: list[Segment]) -> str:
    """סיכום קצר להצגה/לוג: כמות סגמנטים ופירוט תגיות."""
    tags = [s.tag for s in segments]
    return f"{len(segments)} segments: {', '.join(tags[:20])}" + ("..." if len(tags) > 20 else "")
