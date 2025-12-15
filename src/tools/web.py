"""Web operations including search and URL fetching."""

import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


def web_search(
    query: str,
    num_results: int = 10,
    search_type: str = "general"
) -> List[Dict[str, Any]]:
    """Simulate web search (Brave Search API replacement).

    In production, this would use actual Brave Search, Google Custom Search,
    or similar API. For demo purposes, returns simulated results.

    Args:
        query: Search query
        num_results: Number of results to return
        search_type: Type of search (general, news, academic)

    Returns:
        List of search results with title, url, snippet
    """
    console.print(f"[blue]Searching for: {query}[/blue]")

    # Simulated search results for demo
    results = []
    for i in range(min(num_results, 5)):
        results.append({
            "title": f"Result {i+1} for '{query}'",
            "url": f"https://example.com/result{i+1}",
            "snippet": f"This is a simulated search result snippet for {query}. "
                      f"In production, this would return actual search results.",
            "rank": i + 1
        })

    console.print(f"[green]Found {len(results)} results[/green]")
    return results


def fetch_url(
    url: str,
    timeout: int = 30,
    extract_text: bool = True
) -> Dict[str, Any]:
    """Fetch content from a URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        extract_text: Whether to extract text from HTML

    Returns:
        Dictionary with status, content, and metadata

    Raises:
        requests.RequestException: If fetching fails
    """
    try:
        console.print(f"[blue]Fetching URL: {url}[/blue]")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        result = {
            "status": "success",
            "url": url,
            "status_code": response.status_code,
            "content_type": content_type,
            "raw_content": response.text,
        }

        # Extract text from HTML if requested
        if extract_text and "text/html" in content_type:
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator="\n", strip=True)
            result["text"] = text
            result["title"] = soup.title.string if soup.title else ""

            console.print(f"[green]Fetched {len(text)} characters from {url}[/green]")
        else:
            console.print(f"[green]Fetched {len(response.text)} bytes from {url}[/green]")

        return result

    except requests.Timeout:
        console.print(f"[red]Timeout fetching {url}[/red]")
        return {"status": "error", "error": "Timeout", "url": url}
    except requests.RequestException as e:
        console.print(f"[red]Error fetching {url}: {e}[/red]")
        return {"status": "error", "error": str(e), "url": url}
    except Exception as e:
        console.print(f"[red]Unexpected error fetching {url}: {e}[/red]")
        return {"status": "error", "error": str(e), "url": url}


def download_file(
    url: str,
    filepath: str,
    timeout: int = 60
) -> Dict[str, Any]:
    """Download a file from URL.

    Args:
        url: URL to download from
        filepath: Local path to save file
        timeout: Request timeout

    Returns:
        Dictionary with status and message
    """
    try:
        console.print(f"[blue]Downloading {url} to {filepath}[/blue]")

        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = len(response.content)
        console.print(f"[green]Downloaded {file_size} bytes to {filepath}[/green]")

        return {
            "status": "success",
            "filepath": filepath,
            "size": file_size,
            "url": url
        }

    except Exception as e:
        console.print(f"[red]Error downloading {url}: {e}[/red]")
        return {"status": "error", "error": str(e), "url": url}


def extract_links(html: str, base_url: Optional[str] = None) -> List[str]:
    """Extract all links from HTML content.

    Args:
        html: HTML content
        base_url: Optional base URL for resolving relative links

    Returns:
        List of URLs
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            # Resolve relative URLs if base_url provided
            if base_url and not href.startswith(("http://", "https://")):
                from urllib.parse import urljoin
                href = urljoin(base_url, href)

            links.append(href)

        console.print(f"[blue]Extracted {len(links)} links[/blue]")
        return links

    except Exception as e:
        console.print(f"[red]Error extracting links: {e}[/red]")
        return []
