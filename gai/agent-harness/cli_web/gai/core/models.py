"""Response models for cli-web-gai."""

from dataclasses import asdict, dataclass, field


@dataclass
class Source:
    """A reference source from the AI response."""

    title: str
    url: str
    snippet: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d["snippet"]:
            del d["snippet"]
        return d


@dataclass
class SearchResult:
    """An AI Mode search result."""

    query: str
    answer: str
    sources: list[Source] = field(default_factory=list)
    follow_up_prompt: str = ""

    def to_dict(self) -> dict:
        return {
            "success": True,
            "data": {
                "query": self.query,
                "answer": self.answer,
                "sources": [s.to_dict() for s in self.sources],
                **({"follow_up_prompt": self.follow_up_prompt} if self.follow_up_prompt else {}),
            },
        }
