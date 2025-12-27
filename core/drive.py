import os
import shutil
import logging
from typing import Optional
from core.config import Config

logger = logging.getLogger("DriveExporter")

class DriveExporter:
    """
    Centralized utility for exporting files to the configured Google Drive path.
    Encapsulates path checking, error handling, and logging.
    """

    @staticmethod
    def export_file(source_path: str, target_filename: Optional[str] = None) -> bool:
        """
        Exports a local file to the Google Drive folder defined in Config.
        
        Args:
            source_path (str): The absolute or relative path to the local file to export.
            target_filename (str, optional): The name of the file in the destination folder. 
                                             If None, uses the basename of source_path.

        Returns:
            bool: True if export succeeded, False otherwise.
        """
        drive_path = Config.LOCAL_DRIVE_PATH
        if not drive_path:
            logger.debug("Drive export skipped: LOCAL_DRIVE_PATH not configured.")
            return False

        if not os.path.exists(drive_path):
            logger.warning(f"Drive export skipped: Path not found: {drive_path}")
            return False

        if not os.path.exists(source_path):
            logger.error(f"Export failed: Source file not found: {source_path}")
            return False

        # Determine destination
        final_name = target_filename or os.path.basename(source_path)
        dest_path = os.path.join(drive_path, final_name)

        # Ensure destination directory exists
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        except Exception as e:
            logger.error(f"Export failed: Could not create directory {os.path.dirname(dest_path)}: {e}")
            return False

        try:
            shutil.copy(source_path, dest_path)
            logger.info(f"Successfully exported {os.path.basename(source_path)} to {drive_path} as {final_name}")
            return True
        except PermissionError:
            logger.error(f"Export failed: Permission denied writing to {dest_path}. file might be open.")
            return False
        except Exception as e:
            logger.error(f"Export failed for {source_path}: {e}")
            return False
