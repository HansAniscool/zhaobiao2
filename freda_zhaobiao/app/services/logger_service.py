from ..models import SystemLog
from ..extensions import db
from datetime import datetime
import logging

class LoggerService:
    def __init__(self):
        self.logger = logging.getLogger('tender_app')
        self.logger.setLevel(logging.INFO)
        
        file_handler = logging.FileHandler('logs/app.log')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def log(self, level, message, module=None, traceback=None, user_id=None):
        log_entry = SystemLog(
            level=level,
            module=module,
            message=message,
            traceback=traceback,
            user_id=user_id
        )
        db.session.add(log_entry)
        db.session.commit()
        
        if level == 'ERROR':
            self.logger.error(message, exc_info=traceback)
        elif level == 'WARNING':
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def info(self, message, module=None, user_id=None):
        self.log('INFO', message, module, None, user_id)
    
    def warning(self, message, module=None, user_id=None):
        self.log('WARNING', message, module, None, user_id)
    
    def error(self, message, module=None, traceback=None, user_id=None):
        self.log('ERROR', message, module, traceback, user_id)
    
    def debug(self, message, module=None, user_id=None):
        self.log('DEBUG', message, module, None, user_id)

logger_service = LoggerService()
