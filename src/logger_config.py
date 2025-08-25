"""
Centralized logging configuration for the entire application
Smart logging setup with console + file output and log location tracking
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from config.settings import LOGS_DIR, LOG_LEVEL

class ProjectLogger:
    """Centralized logger configuration"""
    
    _initialized = False
    _log_files = {}  # Track where logs are stored
    
    @classmethod
    def setup_logging(cls, component_name: str = "main") -> logging.Logger:
        """
        Setup logging for a component with unified configuration
        
        Args:
            component_name: Name of the component (e.g., 'phase1', 'ui', 'validator')
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(component_name)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # Ensure logs directory exists
        LOGS_DIR.mkdir(exist_ok=True)
        
        # Create component-specific log file
        log_file = LOGS_DIR / f"{component_name}.log"
        cls._log_files[component_name] = log_file
        
        # Configure logger
        logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
        
        # Console handler (with colors if possible)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # File handler 
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Formatters
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        console_handler.setFormatter(console_format)
        file_handler.setFormatter(file_format)
        
        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        # Log initialization
        if not cls._initialized:
            logger.info("Logging system initialized")
            logger.info(f"Logs directory: {LOGS_DIR}")
            logger.info(f"Log level: {LOG_LEVEL}")
            cls._initialized = True
        
        logger.debug(f"Logger configured for component: {component_name}")
        return logger
    
    @classmethod
    def get_log_files_info(cls) -> dict:
        """Get information about all log files"""
        info = {
            "logs_directory": str(LOGS_DIR),
            "log_files": {}
        }
        
        for component, log_file in cls._log_files.items():
            if log_file.exists():
                stat = log_file.stat()
                info["log_files"][component] = {
                    "path": str(log_file),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
        
        return info
    
    @classmethod
    def print_log_info(cls):
        """Print information about log files"""
        info = cls.get_log_files_info()
        
        print(f"\n📊 LOGGING INFORMATION:")
        print(f"📁 Logs directory: {info['logs_directory']}")
        
        if info["log_files"]:
            print(f"📝 Active log files:")
            for component, file_info in info["log_files"].items():
                size_mb = file_info["size_bytes"] / (1024 * 1024)
                print(f"  • {component}: {file_info['path']} ({size_mb:.2f} MB)")
        else:
            print("📝 No log files created yet")


def get_logger(component_name: str) -> logging.Logger:
    """
    Convenience function to get a configured logger
    
    Usage:
        from src.logger_config import get_logger
        logger = get_logger('phase1')
        logger.info("This is logged!")
    """
    return ProjectLogger.setup_logging(component_name)