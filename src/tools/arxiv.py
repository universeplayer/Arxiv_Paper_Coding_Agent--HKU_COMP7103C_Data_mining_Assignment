"""arXiv integration for fetching and parsing academic papers."""

import arxiv
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from rich.console import Console

console = Console()


@dataclass
class PaperMetadata:
    """Metadata for an arXiv paper."""

    id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    primary_category: str
    published: str
    updated: str
    pdf_url: str
    arxiv_url: str
    comment: Optional[str] = None
    journal_ref: Optional[str] = None
    doi: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @property
    def published_date(self) -> datetime:
        """Get published date as datetime."""
        return datetime.fromisoformat(self.published.replace('Z', '+00:00'))

    @property
    def short_id(self) -> str:
        """Get short arXiv ID (without version)."""
        return self.id.split('v')[0]


def fetch_papers(
    category: str = "cs.AI",
    max_results: int = 50,
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
    sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending,
    days_back: Optional[int] = None
) -> List[PaperMetadata]:
    """Fetch papers from arXiv by category.

    Args:
        category: arXiv category (e.g., cs.AI, cs.CL, cs.LG)
        max_results: Maximum number of papers to fetch
        sort_by: Sort criterion
        sort_order: Sort order
        days_back: Only fetch papers from last N days (None for all)

    Returns:
        List of PaperMetadata objects
    """
    try:
        console.print(f"[blue]Fetching papers from arXiv category: {category}[/blue]")

        # Build search query
        search = arxiv.Search(
            query=f"cat:{category}",
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order
        )

        papers = []
        cutoff_date = None
        if days_back:
            from datetime import timezone
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        for result in search.results():
            # Filter by date if specified
            if cutoff_date and result.published < cutoff_date:
                continue

            paper = PaperMetadata(
                id=result.entry_id.split('/')[-1],
                title=result.title,
                authors=[author.name for author in result.authors],
                abstract=result.summary,
                categories=result.categories,
                primary_category=result.primary_category,
                published=result.published.isoformat(),
                updated=result.updated.isoformat(),
                pdf_url=result.pdf_url,
                arxiv_url=result.entry_id,
                comment=result.comment,
                journal_ref=result.journal_ref,
                doi=result.doi
            )
            papers.append(paper)

        console.print(f"[green]Fetched {len(papers)} papers from {category}[/green]")
        return papers

    except Exception as e:
        console.print(f"[red]Error fetching papers: {e}[/red]")
        return []


def search_arxiv(
    query: str,
    max_results: int = 20,
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance
) -> List[PaperMetadata]:
    """Search arXiv by keywords.

    Args:
        query: Search query
        max_results: Maximum results
        sort_by: Sort criterion

    Returns:
        List of PaperMetadata objects
    """
    try:
        console.print(f"[blue]Searching arXiv for: {query}[/blue]")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )

        papers = []
        for result in search.results():
            paper = PaperMetadata(
                id=result.entry_id.split('/')[-1],
                title=result.title,
                authors=[author.name for author in result.authors],
                abstract=result.summary,
                categories=result.categories,
                primary_category=result.primary_category,
                published=result.published.isoformat(),
                updated=result.updated.isoformat(),
                pdf_url=result.pdf_url,
                arxiv_url=result.entry_id,
                comment=result.comment,
                journal_ref=result.journal_ref,
                doi=result.doi
            )
            papers.append(paper)

        console.print(f"[green]Found {len(papers)} papers[/green]")
        return papers

    except Exception as e:
        console.print(f"[red]Error searching arXiv: {e}[/red]")
        return []


def parse_paper_metadata(result: Any) -> PaperMetadata:
    """Parse arXiv search result into PaperMetadata.

    Args:
        result: arXiv search result object

    Returns:
        PaperMetadata object
    """
    return PaperMetadata(
        id=result.entry_id.split('/')[-1],
        title=result.title,
        authors=[author.name for author in result.authors],
        abstract=result.summary,
        categories=result.categories,
        primary_category=result.primary_category,
        published=result.published.isoformat(),
        updated=result.updated.isoformat(),
        pdf_url=result.pdf_url,
        arxiv_url=result.entry_id,
        comment=result.comment,
        journal_ref=result.journal_ref,
        doi=result.doi
    )


def categorize_papers(papers: List[PaperMetadata]) -> Dict[str, List[PaperMetadata]]:
    """Categorize papers by their primary category.

    Args:
        papers: List of papers

    Returns:
        Dictionary mapping categories to papers
    """
    categorized = {}
    for paper in papers:
        category = paper.primary_category
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(paper)

    console.print(f"[blue]Categorized papers into {len(categorized)} categories[/blue]")
    return categorized


def filter_papers_by_keywords(
    papers: List[PaperMetadata],
    keywords: List[str],
    search_in: str = "all"  # 'title', 'abstract', 'all'
) -> List[PaperMetadata]:
    """Filter papers by keywords.

    Args:
        papers: List of papers
        keywords: Keywords to search for
        search_in: Where to search ('title', 'abstract', 'all')

    Returns:
        Filtered list of papers
    """
    filtered = []

    for paper in papers:
        text = ""
        if search_in in ("title", "all"):
            text += paper.title.lower() + " "
        if search_in in ("abstract", "all"):
            text += paper.abstract.lower()

        if any(keyword.lower() in text for keyword in keywords):
            filtered.append(paper)

    console.print(f"[blue]Filtered to {len(filtered)} papers matching keywords[/blue]")
    return filtered


def estimate_difficulty(paper: PaperMetadata) -> str:
    """Estimate paper difficulty based on heuristics.

    Args:
        paper: Paper metadata

    Returns:
        Difficulty level: 'beginner', 'intermediate', 'advanced'
    """
    # Simple heuristic based on abstract length and keywords
    abstract_lower = paper.abstract.lower()

    advanced_keywords = [
        "theorem", "proof", "convergence", "theoretical analysis",
        "asymptotic", "complexity analysis", "formal verification"
    ]
    beginner_keywords = [
        "introduction", "survey", "tutorial", "overview",
        "review", "simplified", "practical"
    ]

    advanced_count = sum(1 for kw in advanced_keywords if kw in abstract_lower)
    beginner_count = sum(1 for kw in beginner_keywords if kw in abstract_lower)

    if advanced_count >= 2:
        return "advanced"
    elif beginner_count >= 1:
        return "beginner"
    else:
        return "intermediate"


def get_daily_papers(
    categories: List[str],
    max_per_category: int = 20
) -> Dict[str, List[PaperMetadata]]:
    """Get today's papers from multiple categories.

    Args:
        categories: List of arXiv categories
        max_per_category: Max papers per category

    Returns:
        Dictionary mapping categories to papers
    """
    console.print(f"[blue]Fetching daily papers from {len(categories)} categories[/blue]")

    daily_papers = {}
    for category in categories:
        papers = fetch_papers(
            category=category,
            max_results=max_per_category,
            days_back=1  # Last 24 hours
        )
        if papers:
            daily_papers[category] = papers

    total = sum(len(papers) for papers in daily_papers.values())
    console.print(f"[green]Fetched {total} papers from {len(daily_papers)} categories[/green]")

    return daily_papers
