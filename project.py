from flask import Flask, render_template, request, redirect
from flask import jsonify, url_for, flash
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from catalogdb_setup import Base, Catalog, CatalogItems, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)
CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Application"


engine = create_engine('sqlite:///catalogdata.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# Check if user exists
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


# REST API call for list of catalogs
@app.route('/catalog.json')
def showCatalogJSONFile():
    categories = session.query(Catalog).all()
    return jsonify(categories=[c.serialize for c in categories])


# REST API call for list of items for a catalog
@app.route('/catalog/<int:catalogid>/items.json')
def showItemsJSONFile(catalogid):
    items = session.query(CatalogItems).filter_by(catalog_id=catalogid).all()
    return jsonify(items=[item.serialize for item in items])


@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Login through gmail account
@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the'
                                            'auth code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps('Token user id does not'
                                            ' match given user id'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps('Token client id does not'
                                            ' match given client id'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    stored_credentials = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already'
                                            'connected'), 200)
        response.headers['Content-Type'] = 'application/json'

    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    user_id = getUserID(data['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;">'
    flash("you are now logged in as %s" % login_session['username'])
    return output


@app.route('/logout')
def logout():
    if login_session['provider'] == 'facebook':
        fbdisconnect()
        del login_session['facebook_id']
    if login_session['provider'] == 'google':
        gdisconnect()
        del login_session['gplus_id']
        del login_session['access_token']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    del login_session['user_id']
    del login_session['provider']
    flash('You have been logged out')
    return redirect(url_for('showHomePage'))


# gmail disconnect called through logout function
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = ('https://accounts.google.com/o/oauth2/revoke?token=%s'
           % login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result.status == 200:
        response = make_response(json.dumps('Successfully disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Fail to revoke token user'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


# Login through facebook
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    app_id = (json.loads(open('fb_client_secret.json', 'r').read())
              ['web']['app_id'])
    app_secret = json.loads(
        open('fb_client_secret.json', 'r').read())['web']['app_secret']
    url = ('https://graph.facebook.com/oauth/access_token?grant_type='
           'fb_exchange_token'
           '&client_id=%s&client_secret=%s&fb_exchange_token=%s'
           % (app_id, app_secret, access_token))
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = ('https://graph.facebook.com/v2.8/me?access_token=%s&'
           'fields=name,id,email' % token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = ('https://graph.facebook.com/v2.8/me/picture?access_token=%s'
           '&redirect=0&height=200&width=200' % token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 90px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


# FB Logout function called through logout
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = ('https://graph.facebook.com/%s/permissions?access_token=%s'
           % (facebook_id, access_token))
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


# List of catalog and recently added items
@app.route('/')
@app.route('/home')
def showHomePage():
    catalog = session.query(Catalog).order_by(asc(Catalog.name))
    items = session.query(CatalogItems).order_by(desc(
                            CatalogItems.addedTime)).limit(10)
    return render_template('homepage.html', catalog=catalog, items=items)


# List of catalog items for a catalog
@app.route('/catalog/<string:catalogname>/items')
def getCatalogItems(catalogname):
    catalogList = session.query(Catalog).all()
    catalog = session.query(Catalog).filter_by(name=catalogname).one()
    items = session.query(CatalogItems).filter_by(catalog_id=catalog.id).all()
    return render_template('catalogitems.html', items=items,
                           catalog=catalog, catalogList=catalogList)


# Catalog item description
@app.route('/catalog/<string:catalogname>/<string:itemname>')
def getCatalogDesc(itemname, catalogname):
    item = session.query(CatalogItems).filter_by(itemname=itemname).first()
    return render_template('itemdescription.html', item=item,
                           catalogname=catalogname)


# Edit a catalog item
@app.route('/catalog/<string:itemname>/edit', methods=['GET', 'POST'])
def editCatalogItem(itemname):
    editItems = session.query(CatalogItems).filter_by(itemname=itemname).one()
    catalogList = session.query(Catalog).order_by(asc(Catalog.name))
    if request.method == 'POST':
        catalogname = session.query(Catalog).filter_by(
                                    id=editItems.catalog_id).one()
        editItems.name = request.form['title']
        editItems.description = request.form['description']
        catalogList.name = request.form['category']
        return redirect(url_for('getCatalogDesc', catalogname=catalogList.name,
                                itemname=editItems.name))
    else:
        return render_template('editcatalogitem.html', editCatalog=editItems,
                               catalogList=catalogList, itemname=itemname)


# Ddelete a catalog item
@app.route('/catalog/<string:itemname>/delete', methods=['GET', 'POST'])
def deleteCatalogItem(itemname):
    if request.method == 'GET':
        return render_template('deleteitem.html', itemname=itemname)
    else:
        itemDelete = session.query(CatalogItems).filter_by(
                    itemname=itemname).one()
        session.delete(itemDelete)
        session.commit()
        flash('Catalog item has been deleted')
        return redirect(url_for('showHomePage'))


# Add a catalog
@app.route('/addCatalog', methods=['GET', 'POST'])
def addCatalog():
    if request.method == 'GET':
        return render_template('addcatalog.html')
    else:
        if not request.form['catalogname']:
            flash('Please add catalog name')
            return redirect(url_for('addCatalog'))
        catalog = Catalog(name=request.form['catalogname'])
        session.add(catalog)
        session.commit()
        flash("Catalog has been added")
        return redirect(url_for('showHomePage'))


# Add a catalog item
@app.route('/<string:catalog>/addCatalogItem', methods=['GET', 'POST'])
def addCatalogItem(catalog):
    if request.method == 'GET':
        return render_template('addcatalogitem.html', catalog=catalog)
    else:
        if not request.form['itemname']:
            flash('Please add itemname')
            return redirect(url_for('addCatalogItem', catalog=catalog))
        if not request.form['description']:
            flash('Please add description')
            return redirect(url_for('addCatalogItem', catalog=catalog))
        catalogid = session.query(Catalog).filter_by(
                    name=request.form['catalogname']).first()
        catalogitems = CatalogItems(itemname=request.form['itemname'],
                                    description=request.form['description'],
                                    catalog_id=catalogid.id)
        session.add(catalogitems)
        session.commit()
        return redirect(url_for('showHomePage'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
