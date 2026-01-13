import asyncio
import logging
from typing import Dict, List, Any, Optional

from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage

from database import DatabaseManager

logger = logging.getLogger(__name__)


class SimpleMemoryManager:
    """
    Simplified memory manager that loads chat history from database 
    and provides it to ConversationBufferMemory for LangChain agents.
    
    This focuses on just session ID, user messages, and responses.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def load_chat_history_to_memory(
        self, 
        session_id: str, 
        memory: ConversationBufferMemory,
        limit: int = 50
    ) -> None:
        """
        Load chat history from database into ConversationBufferMemory.
        
        Args:
            session_id: The chat session ID
            memory: ConversationBufferMemory instance to load messages into
            limit: Maximum number of messages to load
        """
        try:
            # Get chat history from database
            async with self.db_manager.get_connection() as conn:
                rows = await conn.fetch("""
                    MATCH (cs:ChatSession {id: $1})-[:HAS_MESSAGE]->(m:Message)
                    RETURN m.message_type as message_type, m.content as content, m.created_at as created_at
                    ORDER BY m.created_at ASC
                    LIMIT $2
                """, session_id, limit)
                
                # Clear existing memory first
                memory.clear()
                
                # Load messages into memory
                for row in rows:
                    if row['message_type'] == 'user':
                        memory.chat_memory.add_message(HumanMessage(content=row['content']))
                    elif row['message_type'] == 'assistant':
                        memory.chat_memory.add_message(AIMessage(content=row['content']))
                
                logger.info(f"Loaded {len(rows)} messages into memory for session {session_id}")
                
        except Exception as e:
            logger.error(f"Error loading chat history to memory: {e}")
    
    async def get_recent_messages(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[BaseMessage]:
        """
        Get recent messages from database as BaseMessage objects.
        
        Args:
            session_id: The chat session ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of BaseMessage objects
        """
        try:
            async with self.db_manager.get_connection() as conn:
                rows = await conn.fetch("""
                    MATCH (cs:ChatSession {id: $1})-[:HAS_MESSAGE]->(m:Message)
                    RETURN m.message_type as message_type, m.content as content, m.created_at as created_at
                    ORDER BY m.created_at DESC
                    LIMIT $2
                """, session_id, limit)
                
                messages = []
                # Reverse to get chronological order
                for row in reversed(rows):
                    if row['message_type'] == 'user':
                        messages.append(HumanMessage(content=row['content']))
                    elif row['message_type'] == 'assistant':
                        messages.append(AIMessage(content=row['content']))
                
                return messages
                
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []
    
    async def get_message_count(self, session_id: str) -> int:
        """
        Get total message count for a session.
        
        Args:
            session_id: The chat session ID
            
        Returns:
            Total number of messages in the session
        """
        try:
            async with self.db_manager.get_connection() as conn:
                result = await conn.fetchrow("""
                    MATCH (cs:ChatSession {id: $1})-[:HAS_MESSAGE]->(m:Message)
                    RETURN COUNT(m) as count
                """, session_id)
                return result['count'] if result else 0
                
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0
    
    async def clear_session_history(self, session_id: str) -> bool:
        """
        Clear all chat messages for a session.
        
        Args:
            session_id: The chat session ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.execute("""
                    MATCH (cs:ChatSession {id: $1})-[:HAS_MESSAGE]->(m:Message)
                    DETACH DELETE m
                """, session_id)
                
                logger.info(f"Cleared chat history for session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing session history: {e}")
            return False
    
    def create_conversation_buffer_memory(
        self,
        memory_key: str = "chat_history",
        return_messages: bool = True,
        human_prefix: str = "Human",
        ai_prefix: str = "AI"
    ) -> ConversationBufferMemory:
        """
        Create a new ConversationBufferMemory instance with specified configuration.
        
        Args:
            memory_key: Key to store memory under in prompt template
            return_messages: Whether to return messages as objects or string
            human_prefix: Prefix for human messages
            ai_prefix: Prefix for AI messages
            
        Returns:
            Configured ConversationBufferMemory instance
        """
        return ConversationBufferMemory(
            memory_key=memory_key,
            return_messages=return_messages,
            human_prefix=human_prefix,
            ai_prefix=ai_prefix
        )