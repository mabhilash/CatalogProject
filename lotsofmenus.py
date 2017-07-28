from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from catalogdb_setup import Catalog, Base, CatalogItems
 
engine = create_engine('sqlite:///catalogdata.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

#Catalog

c1 = Catalog(name="Soccer")

session.add(c1)
session.commit()

item1 = CatalogItems(itemname = "Chelsea", description = "Best club in EPL", catalog = c1)

session.add(item1)
session.commit()

item2 = CatalogItems(itemname = "RealMadrid", description = "Best club in LaLiga", catalog = c1)

session.add(item2)
session.commit()



c2 = Catalog(name="Cricket")

session.add(c2)
session.commit()

item1 = CatalogItems(itemname = "India", description = "Best team in world", catalog = c2)

session.add(item1)
session.commit()


item2 = CatalogItems(itemname = "SouthAfrica", description = "Strong team in world", catalog = c2)

session.add(item2)
session.commit()


print "added catalog items!"

