from catalogdb_setup import User
from sqlalchemy import create_engine
from catalogdb_setup import Base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///catalogdata.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Creates a new user
def createUser(login_session):
    user = User(username=login_session['username'],
                email=login_session['email'], picture=login_session['picture'])
    session.add(user)
    session.commit()
    usrinfo = session.query(User).filter_by(email=login_session['email']).one()
    return usrinfo.id