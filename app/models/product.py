from app.db.session import Base
from sqlalchemy import Column, Integer, String, Boolean,ForeignKey,Text,LargeBinary
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy import text
from sqlalchemy.orm import relationship

class Shoes(Base):
    __tablename__="shoes"
    id=Column(Integer,primary_key=True,nullable=False)
    name=Column(String,nullable=False)
    price=Column(Integer,nullable=False)
    shoes_type=Column(String,nullable=False)
    product_image=Column(String,nullable=False)
    shoes_category=Column(String,nullable=False)
    shoes_stock=Column(Integer,server_default=text('0'))
    shoes_description=Column(String,server_default=text("''"))
    created_at=Column(TIMESTAMP(timezone=True),nullable=False,server_default=text('CURRENT_TIMESTAMP'))
    stripe_product_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
