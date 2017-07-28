from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()

class Catalog(Base):
	__tablename__ = 'catalog'

	id = Column(Integer, primary_key=True)
	name = Column(String, nullable=False)

	@property
	def serialize(self):
		return{
		'name':self.name,
		'id':self.id,
		}

class CatalogItems(Base):
	__tablename__ = 'catalog_items'

	id = Column(Integer, primary_key=True)
	itemname = Column(String, nullable=False)
	description=Column(String(250))
	addedTime = Column(DateTime, default = func.now())
	catalog_id = Column(Integer, ForeignKey('catalog.id'))
	catalog = relationship(Catalog)

	@property
	def serialize(self):
		return{
		'id':self.id,
		'name':self.name,
		'description':self.description,
		}

engine = create_engine('sqlite:///catalogdata.db')
Base.metadata.create_all(engine)
