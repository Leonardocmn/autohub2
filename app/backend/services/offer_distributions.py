import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.offer_distributions import Offer_distributions

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Offer_distributionsService:
    """Service layer for Offer_distributions operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Offer_distributions]:
        """Create a new offer_distributions"""
        try:
            obj = Offer_distributions(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created offer_distributions with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating offer_distributions: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Offer_distributions]:
        """Get offer_distributions by ID"""
        try:
            query = select(Offer_distributions).where(Offer_distributions.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching offer_distributions {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of offer_distributionss"""
        try:
            query = select(Offer_distributions)
            count_query = select(func.count(Offer_distributions.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Offer_distributions, field):
                        query = query.where(getattr(Offer_distributions, field) == value)
                        count_query = count_query.where(getattr(Offer_distributions, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Offer_distributions, field_name):
                        query = query.order_by(getattr(Offer_distributions, field_name).desc())
                else:
                    if hasattr(Offer_distributions, sort):
                        query = query.order_by(getattr(Offer_distributions, sort))
            else:
                query = query.order_by(Offer_distributions.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching offer_distributions list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Offer_distributions]:
        """Update offer_distributions"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Offer_distributions {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated offer_distributions {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating offer_distributions {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete offer_distributions"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Offer_distributions {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted offer_distributions {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting offer_distributions {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Offer_distributions]:
        """Get offer_distributions by any field"""
        try:
            if not hasattr(Offer_distributions, field_name):
                raise ValueError(f"Field {field_name} does not exist on Offer_distributions")
            result = await self.db.execute(
                select(Offer_distributions).where(getattr(Offer_distributions, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching offer_distributions by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Offer_distributions]:
        """Get list of offer_distributionss filtered by field"""
        try:
            if not hasattr(Offer_distributions, field_name):
                raise ValueError(f"Field {field_name} does not exist on Offer_distributions")
            result = await self.db.execute(
                select(Offer_distributions)
                .where(getattr(Offer_distributions, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Offer_distributions.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching offer_distributionss by {field_name}: {str(e)}")
            raise