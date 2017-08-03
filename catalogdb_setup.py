# Creats DB tables in Sqlite for Catalog Project


from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy import LargeBinary

Base = declarative_base()

# User table class to store user information
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(250), nullable=False, unique=True)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


# Catalog class to store catalog details.
class Catalog(Base):
    __tablename__ = 'catalog'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    catalogitems = relationship("CatalogItems", backref="catalog", cascade="all, delete-orphan")

    @property
    def serialize(self):
        return{
            'name': self.name,
            'id': self.id,
            }


#CatalogItems class to store items for a particular catalog.
class CatalogItems(Base):
    __tablename__ = 'catalog_items'
    id = Column(Integer, primary_key=True)
    itemname = Column(String, nullable=False, unique=True)
    description = Column(String(250))
    addedTime = Column(DateTime, default=func.now())
    catalog_id = Column(Integer, ForeignKey('catalog.id'))
    picturename = Column(String(100))
    # picture = Column(LargeBinary)
    # # catalog = relationship(Catalog)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return{
            'id': self.id,
            'itemname': self.itemname,
            'description': self.description,
            }


engine = create_engine('sqlite:///catalogdata.db')
Base.metadata.create_all(engine)
