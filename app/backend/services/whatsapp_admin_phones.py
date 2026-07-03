import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.whatsapp_admin_phones import Whatsapp_admin_phones

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Whatsapp_admin_phonesService:
    """Service layer for Whatsapp_admin_phones operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Whatsapp_admin_phones]:
        """Create a new whatsapp_admin_phones"""
        try:
            obj = Whatsapp_admin_phones(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created whatsapp_admin_phones with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating whatsapp_admin_phones: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Whatsapp_admin_phones]:
        """Get whatsapp_admin_phones by ID"""
        try:
            query = select(Whatsapp_admin_phones).where(Whatsapp_admin_phones.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching whatsapp_admin_phones {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of whatsapp_admin_phoness"""
        try:
            query = select(Whatsapp_admin_phones)
            count_query = select(func.count(Whatsapp_admin_phones.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Whatsapp_admin_phones, field):
                        query = query.where(getattr(Whatsapp_admin_phones, field) == value)
                        count_query = count_query.where(getattr(Whatsapp_admin_phones, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Whatsapp_admin_phones, field_name):
                        query = query.order_by(getattr(Whatsapp_admin_phones, field_name).desc())
                else:
                    if hasattr(Whatsapp_admin_phones, sort):
                        query = query.order_by(getattr(Whatsapp_admin_phones, sort))
            else:
                query = query.order_by(Whatsapp_admin_phones.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching whatsapp_admin_phones list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Whatsapp_admin_phones]:
        """Update whatsapp_admin_phones"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Whatsapp_admin_phones {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated whatsapp_admin_phones {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating whatsapp_admin_phones {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete whatsapp_admin_phones"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Whatsapp_admin_phones {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted whatsapp_admin_phones {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting whatsapp_admin_phones {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Whatsapp_admin_phones]:
        """Get whatsapp_admin_phones by any field"""
        try:
            if not hasattr(Whatsapp_admin_phones, field_name):
                raise ValueError(f"Field {field_name} does not exist on Whatsapp_admin_phones")
            result = await self.db.execute(
                select(Whatsapp_admin_phones).where(getattr(Whatsapp_admin_phones, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching whatsapp_admin_phones by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Whatsapp_admin_phones]:
        """Get list of whatsapp_admin_phoness filtered by field"""
        try:
            if not hasattr(Whatsapp_admin_phones, field_name):
                raise ValueError(f"Field {field_name} does not exist on Whatsapp_admin_phones")
            result = await self.db.execute(
                select(Whatsapp_admin_phones)
                .where(getattr(Whatsapp_admin_phones, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Whatsapp_admin_phones.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching whatsapp_admin_phoness by {field_name}: {str(e)}")
            raise