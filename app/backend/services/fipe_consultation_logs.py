import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.fipe_consultation_logs import Fipe_consultation_logs

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Fipe_consultation_logsService:
    """Service layer for Fipe_consultation_logs operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Fipe_consultation_logs]:
        """Create a new fipe_consultation_logs"""
        try:
            obj = Fipe_consultation_logs(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created fipe_consultation_logs with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating fipe_consultation_logs: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Fipe_consultation_logs]:
        """Get fipe_consultation_logs by ID"""
        try:
            query = select(Fipe_consultation_logs).where(Fipe_consultation_logs.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching fipe_consultation_logs {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of fipe_consultation_logss"""
        try:
            query = select(Fipe_consultation_logs)
            count_query = select(func.count(Fipe_consultation_logs.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Fipe_consultation_logs, field):
                        query = query.where(getattr(Fipe_consultation_logs, field) == value)
                        count_query = count_query.where(getattr(Fipe_consultation_logs, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Fipe_consultation_logs, field_name):
                        query = query.order_by(getattr(Fipe_consultation_logs, field_name).desc())
                else:
                    if hasattr(Fipe_consultation_logs, sort):
                        query = query.order_by(getattr(Fipe_consultation_logs, sort))
            else:
                query = query.order_by(Fipe_consultation_logs.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching fipe_consultation_logs list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Fipe_consultation_logs]:
        """Update fipe_consultation_logs"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Fipe_consultation_logs {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated fipe_consultation_logs {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating fipe_consultation_logs {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete fipe_consultation_logs"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Fipe_consultation_logs {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted fipe_consultation_logs {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting fipe_consultation_logs {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Fipe_consultation_logs]:
        """Get fipe_consultation_logs by any field"""
        try:
            if not hasattr(Fipe_consultation_logs, field_name):
                raise ValueError(f"Field {field_name} does not exist on Fipe_consultation_logs")
            result = await self.db.execute(
                select(Fipe_consultation_logs).where(getattr(Fipe_consultation_logs, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching fipe_consultation_logs by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Fipe_consultation_logs]:
        """Get list of fipe_consultation_logss filtered by field"""
        try:
            if not hasattr(Fipe_consultation_logs, field_name):
                raise ValueError(f"Field {field_name} does not exist on Fipe_consultation_logs")
            result = await self.db.execute(
                select(Fipe_consultation_logs)
                .where(getattr(Fipe_consultation_logs, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Fipe_consultation_logs.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching fipe_consultation_logss by {field_name}: {str(e)}")
            raise