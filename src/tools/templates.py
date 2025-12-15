"""Template system for generating web pages."""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console

console = Console()


class TemplateRenderer:
    """Render HTML templates with Jinja2."""

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template renderer.

        Args:
            template_dir: Directory containing templates (uses package templates if None)
        """
        if template_dir is None:
            # Use package templates directory
            template_dir = Path(__file__).parent.parent / "templates"

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

        console.print(f"[blue]Template renderer initialized with dir: {template_dir}[/blue]")

    def render(
        self,
        template_name: str,
        context: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> str:
        """Render template with context.

        Args:
            template_name: Template filename
            context: Template context variables
            output_path: Optional path to save rendered output

        Returns:
            Rendered HTML string
        """
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)

            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding='utf-8')
                console.print(f"[green]Rendered template to {output_path}[/green]")

            return rendered

        except Exception as e:
            console.print(f"[red]Error rendering template {template_name}: {e}[/red]")
            raise

    def render_arxiv_page(
        self,
        papers: list,
        output_dir: Path,
        date: Optional[str] = None
    ) -> Path:
        """Render arXiv daily page with all assets.

        Args:
            papers: List of paper metadata
            output_dir: Output directory for generated files
            date: Display date (defaults to today)

        Returns:
            Path to generated index.html
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare context
        if date is None:
            date = datetime.now().strftime("%B %d, %Y")

        # Categorize papers
        categories = set()
        for paper in papers:
            categories.add(paper.get('primary_category', 'Unknown'))

        # Estimate difficulty for each paper
        from src.tools.arxiv import estimate_difficulty, PaperMetadata

        enriched_papers = []
        for paper in papers:
            # Convert dict to PaperMetadata if needed
            if isinstance(paper, dict):
                # Create minimal PaperMetadata
                paper_obj = type('obj', (object,), paper)()
                difficulty = estimate_difficulty(paper_obj)
                paper['difficulty'] = difficulty

                # Format date
                pub_date = paper.get('published', '')
                if pub_date:
                    try:
                        dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        paper['published_date'] = dt.strftime("%b %d, %Y")
                    except:
                        paper['published_date'] = pub_date[:10]

                # Short ID
                paper_id = paper.get('id', '')
                paper['short_id'] = paper_id.split('v')[0] if 'v' in paper_id else paper_id

            enriched_papers.append(paper)

        context = {
            'date': date,
            'papers': enriched_papers,
            'total_papers': len(enriched_papers),
            'categories': sorted(categories)
        }

        # Render HTML
        index_path = output_dir / "index.html"
        self.render('modern_arxiv.html', context, index_path)

        # Copy CSS and JS
        css_src = self.template_dir / "style.css"
        js_src = self.template_dir / "script.js"

        if css_src.exists():
            shutil.copy2(css_src, output_dir / "style.css")
            console.print(f"[green]Copied CSS to {output_dir / 'style.css'}[/green]")

        if js_src.exists():
            shutil.copy2(js_src, output_dir / "script.js")
            console.print(f"[green]Copied JS to {output_dir / 'script.js'}[/green]")

        console.print(f"[bold green]arXiv page generated at {index_path}[/bold green]")

        return index_path

    def render_paper_detail(
        self,
        paper: Dict[str, Any],
        output_path: Path
    ) -> Path:
        """Render individual paper detail page.

        Args:
            paper: Paper metadata
            output_path: Output file path

        Returns:
            Path to generated file
        """
        # Create simple detail template inline
        detail_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ paper.title }}</title>
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{{ paper.title }}</h1>
            <p class="subtitle">{{ paper.primary_category }} | {{ paper.published_date }}</p>
        </header>

        <section class="paper-detail">
            <div class="detail-section">
                <h2>Authors</h2>
                <ul>
                {% for author in paper.authors %}
                    <li>{{ author }}</li>
                {% endfor %}
                </ul>
            </div>

            <div class="detail-section">
                <h2>Abstract</h2>
                <p>{{ paper.abstract }}</p>
            </div>

            <div class="detail-section">
                <h2>Categories</h2>
                <p>{{ paper.categories|join(', ') }}</p>
            </div>

            <div class="detail-section">
                <h2>Links</h2>
                <a href="{{ paper.pdf_url }}" class="btn btn-primary">View PDF</a>
                <a href="{{ paper.arxiv_url }}" class="btn btn-secondary">View on arXiv</a>
            </div>
        </section>
    </div>
</body>
</html>
"""

        # Render using string template
        from jinja2 import Template
        template = Template(detail_template)
        rendered = template.render(paper=paper)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding='utf-8')

        console.print(f"[green]Paper detail page generated at {output_path}[/green]")

        return output_path
