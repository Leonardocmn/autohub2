import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.whatsapp_conversations import Whatsapp_conversations

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Whatsapp_conversationsService:
    """Service layer for Whatsapp_conversations operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Whatsapp_conversations]:
        """Create a new whatsapp_conversations"""
        try:
            obj = Whatsapp_conversations(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created whatsapp_conversations with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating whatsapp_conversations: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Whatsapp_conversations]:
        """Get whatsapp_conversations by ID"""
        try:
            query = select(Whatsapp_conversations).where(Whatsapp_conversations.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching whatsapp_conversations {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of whatsapp_conversationss"""
        try:
            query = select(Whatsapp_conversations)
            count_query = select(func.count(Whatsapp_conversations.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Whatsapp_conversations, field):
                        query = query.where(getattr(Whatsapp_conversations, field) == value)
                        count_query = count_query.where(getattr(Whatsapp_conversations, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Whatsapp_conversations, field_name):
                        query = query.order_by(getattr(Whatsapp_conversations, field_name).desc())
                else:
                    if hasattr(Whatsapp_conversations, sort):
                        query = query.order_by(getattr(Whatsapp_conversations, sort))
            else:
                query = query.order_by(Whatsapp_conversations.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching whatsapp_conversations list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Whatsapp_conversations]:
        """Update whatsapp_conversations"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Whatsapp_conversations {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated whatsapp_conversations {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating whatsapp_conversations {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete whatsapp_conversations"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Whatsapp_conversations {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted whatsapp_conversations {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting whatsapp_conversations {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Whatsapp_conversations]:
        """Get whatsapp_conversations by any field"""
        try:
            if not hasattr(Whatsapp_conversations, field_name):
                raise ValueError(f"Field {field_name} does not exist on Whatsapp_conversations")
            result = await self.db.execute(
                select(Whatsapp_conversations).where(getattr(Whatsapp_conversations, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching whatsapp_conversations by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Whatsapp_conversations]:
        """Get list of whatsapp_conversationss filtered by field"""
        try:
            if not hasattr(Whatsapp_conversations, field_name):
                raise ValueError(f"Field {field_name} does not exist on Whatsapp_conversations")
            result = await self.db.execute(
                select(Whatsapp_conversations)
                .where(getattr(Whatsapp_conversations, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Whatsapp_conversations.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching whatsapp_conversationss by {field_name}: {str(e)}")
            raise