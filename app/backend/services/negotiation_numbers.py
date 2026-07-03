import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.negotiation_numbers import Negotiation_numbers

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Negotiation_numbersService:
    """Service layer for Negotiation_numbers operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Negotiation_numbers]:
        """Create a new negotiation_numbers"""
        try:
            obj = Negotiation_numbers(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created negotiation_numbers with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating negotiation_numbers: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Negotiation_numbers]:
        """Get negotiation_numbers by ID"""
        try:
            query = select(Negotiation_numbers).where(Negotiation_numbers.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching negotiation_numbers {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of negotiation_numberss"""
        try:
            query = select(Negotiation_numbers)
            count_query = select(func.count(Negotiation_numbers.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Negotiation_numbers, field):
                        query = query.where(getattr(Negotiation_numbers, field) == value)
                        count_query = count_query.where(getattr(Negotiation_numbers, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Negotiation_numbers, field_name):
                        query = query.order_by(getattr(Negotiation_numbers, field_name).desc())
                else:
                    if hasattr(Negotiation_numbers, sort):
                        query = query.order_by(getattr(Negotiation_numbers, sort))
            else:
                query = query.order_by(Negotiation_numbers.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching negotiation_numbers list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Negotiation_numbers]:
        """Update negotiation_numbers"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Negotiation_numbers {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated negotiation_numbers {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating negotiation_numbers {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete negotiation_numbers"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Negotiation_numbers {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted negotiation_numbers {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting negotiation_numbers {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Negotiation_numbers]:
        """Get negotiation_numbers by any field"""
        try:
            if not hasattr(Negotiation_numbers, field_name):
                raise ValueError(f"Field {field_name} does not exist on Negotiation_numbers")
            result = await self.db.execute(
                select(Negotiation_numbers).where(getattr(Negotiation_numbers, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching negotiation_numbers by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Negotiation_numbers]:
        """Get list of negotiation_numberss filtered by field"""
        try:
            if not hasattr(Negotiation_numbers, field_name):
                raise ValueError(f"Field {field_name} does not exist on Negotiation_numbers")
            result = await self.db.execute(
                select(Negotiation_numbers)
                .where(getattr(Negotiation_numbers, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Negotiation_numbers.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching negotiation_numberss by {field_name}: {str(e)}")
            raise