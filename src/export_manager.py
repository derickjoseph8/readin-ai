"""Export manager for saving conversation history to files."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class ExportManager:
    """Manages exporting conversation history to various file formats."""

    SUPPORTED_FORMATS = ['txt', 'md', 'json']

    def __init__(self, default_directory: Optional[str] = None):
        """Initialize the export manager.

        Args:
            default_directory: Default directory for exports. Uses Documents/ReadIn AI if not specified.
        """
        if default_directory:
            self.default_directory = Path(default_directory)
        else:
            # Default to Documents/ReadIn AI
            if os.name == 'nt':
                docs = Path(os.environ.get('USERPROFILE', Path.home())) / 'Documents'
            else:
                docs = Path.home() / 'Documents'
            self.default_directory = docs / 'ReadIn AI'

        self.default_directory.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        conversations: List[Dict[str, Any]],
        format: str = 'md',
        filename: Optional[str] = None,
        directory: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
        """Export conversations to a file.

        Args:
            conversations: List of conversation entries with 'question' and 'answer' keys
            format: Export format ('txt', 'md', 'json')
            filename: Custom filename (without extension). Auto-generated if not provided.
            directory: Export directory. Uses default if not provided.
            metadata: Optional metadata to include (date, duration, meeting app, etc.)

        Returns:
            Path to the exported file, or None if export failed
        """
        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}. Use one of: {self.SUPPORTED_FORMATS}")

        if not conversations:
            return None

        # Determine output path
        export_dir = directory or self.default_directory
        export_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"conversation_{timestamp}"

        output_path = export_dir / f"{filename}.{format}"

        # Export based on format
        try:
            if format == 'txt':
                self._export_txt(output_path, conversations, metadata)
            elif format == 'md':
                self._export_md(output_path, conversations, metadata)
            elif format == 'json':
                self._export_json(output_path, conversations, metadata)

            # Set secure file permissions (owner read/write only)
            self._set_secure_permissions(output_path)

            return output_path
        except PermissionError as e:
            print(f"Export failed - permission denied: {e}")
            return None
        except Exception as e:
            print(f"Export failed: {e}")
            return None

    def _set_secure_permissions(self, path: Path) -> None:
        """Set secure file permissions (owner read/write only - 0o600).

        Works on both Windows and Unix systems.

        Args:
            path: Path to the file to secure
        """
        try:
            # Set file mode to 0o600 (owner read/write only)
            os.chmod(path, 0o600)
        except PermissionError as e:
            print(f"Warning: Could not set secure permissions on {path}: {e}")
        except OSError as e:
            # On some Windows configurations, chmod may fail
            print(f"Warning: Could not set file permissions on {path}: {e}")
        except Exception as e:
            print(f"Warning: Unexpected error setting permissions on {path}: {e}")

    def _export_txt(
        self,
        path: Path,
        conversations: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]]
    ):
        """Export to plain text format."""
        lines = []

        # Header
        lines.append("ReadIn AI - Conversation Export")
        lines.append("=" * 40)
        lines.append("")

        # Metadata
        if metadata:
            if 'date' in metadata:
                lines.append(f"Date: {metadata['date']}")
            if 'duration' in metadata:
                lines.append(f"Duration: {metadata['duration']}")
            if 'meeting_app' in metadata:
                lines.append(f"Meeting App: {metadata['meeting_app']}")
            lines.append("")
            lines.append("-" * 40)
            lines.append("")

        # Conversations
        for i, conv in enumerate(conversations, 1):
            timestamp = conv.get('timestamp', '')
            timestamp_str = f" [{timestamp}]" if timestamp else ""

            lines.append(f"[{i}]{timestamp_str}")
            lines.append("")
            lines.append("QUESTION:")
            lines.append(conv.get('question', '(No question recorded)'))
            lines.append("")
            lines.append("ANSWER:")
            lines.append(conv.get('answer', '(No answer recorded)'))
            lines.append("")
            lines.append("-" * 40)
            lines.append("")

        # Footer
        lines.append("")
        lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("Generated by ReadIn AI - https://www.getreadin.us")

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        except PermissionError:
            raise PermissionError(f"Cannot write to {path}. Check file permissions.")

    def _export_md(
        self,
        path: Path,
        conversations: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]]
    ):
        """Export to Markdown format."""
        lines = []

        # Header
        lines.append("# ReadIn AI - Conversation Export")
        lines.append("")

        # Metadata
        if metadata:
            lines.append("## Session Info")
            lines.append("")
            if 'date' in metadata:
                lines.append(f"- **Date:** {metadata['date']}")
            if 'duration' in metadata:
                lines.append(f"- **Duration:** {metadata['duration']}")
            if 'meeting_app' in metadata:
                lines.append(f"- **Meeting App:** {metadata['meeting_app']}")
            if 'total_exchanges' in metadata:
                lines.append(f"- **Total Exchanges:** {metadata['total_exchanges']}")
            lines.append("")

        # Conversations
        lines.append("## Conversation")
        lines.append("")

        for i, conv in enumerate(conversations, 1):
            timestamp = conv.get('timestamp', '')
            timestamp_str = f" `{timestamp}`" if timestamp else ""

            lines.append(f"### Exchange {i}{timestamp_str}")
            lines.append("")
            lines.append("**Question:**")
            lines.append(f"> {conv.get('question', '(No question recorded)')}")
            lines.append("")
            lines.append("**AI Talking Points:**")
            lines.append("")

            answer = conv.get('answer', '(No answer recorded)')
            # Format bullet points properly
            for line in answer.split('\n'):
                line = line.strip()
                if line:
                    if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                        lines.append(line)
                    else:
                        lines.append(f"- {line}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Footer
        lines.append("")
        lines.append(f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append("*Generated by [ReadIn AI](https://www.getreadin.us)*")

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        except PermissionError:
            raise PermissionError(f"Cannot write to {path}. Check file permissions.")

    def _export_json(
        self,
        path: Path,
        conversations: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]]
    ):
        """Export to JSON format."""
        export_data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'generator': 'ReadIn AI',
            'metadata': metadata or {},
            'conversations': conversations
        }

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        except PermissionError:
            raise PermissionError(f"Cannot write to {path}. Check file permissions.")

    def get_export_path(self, format: str = 'md', filename: Optional[str] = None) -> Path:
        """Get the path where a file would be exported.

        Useful for showing the user where the file will be saved before exporting.
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"conversation_{timestamp}"

        return self.default_directory / f"{filename}.{format}"

    def list_exports(self, format: Optional[str] = None) -> List[Path]:
        """List all exported files in the default directory.

        Args:
            format: Filter by format, or None for all formats

        Returns:
            List of export file paths, sorted by modification time (newest first)
        """
        if not self.default_directory.exists():
            return []

        if format:
            pattern = f"*.{format}"
        else:
            patterns = [f"*.{fmt}" for fmt in self.SUPPORTED_FORMATS]
            files = []
            for pattern in patterns:
                files.extend(self.default_directory.glob(pattern))
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return files

        files = list(self.default_directory.glob(pattern))
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def delete_export(self, path: Path) -> bool:
        """Delete an exported file.

        Args:
            path: Path to the file to delete

        Returns:
            True if deleted, False if failed or file doesn't exist
        """
        try:
            if path.exists() and path.parent == self.default_directory:
                path.unlink()
                return True
        except Exception as e:
            print(f"Failed to delete export: {e}")
        return False


