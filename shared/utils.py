import hashlib
import re
import logging
from typing import Optional, Dict, Any
import redis
import json
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

def sanitize_title_for_table(title: str) -> str:
    """Sanitize title for use as database table name - create short, manageable names"""
    # Create a short hash-based table name
    # This ensures uniqueness while keeping names short and manageable
    
    # Create a hash of the full title for uniqueness
    title_hash = hashlib.md5(title.encode()).hexdigest()[:12].upper()
    
    # Extract first few meaningful words from title
    words = re.findall(r'[A-Za-z]+', title.upper())
    
    # Take first 2-3 meaningful words (skip common words)
    skip_words = {'THE', 'A', 'AN', 'AND', 'OR', 'BUT', 'FOR', 'OF', 'TO', 'IN', 'ON', 'AT', 'BY'}
    meaningful_words = [word for word in words if word not in skip_words and len(word) > 2]
    
    # Create prefix from first 2 words or use "BOOK" as fallback
    if len(meaningful_words) >= 2:
        prefix = meaningful_words[0][:4] + '_' + meaningful_words[1][:4]
    elif len(meaningful_words) >= 1:
        prefix = meaningful_words[0][:8]
    else:
        prefix = 'BOOK'
    
    # Combine prefix with hash to ensure uniqueness and keep it short
    # Format: PREFIX_HASH (e.g., "BIG_DATA_A1B2C3D4E5F6")
    sanitized = f"{prefix}_{title_hash}"
    
    # Ensure it's within PostgreSQL limits (63 chars) and reasonable length (max 25 chars)
    if len(sanitized) > 25:
        sanitized = sanitized[:25]
    
    return sanitized

def extract_category_id(subject: str) -> int:
    """Map subject to category ID"""
    category_mapping = {
        " Accounts & Savings": 1,
        "Loans": 2,
        "Cards": 3,
        "Investments": 4,
        "Business & Corporate Banking": 5,
        "Insurance (Bancassurance)": 6,
        "Digital & E-Banking": 7,
        "Payroll Services": 8,
        "General Information": 9
    }
    return category_mapping.get(subject.lower(), 7)  # Default to 'general'

class RedisManager:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[redis.Redis] = None

    def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Redis")

    def set_cache(self, key: str, value: Any, expire_seconds: int = 3600):
        """Set cache value with expiration"""
        if not self.client:
            return False
        try:
            serialized_value = json.dumps(value, default=str)
            return self.client.setex(key, expire_seconds, serialized_value)
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False

    def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        if not self.client:
            return None
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get cache: {e}")
            return None

    def delete_cache(self, key: str) -> bool:
        """Delete cache key"""
        if not self.client:
            return False
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete cache: {e}")
            return False

    def set_session(self, session_id: str, data: Dict[str, Any], expire_hours: int = 24):
        """Set session data"""
        expire_seconds = expire_hours * 3600
        return self.set_cache(f"session:{session_id}", data, expire_seconds)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        return self.get_cache(f"session:{session_id}")

    def extend_session(self, session_id: str, expire_hours: int = 24):
        """Extend session expiration"""
        if not self.client:
            return False
        try:
            expire_seconds = expire_hours * 3600
            return self.client.expire(f"session:{session_id}", expire_seconds)
        except Exception as e:
            logger.error(f"Failed to extend session: {e}")
            return False

# Global Redis instance
redis_manager: Optional[RedisManager] = None

def get_redis() -> RedisManager:
    """Get Redis manager instance"""
    global redis_manager
    if not redis_manager:
        redis_manager = RedisManager()
        redis_manager.connect()
    return redis_manager

def setup_logging(service_name: str, level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=f'%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'/app/logs/{service_name}.log', mode='a')
        ]
    )

def validate_file_type(mime_type: str) -> bool:
    """Validate if file type is supported"""
    supported_types = [
        'application/pdf',
        'text/plain',
        'text/markdown',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    return mime_type in supported_types

def generate_session_id() -> str:
    """Generate unique session ID"""
    import uuid
    return str(uuid.uuid4())

def format_timestamp(dt: datetime) -> str:
    """Format datetime for API responses"""
    return dt.isoformat()

def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime"""
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))