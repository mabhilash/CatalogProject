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


# CLIENT_ID = json.loads(
#     open('client_secrets.json', 'r').read())['web']['client_id']
# APPLICATION_NAME = "Restaurant Menu Application"


#Connect to Database and create database session
engine = create_engine('sqlite:///catalogdata.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def showHomePage():
  catalog = session.query(Catalog).order_by(asc(Catalog.name))
  items = session.query(CatalogItems).order_by(desc(CatalogItems.addedTime)).limit(10)
  return render_template('homepage.html',catalog = catalog, items = items)

@app.route('/catalog/<string:catalogname>/items')
def getCatalogItems(catalogname):
  catalog = session.query(Catalog).filter_by(name= catalogname).one()
  items = session.query(CatalogItems).filter_by(catalog_id = catalog.id)
  return render_template('catalogitems.html', items = items,catalog=catalog)


@app.route('/catalog/<string:catalogname>/<string:itemname>')
def getCatalogDesc(itemname, catalogname):
  itemDesc = session.query(CatalogItems).filter_by(name = itemname)
  return render_template('itemdescription.html', itemDesc = itemDesc, catalogname = catalogname)


@app.route('/catalog/<string:itemname>/edit', methods=['GET','POST'])
def editCatalogItem(itemname):
  editItems = session.query(CatalogItems).filter_by(name = itemname).one()
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
    itemDelete = session.query(CatalogItems).filter_by(name= itemname).one()
    session.delete(itemDelete)
    session.commit()
    return redirect(url_for('showHomePage'))


if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
