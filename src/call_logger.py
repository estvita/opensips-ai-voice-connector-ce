#!/usr/bin/env python3
"""
Call-specific logging utilities
"""

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


class CallLogger:
    """Manages call-specific logging"""
    
    def __init__(self, call_id, bot_id=None):
        """
        Initialize call logger
        
        :param call_id: Unique call identifier (e.g., B2B.502.79.1756047989.2127904424)
        :param bot_id: Bot identifier (optional)
        """
        self.call_id = call_id
        self.bot_id = bot_id or "unknown"
        self.logger = None
        self.log_file_path = None
        
    def setup(self):
        """Setup call-specific logger"""
        # Create directory structure
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = os.path.join("logs", today, f"bot_{self.bot_id}")
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log file path
        self.log_file_path = os.path.join(log_dir, f"call_{self.call_id}.log")
        
        # Create logger with unique name to prevent propagation to root logger
        logger_name = f"call_{self.call_id}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return self.logger
            
        # Create file handler
        file_handler = RotatingFileHandler(
            self.log_file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - tid: %(thread)d - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(file_handler)
        
        # Log call start
        self.logger.info(f"Call started - ID: {self.call_id}, Bot: {self.bot_id}")
        
        return self.logger
    
    def get_logger(self):
        """Get the call logger"""
        if not self.logger:
            self.setup()
        return self.logger
    
    def cleanup(self):
        """Cleanup logger handlers"""
        if self.logger:
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
            self.logger.info(f"Call ended - ID: {self.call_id}")
    
    def get_log_file_path(self):
        """Get the log file path"""
        return self.log_file_path


def create_call_logger(call_id, bot_id=None):
    """
    Factory function to create call logger
    
    :param call_id: Unique call identifier
    :param bot_id: Bot identifier (optional)
    :return: CallLogger instance
    """
    return CallLogger(call_id, bot_id)
