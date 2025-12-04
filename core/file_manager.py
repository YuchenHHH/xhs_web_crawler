"""
File Management Utilities
Handles directory creation, file naming, and data persistence
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict
from playwright.async_api import Page


class FileManager:
    """
    Manages output directory structure and file saving
    """

    @staticmethod
    def create_output_directory(keyword: str) -> str:
        """
        Create timestamped output directory

        Format: output/{keyword}_{timestamp}/
        Example: output/番茄炒蛋_20251203_143022/

        Args:
            keyword: Search keyword for directory naming

        Returns:
            Absolute path to created directory
        """
        # Create timestamp string
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sanitize keyword for directory name (remove special chars)
        safe_keyword = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in keyword)
        safe_keyword = safe_keyword.strip().replace(' ', '_')

        # Create directory path
        base_dir = Path("output")
        output_dir = base_dir / f"{safe_keyword}_{timestamp}"

        # Create directory (including parent if needed)
        output_dir.mkdir(parents=True, exist_ok=True)

        return str(output_dir.absolute())

    @staticmethod
    def get_note_filename(base_dir: str, note_index: int, extension: str) -> str:
        """
        Generate standardized filename for note files

        Format: note_{index:02d}.{extension}
        Example: note_01.png, note_01.json

        Args:
            base_dir: Base output directory
            note_index: Index of the note (0-based)
            extension: File extension (without dot)

        Returns:
            Absolute file path
        """
        filename = f"note_{note_index + 1:02d}.{extension}"
        filepath = Path(base_dir) / filename
        return str(filepath.absolute())

    @staticmethod
    async def save_screenshot(page: Page, filepath: str) -> bool:
        """
        Save current viewport screenshot

        Args:
            page: Playwright Page object
            filepath: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Take screenshot (current viewport only, not full page)
            await page.screenshot(
                path=filepath,
                type="png",
                full_page=False
            )

            # Verify file was created
            if Path(filepath).exists():
                file_size_kb = Path(filepath).stat().st_size / 1024
                print(f"   - 📸 Screenshot saved: {Path(filepath).name} ({file_size_kb:.1f} KB)")
                return True
            else:
                print(f"   - ❌ Screenshot file not created: {filepath}")
                return False

        except Exception as e:
            print(f"   - ❌ Failed to save screenshot: {e}")
            return False

    @staticmethod
    def save_json(data: Dict, filepath: str) -> bool:
        """
        Save structured data as formatted JSON

        Args:
            data: Dictionary to save
            filepath: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Write JSON with nice formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Verify file was created
            if Path(filepath).exists():
                file_size_kb = Path(filepath).stat().st_size / 1024
                print(f"   - 💾 JSON saved: {Path(filepath).name} ({file_size_kb:.1f} KB)")
                return True
            else:
                print(f"   - ❌ JSON file not created: {filepath}")
                return False

        except Exception as e:
            print(f"   - ❌ Failed to save JSON: {e}")
            return False

    @staticmethod
    def save_metadata(base_dir: str, metadata: Dict) -> str:
        """
        Save session metadata

        Saved as: {base_dir}/metadata.json

        Args:
            base_dir: Base output directory
            metadata: Metadata dictionary (keyword, timestamp, stats, etc.)

        Returns:
            Path to saved metadata file, or empty string on failure
        """
        try:
            filepath = Path(base_dir) / "metadata.json"

            # Add timestamp if not present
            if "created_at" not in metadata:
                metadata["created_at"] = datetime.now().isoformat()

            # Write metadata
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            print(f"   - 📋 Metadata saved: {filepath.name}")
            return str(filepath.absolute())

        except Exception as e:
            print(f"   - ❌ Failed to save metadata: {e}")
            return ""
