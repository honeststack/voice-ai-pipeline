#!/usr/bin/env python3
"""
Microsoft OneNote Integration for TTS AI Pipeline

This component provides integration with Microsoft OneNote for creating
and managing notes from transcribed and summarized audio content.

Features:
- Microsoft Graph API integration
- Automatic note creation with transcription and summary
- Support for different note sections and pages
- Error handling and authentication management

Requirements:
    - msgraph-sdk
    - msgraph-core
    - azure-identity
    - Microsoft Azure app registration with OneNote permissions

Setup:
    1. Register an app in Azure AD
    2. Add OneNote permissions: Notes.ReadWrite, Notes.ReadWrite.All
    3. Set up authentication flow (device code or client credentials)
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from msgraph import GraphServiceClient
    from msgraph_core import GraphClient
    from azure.identity import DeviceCodeCredential, ClientSecretCredential
    from azure.core.exceptions import ClientException
    MSGRAPH_AVAILABLE = True
except ImportError:
    GraphServiceClient = None
    GraphClient = None
    DeviceCodeCredential = None
    ClientSecretCredential = None
    ClientException = None
    MSGRAPH_AVAILABLE = False


class OneNoteManager:
    """Microsoft OneNote integration manager."""

    def __init__(self, client_id: Optional[str] = None, tenant_id: Optional[str] = None,
                 client_secret: Optional[str] = None):
        """
        Initialize OneNote manager.

        Args:
            client_id: Azure app client ID
            tenant_id: Azure tenant ID
            client_secret: Azure app client secret (for service principal auth)
        """
        if not MSGRAPH_AVAILABLE:
            raise ImportError("Microsoft Graph SDK is not available. Please install with: pip install msgraph-sdk azure-identity")

        self.client_id = client_id or os.getenv('AZURE_CLIENT_ID')
        self.tenant_id = tenant_id or os.getenv('AZURE_TENANT_ID')
        self.client_secret = client_secret or os.getenv('AZURE_CLIENT_SECRET')

        if not self.client_id:
            raise ValueError("Client ID is required. Set AZURE_CLIENT_ID environment variable or pass client_id parameter.")

        self.graph_client = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Microsoft Graph API."""
        try:
            if self.client_secret and self.tenant_id:
                # Service principal authentication
                credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            else:
                # Device code authentication (interactive)
                credential = DeviceCodeCredential(
                    client_id=self.client_id,
                    tenant_id=self.tenant_id
                )

            scopes = ['https://graph.microsoft.com/.default']
            self.graph_client = GraphServiceClient(credential, scopes)

            print("✅ Successfully authenticated with Microsoft Graph")

        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            raise

    def list_notebooks(self) -> List[Dict[str, Any]]:
        """
        List all OneNote notebooks.

        Returns:
            List of notebook dictionaries
        """
        try:
            result = self.graph_client.me.onenote.notebooks.get()
            notebooks = []
            for notebook in result.value:
                notebooks.append({
                    'id': notebook.id,
                    'name': notebook.display_name,
                    'created_time': notebook.created_date_time,
                    'last_modified': notebook.last_modified_date_time
                })
            return notebooks

        except Exception as e:
            print(f"❌ Failed to list notebooks: {e}")
            return []

    def get_or_create_notebook(self, notebook_name: str = "AI Transcriptions") -> Optional[str]:
        """
        Get or create a notebook by name.

        Args:
            notebook_name: Name of the notebook

        Returns:
            Notebook ID or None if failed
        """
        try:
            # Check if notebook exists
            notebooks = self.list_notebooks()
            for notebook in notebooks:
                if notebook['name'] == notebook_name:
                    print(f"📓 Found existing notebook: {notebook_name}")
                    return notebook['id']

            # Create new notebook
            print(f"📓 Creating new notebook: {notebook_name}")
            request_body = {
                "displayName": notebook_name
            }

            result = self.graph_client.me.onenote.notebooks.post(request_body)
            print(f"✅ Created notebook: {notebook_name}")
            return result.id

        except Exception as e:
            print(f"❌ Failed to get/create notebook: {e}")
            return None

    def list_sections(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        List sections in a notebook.

        Args:
            notebook_id: ID of the notebook

        Returns:
            List of section dictionaries
        """
        try:
            result = self.graph_client.me.onenote.notebooks.by_onenote_notebook_id(notebook_id).sections.get()
            sections = []
            for section in result.value:
                sections.append({
                    'id': section.id,
                    'name': section.display_name,
                    'created_time': section.created_date_time,
                    'last_modified': section.last_modified_date_time
                })
            return sections

        except Exception as e:
            print(f"❌ Failed to list sections: {e}")
            return []

    def get_or_create_section(self, notebook_id: str, section_name: str = "Transcriptions") -> Optional[str]:
        """
        Get or create a section in a notebook.

        Args:
            notebook_id: ID of the notebook
            section_name: Name of the section

        Returns:
            Section ID or None if failed
        """
        try:
            # Check if section exists
            sections = self.list_sections(notebook_id)
            for section in sections:
                if section['name'] == section_name:
                    print(f"📑 Found existing section: {section_name}")
                    return section['id']

            # Create new section
            print(f"📑 Creating new section: {section_name}")
            request_body = {
                "displayName": section_name
            }

            result = self.graph_client.me.onenote.notebooks.by_onenote_notebook_id(notebook_id).sections.post(request_body)
            print(f"✅ Created section: {section_name}")
            return result.id

        except Exception as e:
            print(f"❌ Failed to get/create section: {e}")
            return None

    def create_note_page(self, section_id: str, title: str, transcription: str,
                        summary: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Create a new note page with transcription and summary.

        Args:
            section_id: ID of the section to create the page in
            title: Title of the note
            transcription: Full transcription text
            summary: Summarized text
            metadata: Additional metadata (duration, timestamp, etc.)

        Returns:
            Page ID or None if failed
        """
        try:
            # Format the HTML content
            html_content = self._format_note_html(title, transcription, summary, metadata)

            # Create the page
            result = self.graph_client.me.onenote.sections.by_onenote_section_id(section_id).pages.post({
                "title": title,
                "content": html_content
            })

            print(f"📝 Created note page: {title}")
            return result.id

        except Exception as e:
            print(f"❌ Failed to create note page: {e}")
            return None

    def _format_note_html(self, title: str, transcription: str, summary: str,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Format the note content as HTML.

        Args:
            title: Note title
            transcription: Full transcription
            summary: Summary text
            metadata: Additional metadata

        Returns:
            HTML formatted content
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
        </head>
        <body>
            <h1>{title}</h1>
            <p><strong>Created:</strong> {timestamp}</p>
        """

        if metadata:
            html += "<h2>Metadata</h2><ul>"
            for key, value in metadata.items():
                html += f"<li><strong>{key}:</strong> {value}</li>"
            html += "</ul>"

        html += f"""
            <h2>Summary</h2>
            <p>{summary}</p>

            <h2>Full Transcription</h2>
            <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
                {transcription.replace(chr(10), '<br>')}
            </div>
        </body>
        </html>
        """

        return html

    def create_transcription_note(self, transcription: str, summary: str,
                                title: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a complete transcription note with automatic notebook/section management.

        Args:
            transcription: Full transcription text
            summary: Summarized text
            title: Custom title (auto-generated if None)
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Auto-generate title if not provided
            if not title:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                title = f"AI Transcription {timestamp}"

            # Get or create notebook
            notebook_id = self.get_or_create_notebook()
            if not notebook_id:
                return False

            # Get or create section
            section_id = self.get_or_create_section(notebook_id)
            if not section_id:
                return False

            # Create the note page
            page_id = self.create_note_page(section_id, title, transcription, summary, metadata)

            return page_id is not None

        except Exception as e:
            print(f"❌ Failed to create transcription note: {e}")
            return False


def main():
    """Command-line interface for OneNote manager."""
    import argparse

    parser = argparse.ArgumentParser(description="Microsoft OneNote Manager for TTS AI Pipeline")
    parser.add_argument('--client-id', help='Azure app client ID')
    parser.add_argument('--tenant-id', help='Azure tenant ID')
    parser.add_argument('--client-secret', help='Azure app client secret')
    parser.add_argument('--list-notebooks', action='store_true', help='List all notebooks')
    parser.add_argument('--test-connection', action='store_true', help='Test OneNote connection')

    args = parser.parse_args()

    # Check availability
    if not MSGRAPH_AVAILABLE:
        print("❌ Microsoft Graph SDK is not available.")
        print("📦 Install with: pip install msgraph-sdk azure-identity")
        print("\n🔧 Setup instructions:")
        print("1. Register an app in Azure AD: https://portal.azure.com")
        print("2. Add OneNote permissions: Notes.ReadWrite, Notes.ReadWrite.All")
        print("3. Set environment variables:")
        print("   export AZURE_CLIENT_ID='your-client-id'")
        print("   export AZURE_TENANT_ID='your-tenant-id'")
        print("   export AZURE_CLIENT_SECRET='your-client-secret' (optional)")
        return 1

    try:
        manager = OneNoteManager(
            client_id=args.client_id,
            tenant_id=args.tenant_id,
            client_secret=args.client_secret
        )

        if args.list_notebooks:
            notebooks = manager.list_notebooks()
            if notebooks:
                print("📓 Available notebooks:")
                for notebook in notebooks:
                    print(f"  - {notebook['name']} (ID: {notebook['id']})")
            else:
                print("❌ No notebooks found")

        elif args.test_connection:
            print("🧪 Testing OneNote connection...")
            notebooks = manager.list_notebooks()
            if notebooks:
                print(f"✅ Connection successful! Found {len(notebooks)} notebook(s)")
            else:
                print("⚠️  Connection successful but no notebooks found")

        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
