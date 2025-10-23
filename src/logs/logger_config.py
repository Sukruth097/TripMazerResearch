"""
Centralized logging configuration for TripMazer agents and services.

This module provides a unified logging setup that can be used across
all agents, tools, and services in the TripMazer application.
"""

import os
import logging
from datetime import datetime
from typing import Optional


class LoggerConfig:
    """Centralized logger configuration and management."""
    
    # Class-level storage for loggers
    _loggers = {}
    # Create timestamped log directory to keep logs organized
    _log_timestamp = datetime.now().strftime('%m_%d_%Y_%H_%M_%S')
    _logs_base_dir = "Optimizer logs"
    _logs_dir = os.path.join(_logs_base_dir, _log_timestamp)
    
    @classmethod
    def setup_logger(
        cls, 
        name: str, 
        enable_console: bool = True,
        enable_file: bool = True,
        log_level: int = logging.INFO,
        execution_id: Optional[str] = None
    ) -> logging.Logger:
        """
        Setup and configure a logger with file and console handlers.
        
        Args:
            name: Logger name (typically module or class name)
            enable_console: Whether to enable console output
            enable_file: Whether to enable file logging
            log_level: Logging level (default: INFO)
            execution_id: Optional execution ID for execution-specific logs
            
        Returns:
            Configured logger instance
        """
        # Return existing logger if already configured
        if name in cls._loggers:
            return cls._loggers[name]
        
        # Create logs directory if it doesn't exist
        os.makedirs(cls._logs_dir, exist_ok=True)
        
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        
        # Clear existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        # Create formatters with custom format
        detailed_formatter = logging.Formatter(
            "[%(asctime)s]: %(levelname)s -['User_Name':Sukruth]: -['filename']:%(filename)s -['function_name']:%(funcName)s -['line_no']:%(lineno)d - %(message)s "
        )
        
        simple_formatter = logging.Formatter(
            "[%(asctime)s]: %(levelname)s - %(message)s "
        )
        
        # Console handler for simple logs
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(simple_formatter)
            logger.addHandler(console_handler)
        
        # File handler for detailed logs
        if enable_file:
            # Main detailed log file
            file_handler = logging.FileHandler(
                f'{cls._logs_dir}/{name.lower()}_detailed.log', 
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
            
            # Execution-specific log file (if execution_id provided)
            if execution_id:
                execution_handler = logging.FileHandler(
                    f'{cls._logs_dir}/execution_{execution_id}.log', 
                    encoding='utf-8'
                )
                execution_handler.setLevel(log_level)
                execution_handler.setFormatter(detailed_formatter)
                logger.addHandler(execution_handler)
        
        # Store logger for reuse
        cls._loggers[name] = logger
        
        logger.info("=" * 80)
        logger.info(f"LOGGER INITIALIZED: {name}")
        logger.info("=" * 80)
        
        return logger
    
    @classmethod
    def log_tool_output(cls, tool_name: str, output: str, execution_id: str):
        """
        Log full tool output to a separate file.
        
        Args:
            tool_name: Name of the tool
            output: Tool output to log
            execution_id: Execution ID for the log file
        """
        try:
            tool_log_file = f"{cls._logs_dir}/tool_outputs_{execution_id}.log"
            
            with open(tool_log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"TOOL: {tool_name.upper()}\n")
                f.write(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*80}\n")
                f.write(str(output))
                f.write(f"\n{'='*80}\n\n")
                
            # Get logger if available
            logger = cls._loggers.get('TripOptimizationAgent')
            if logger:
                logger.info(f"Full tool output logged to: {tool_log_file}")
                
        except Exception as e:
            print(f"Failed to log tool output: {e}")
    
    @classmethod
    def log_final_output(cls, final_result: dict, execution_id: str):
        """
        Log final agent output to a separate file.
        
        Args:
            final_result: Final result dictionary
            execution_id: Execution ID for the log file
        """
        try:
            final_log_file = f"{cls._logs_dir}/final_output_{execution_id}.log"
            
            with open(final_log_file, 'w', encoding='utf-8') as f:
                f.write(f"FINAL AGENT OUTPUT\n")
                f.write(f"Execution ID: {execution_id}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*100}\n\n")
                
                # Write combined result
                if final_result.get("combined_result"):
                    f.write("COMBINED RESULT:\n")
                    f.write(f"{'-'*50}\n")
                    f.write(str(final_result["combined_result"]))
                    f.write(f"\n{'-'*50}\n\n")
                
                # Write execution summary
                if final_result.get("execution_summary"):
                    f.write("EXECUTION SUMMARY:\n")
                    f.write(f"{'-'*50}\n")
                    f.write(str(final_result["execution_summary"]))
                    f.write(f"\n{'-'*50}\n\n")
                
                # Write state
                if final_result.get("state"):
                    f.write("FINAL STATE:\n")
                    f.write(f"{'-'*50}\n")
                    f.write(str(final_result["state"]))
                    f.write(f"\n{'-'*50}\n")
            
            # Get logger if available
            logger = cls._loggers.get('TripOptimizationAgent')
            if logger:
                logger.info(f"Final agent output logged to: {final_log_file}")
                
        except Exception as e:
            print(f"Failed to log final output: {e}")
    
    @classmethod
    def get_logger(cls, name: str) -> Optional[logging.Logger]:
        """
        Get an existing logger by name.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance if exists, None otherwise
        """
        return cls._loggers.get(name)
    
    @classmethod
    def set_logs_directory(cls, logs_dir: str):
        """
        Set custom logs directory.
        
        Args:
            logs_dir: Path to logs directory
        """
        cls._logs_dir = logs_dir
        os.makedirs(cls._logs_dir, exist_ok=True)


def get_agent_logger(execution_id: Optional[str] = None) -> logging.Logger:
    """
    Convenience function to get a pre-configured agent logger.
    
    Args:
        execution_id: Optional execution ID for execution-specific logging
        
    Returns:
        Configured logger for agent
    """
    return LoggerConfig.setup_logger(
        name='TripOptimizationAgent',
        enable_console=True,
        enable_file=True,
        log_level=logging.INFO,
        execution_id=execution_id
    )


def get_tool_logger(tool_name: str) -> logging.Logger:
    """
    Convenience function to get a pre-configured tool logger.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Configured logger for tool
    """
    return LoggerConfig.setup_logger(
        name=f'Tool_{tool_name}',
        enable_console=True,
        enable_file=True,
        log_level=logging.INFO
    )


def get_service_logger(service_name: str) -> logging.Logger:
    """
    Convenience function to get a pre-configured service logger.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Configured logger for service
    """
    return LoggerConfig.setup_logger(
        name=f'Service_{service_name}',
        enable_console=True,
        enable_file=True,
        log_level=logging.INFO
    )
