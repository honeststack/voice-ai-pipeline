#!/usr/bin/env python3
"""
Local Note Manager for TTS AI Pipeline

This component provides local note storage and management as an alternative
to Microsoft OneNote. It creates structured notes in local files and directories,
eliminating the need for Azure authentication.

Features:
- Local file-based note storage
- Automatic directory structure creation
- Markdown and HTML note formats
- Note search and organization
- No external dependencies or authentication required

Usage:
    from voice_ai_pipeline.local_notes import LocalNoteManager
    manager = LocalNoteManager()
    manager.create_note("My Note", "Full transcription", "Summary")
"""

import os
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import re


class LocalNoteManager:
    """Local file-based note manager."""

    def __init__(self, base_dir: str = "~/tts_ai_notes"):
        """
        Initialize local note manager.

        Args:
            base_dir: Base directory for storing notes (default: ~/tts_ai_notes)
        """
        self.base_dir = Path(base_dir).expanduser()
        self.notes_dir = self.base_dir / "notes"
        self.metadata_file = self.base_dir / "metadata.json"

        # Create directories if they don't exist
        self.notes_dir.mkdir(parents=True, exist_ok=True)

        # Load or create metadata
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass

        # Create default metadata
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "note_count": 0,
            "notebooks": {},
            "tags": []
        }

    def _save_metadata(self):
        """Save metadata to file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Failed to save metadata: {e}")

    def create_notebook(self, name: str) -> str:
        """
        Create a new notebook (directory).

        Args:
            name: Notebook name

        Returns:
            Path to the notebook directory
        """
        # Sanitize notebook name for filesystem
        safe_name = self._sanitize_filename(name)
        notebook_path = self.notes_dir / safe_name

        notebook_path.mkdir(exist_ok=True)

        # Update metadata
        if safe_name not in self.metadata["notebooks"]:
            self.metadata["notebooks"][safe_name] = {
                "name": name,
                "created": datetime.now().isoformat(),
                "note_count": 0,
                "path": str(notebook_path)
            }
            self._save_metadata()

        print(f"📓 Created notebook: {name}")
        return str(notebook_path)

    def create_section(self, notebook_name: str, section_name: str) -> str:
        """
        Create a section within a notebook.

        Args:
            notebook_name: Parent notebook name
            section_name: Section name

        Returns:
            Path to the section directory
        """
        notebook_path = self.notes_dir / self._sanitize_filename(notebook_name)
        section_path = notebook_path / self._sanitize_filename(section_name)

        section_path.mkdir(parents=True, exist_ok=True)

        print(f"📑 Created section: {section_name}")
        return str(section_path)

    def create_note(self, title: str, transcription: str, summary: str,
                   notebook: str = "AI Transcriptions",
                   section: str = "Transcriptions",
                   metadata: Optional[Dict[str, Any]] = None,
                   format: str = "markdown") -> str:
        """
        Create a new note with transcription and summary.

        Args:
            title: Note title
            transcription: Full transcription text
            summary: Summarized text
            notebook: Notebook name
            section: Section name
            metadata: Additional metadata
            format: Output format ('markdown' or 'html')

        Returns:
            Path to the created note file
        """
        # Create notebook and section
        notebook_path = self.create_notebook(notebook)
        section_path = self.create_section(notebook, section)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = self._sanitize_filename(title)
        filename = f"{timestamp}_{safe_title}"

        if format == "html":
            filename += ".html"
            content = self._format_html_note(title, transcription, summary, metadata)
        else:
            filename += ".md"
            content = self._format_markdown_note(title, transcription, summary, metadata)

        # Write note file
        note_path = Path(section_path) / filename
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Update metadata
        notebook_key = self._sanitize_filename(notebook)
        if notebook_key in self.metadata["notebooks"]:
            self.metadata["notebooks"][notebook_key]["note_count"] += 1
        self.metadata["note_count"] += 1
        self._save_metadata()

        print(f"📝 Created note: {title}")
        print(f"   Saved to: {note_path}")

        return str(note_path)

    def _format_markdown_note(self, title: str, transcription: str,
                            summary: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Format note as Markdown."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content = f"# {title}\n\n"
        content += f"**Created:** {timestamp}\n\n"

        if metadata:
            content += "## Metadata\n\n"
            for key, value in metadata.items():
                content += f"- **{key}:** {value}\n"
            content += "\n"

        content += f"## Summary\n\n{summary}\n\n"

        content += f"## Full Transcription\n\n{transcription}\n\n"

        content += "---\n*Generated by TTS AI Pipeline*"

        return content

    def _format_html_note(self, title: str, transcription: str,
                        summary: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Format note as HTML."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .metadata {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .transcription {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            white-space: pre-wrap;
        }}
        .footer {{
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p><strong>Created:</strong> {timestamp}</p>
"""

        if metadata:
            html += """
        <h2>Metadata</h2>
        <div class="metadata">
"""
            for key, value in metadata.items():
                html += f"            <p><strong>{key}:</strong> {value}</p>\n"
            html += "        </div>\n"

        html += f"""
        <h2>Summary</h2>
        <div class="summary">
            {summary}
        </div>

        <h2>Full Transcription</h2>
        <div class="transcription">
            {transcription.replace(chr(10), '<br>')}
        </div>

        <div class="footer">
            Generated by TTS AI Pipeline
        </div>
    </div>
</body>
</html>"""

        return html

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use as filename."""
        # Remove or replace invalid characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Remove leading/trailing whitespace and dots
        safe_name = safe_name.strip(' .')
        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        # Ensure not empty
        if not safe_name:
            safe_name = "untitled"
        return safe_name

    def list_notebooks(self) -> List[Dict[str, Any]]:
        """List all notebooks."""
        notebooks = []
        for name, info in self.metadata["notebooks"].items():
            notebooks.append({
                'id': name,
                'name': info['name'],
                'created': info['created'],
                'note_count': info['note_count'],
                'path': info['path']
            })
        return notebooks

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """
        Search notes by content.

        Args:
            query: Search query

        Returns:
            List of matching notes
        """
        results = []
        query_lower = query.lower()

        # Search through all note files
        for notebook_dir in self.notes_dir.iterdir():
            if notebook_dir.is_dir():
                for section_dir in notebook_dir.iterdir():
                    if section_dir.is_dir():
                        for note_file in section_dir.iterdir():
                            if note_file.is_file() and note_file.suffix in ['.md', '.html']:
                                try:
                                    with open(note_file, 'r', encoding='utf-8') as f:
                                        content = f.read().lower()

                                    if query_lower in content:
                                        results.append({
                                            'path': str(note_file),
                                            'notebook': notebook_dir.name,
                                            'section': section_dir.name,
                                            'filename': note_file.name,
                                            'modified': datetime.fromtimestamp(note_file.stat().st_mtime).isoformat()
                                        })
                                except Exception:
                                    continue

        return results

    def get_note_content(self, note_path: str) -> Optional[str]:
        """Get content of a specific note."""
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the note collection."""
        total_notes = 0
        total_size = 0

        for notebook_dir in self.notes_dir.iterdir():
            if notebook_dir.is_dir():
                for section_dir in notebook_dir.iterdir():
                    if section_dir.is_dir():
                        for note_file in section_dir.iterdir():
                            if note_file.is_file() and note_file.suffix in ['.md', '.html']:
                                total_notes += 1
                                total_size += note_file.stat().st_size

        return {
            'total_notebooks': len(self.metadata["notebooks"]),
            'total_notes': total_notes,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'base_directory': str(self.base_dir)
        }


