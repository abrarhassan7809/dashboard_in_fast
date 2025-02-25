from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, Boolean, Float
from database_config.db_creation import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, unique=False, nullable=False)
    last_name = Column(String, unique=False, nullable=False)
    email = Column(String, unique=False, nullable=False)
    password = Column(String, unique=False, nullable=False)
    confirm_password = Column(String, unique=False, nullable=False)
    img_path = Column(String, nullable=True)
    user_token = Column(String, nullable=True)

    created_at = Column(TIMESTAMP, nullable=False)
    is_admin = Column(Boolean, default=False)
    user_status = Column(Boolean, default=False)


# ======== Products ========
class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, unique=False, nullable=False)
    img_path = Column(String, unique=False, nullable=True)

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)


class Products(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String, unique=False, nullable=False)
    product_name = Column(String, unique=False, nullable=False)
    product_description = Column(String, unique=False, nullable=True)
    product_image1 = Column(String, unique=False, nullable=True)
    product_image2 = Column(String, unique=False, nullable=True)
    product_image3 = Column(String, unique=False, nullable=True)
    product_quantity = Column(Integer, nullable=False)
    purchase_price = Column(Float, nullable=True)
    sale_price = Column(Float, nullable=False)

    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)


# ======== Order ========
class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True, autoincrement=True)
    discount = Column(Float, nullable=False)
    # subtotal = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    order_status = Column(String, default='Order', nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    order_status_id = Column(Integer, ForeignKey('order_status.id', ondelete='CASCADE'), nullable=False)


class OrderItem(Base):
    __tablename__ = 'orderitem'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order = Column(Integer, default=1, nullable=False)
    barcode = Column(String, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    discount = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)


class OrderStatus(Base):
    __tablename__ = 'order_status'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_paid = Column(String, unique=False, nullable=False)
    order_status = Column(String, unique=False, nullable=False)

    order_id = Column(Integer, ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