class ConversationRecorder:
    """Records conversation exchanges for later export."""

    def __init__(self, max_entries: int = 100):
        """Initialize the recorder.

        Args:
            max_entries: Maximum number of entries to keep in memory
        """
        self.max_entries = max_entries
        self.entries: List[Dict[str, Any]] = []
        self.session_start = datetime.now()
        self.meeting_app: Optional[str] = None

    def add_entry(self, question: str, answer: str):
        """Add a conversation entry.

        Args:
            question: The transcribed question
            answer: The AI-generated response
        """
        entry = {
            'question': question,
            'answer': answer,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }

        self.entries.append(entry)

        # Trim if over limit
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def set_meeting_app(self, app_name: str):
        """Set the detected meeting application name."""
        self.meeting_app = app_name

    def get_entries(self) -> List[Dict[str, Any]]:
        """Get all recorded entries."""
        return self.entries.copy()

    def get_metadata(self) -> Dict[str, Any]:
        """Get session metadata for export."""
        duration = datetime.now() - self.session_start
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            duration_str = f"{hours}h {minutes}m"
        elif minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{seconds}s"

        return {
            'date': self.session_start.strftime('%Y-%m-%d %H:%M'),
            'duration': duration_str,
            'meeting_app': self.meeting_app or 'Unknown',
            'total_exchanges': len(self.entries)
        }

    def clear(self):
        """Clear all recorded entries and reset session."""
        self.entries.clear()
        self.session_start = datetime.now()
        self.meeting_app = None

    def is_empty(self) -> bool:
        """Check if there are any recorded entries."""
        return len(self.entries) == 0
