from flask import Flask, render_template, request, redirect,jsonify, url_for, flash
app = Flask(__name__)

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from catalogdb_setup import Base, Catalog, CatalogItems

from flask import session as login_session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests


CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Application"


#Connect to Database and create database session
engine = create_engine('sqlite:///catalogdata.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#API ENDPOITS-JSON

@app.route('/catalog.json')
def showCatalogJSONFile():
  categories = session.query(Catalog).all()
  return jsonify(categories = [category.serialize for category in categories])

@app.route('/catalog/<int:catalogid>/items.json')
def showItemsJSONFile(catalogid):
  items = session.query(CatalogItems).filter_by(catalog_id = catalogid).all()
  return jsonify(items = [item.serialize for item in items])

@app.route('/login')
def login():
  state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
  login_session['state'] = state
  return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
  if request.args.get('state') != login_session['state']:
    print login_session['state']
    print request.args.get('state')
    response = make_response(json.dumps('Invalid state parameter'),401)
    response.headers['Content-Type'] = 'application/json'
    return response
  code = request.data
  try:
    oauth_flow = flow_from_clientsecrets('client_secret.json',scope= '')
    oauth_flow.redirect_uri = 'postmessage'
    credentials = oauth_flow.step2_exchange(code)
  except FlowExchangeError:
    response = make_response(json.dumps('Failed to upgrade the authorization code'),401)
    response.headers['Content-Type'] = 'application/json'
    return response
  access_token = credentials.access_token
  url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' %access_token)
  h = httplib2.Http()
  result = json.loads(h.request(url,'GET')[1])
  if result.get('error') is not None:
    response = make_response(json.dumps(result.get('error')),500)
    response.headers['Content-Type'] = 'application/json'
  gplus_id = credentials.id_token['sub']
  if result['user_id'] != gplus_id:
    response = make_response(json.dumps('Token user id does not match given user id'), 401)
    response.headers['Content-Type'] = 'application/json'
    return response
  if result['issued_to'] != CLIENT_ID:
    response = make_response(json.dumps('Token client id does not match given client id'), 401)
    response.headers['Content-Type'] = 'application/json'
    return response
  stored_credentials = login_session.get('access_token')
  stored_gplus_id = login_session.get('gplus_id')
  if stored_credentials is not None and gplus_id == stored_gplus_id:
    response = make_response(json.dumps('Current user is already connected'),200)
    response.headers['Content-Type'] = 'application/json'

  login_session['access_token'] = credentials.access_token
  login_session['gplus_id'] = gplus_id

  userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
  params = {'access_token':credentials.access_token, 'alt':'json'}
  answer = requests.get(userinfo_url, params=params)
  data = answer.json()

  login_session['username'] = data['name']
  login_session['picture'] = data['picture']
  login_session['email'] = data['email']

  output = ''
  output += '<h1>Welcome, '
  output += login_session['username']
  output += '!</h1>'
  output += '<img src="'
  output += login_session['picture']
  output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
  flash("you are now logged in as %s" % login_session['username'])
  print "done!"
  return output


@app.route('/gdisconnect')
def logout():
  print 'logged out'
  access_token = login_session.get('access_token')
  if access_token is None:
    response = make_response(json.dumps('Current user not connected'),401)
    response.headers['Content-Type'] = 'application/json'
    return response
  url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' %login_session['access_token']
  h = httplib2.Http()
  result = h.request(url,'GET')[0]
  print 'result is'
  print result
  # del login_session['access_token']
  # del login_session['gplus_id']
  # del login_session['username']
  # del login_session['email']
  # del login_session['picture']
  # print result
  if result.status == 200:
    del login_session['access_token']
    del login_session['gplus_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    response = make_response(json.dumps('Successfully disconnected'),200)
    response.headers['Content-Type']='application/json'
    return response
  else:
    response = make_response(json.dumps('Failed to revoke token for given user'),400)
    response.headers['Content-Type']='application/json'
    return response

@app.route('/')
@app.route('/home')
def showHomePage():
  catalog = session.query(Catalog).order_by(asc(Catalog.name))
  items = session.query(CatalogItems).order_by(desc(CatalogItems.addedTime)).limit(10)
  print login_session
  return render_template('homepage.html',catalog = catalog, items = items)

@app.route('/catalog/<string:catalogname>/items')
def getCatalogItems(catalogname):
  catalog = session.query(Catalog).filter_by(name= catalogname).one()
  print catalog.id
  items = session.query(CatalogItems).filter_by(catalog_id = catalog.id).all()
  print items
  for item in items:
    print item.itemname
  return render_template('catalogitems.html', items = items,catalog=catalog)


@app.route('/catalog/<string:catalogname>/<string:itemname>')
def getCatalogDesc(itemname, catalogname):
  item = session.query(CatalogItems).filter_by(itemname = itemname).first()
  return render_template('itemdescription.html', item = item, catalogname = catalogname)


@app.route('/catalog/<string:itemname>/edit', methods=['GET','POST'])
def editCatalogItem(itemname):
  editItems = session.query(CatalogItems).filter_by(itemname = itemname).one()
  catalogList = session.query(Catalog).order_by(asc(Catalog.name))
  print catalogList
  if request.method == 'POST':
    catalogname = session.query(Catalog).filter_by(id = editItems.catalog_id).one()
    print 'post method'
    editItems.name = request.form['title']
    editItems.description = request.form['description']
    catalogList.name = request.form['category']
    return redirect(url_for('getCatalogDesc',catalogname=catalogList.name,itemname=editItems.name))
  else:
    return render_template('editcatalogitem.html',editCatalog = editItems, catalogList = catalogList,
                           itemname = itemname)


@app.route('/catalog/<string:itemname>/delete', methods=['GET','POST'])
def deleteCatalogItem(itemname):
  if request.method == 'GET':
    return render_template('deleteitem.html', itemname=itemname)
  else:
    if request.form['cancel'] == 'cancel':
      item_catalogid = session.query(CatalogItems).filter_by(itemname=itemname).first()
      catalog = session.query(Catalog).filter_by(id=item_catalogid).first()
      catalogname=catalog.name
      return render_template('getCatalogDesc', itemname=itemname, catalogname=catalogname)
    else:
      itemDelete = session.query(CatalogItems).filter_by(itemname= itemname).one()
      session.delete(itemDelete)
      session.commit()
      return redirect(url_for('showHomePage'))


@app.route('/addCatalog', methods=['GET', 'POST'])
def addCatalog():
  if request.method == 'GET':
    # catalog = session.query(Catalog).order_by(asc(Catalog.name))
    return render_template('addcatalog.html')
  else:
    catalog = Catalog(name=request.form['catalogname'])
    session.add(catalog)
    session.commit()
    return redirect(url_for('showHomePage'))


@app.route('/<string:catalog>/addCatalogItem', methods=['GET','POST'])
def addCatalogItem(catalog):
  if request.method == 'GET':
    return render_template('addcatalogitem.html', catalog=catalog)
  else:
    print request.form['catalogname']
    catalogid = session.query(Catalog).filter_by(name=request.form['catalogname']).first()
    catalogitems = CatalogItems(itemname=request.form['itemname'], description=request.form['description'],catalog_id = catalogid.id)
    session.add(catalogitems)
    session.commit()
    return redirect(url_for('showHomePage'))
    # return redirect(url_for('getCatalogItems',catalogname = request.form['catalogname']))



if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