def main():
    """Command-line interface for local note manager."""
    import argparse

    parser = argparse.ArgumentParser(description="Local Note Manager for TTS AI Pipeline")
    parser.add_argument('--list-notebooks', action='store_true', help='List all notebooks')
    parser.add_argument('--search', help='Search notes by content')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--base-dir', help='Base directory for notes')

    args = parser.parse_args()

    try:
        manager = LocalNoteManager(base_dir=args.base_dir)

        if args.list_notebooks:
            notebooks = manager.list_notebooks()
            if notebooks:
                print("📓 Local Notebooks:")
                for notebook in notebooks:
                    print(f"  - {notebook['name']} ({notebook['note_count']} notes)")
            else:
                print("❌ No notebooks found")

        elif args.search:
            results = manager.search_notes(args.search)
            if results:
                print(f"🔍 Search results for '{args.search}':")
                for result in results:
                    print(f"  - {result['notebook']}/{result['section']}/{result['filename']}")
            else:
                print(f"❌ No notes found matching '{args.search}'")

        elif args.stats:
            stats = manager.get_stats()
            print("📊 Local Notes Statistics:")
            print(f"   Base Directory: {stats['base_directory']}")
            print(f"   Notebooks: {stats['total_notebooks']}")
            print(f"   Total Notes: {stats['total_notes']}")
            print(f"   Total Size: {stats['total_size_mb']} MB")

        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
