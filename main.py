from fastapi import FastAPI
import requests
import json
import hashlib
from pydantic import BaseModel
import mysql.connector

app = FastAPI()
url = 'https://suitecrmdemo.dtbc.eu/service/v4/rest.php'
session = {'sessId': None}


class PhoneWork(BaseModel):
  name: str
  value: str


class FirstName(BaseModel):
  name: str
  value: str


class LastName(BaseModel):
  name: str
  value: str


class NameValueList(BaseModel):
  phone_work: PhoneWork
  first_name: FirstName
  last_name: LastName


class Lead(BaseModel):
  id: str
  module_name: str
  name_value_list: NameValueList


def restRequest(method, arguments):
  post = {
    "method": method,
    "input_type": "JSON",
    "response_type": "JSON",
    "rest_data": json.dumps(arguments),
  }
  result = requests.post(url, data=post)
  return result.json()

# Conectar a la base de datos MySQL en el contenedor de Docker
mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="suiteCRM",
  port=3306,
  database="mydatabase"
)
mycursor = mydb.cursor()

def createTable():
  # Crear una tabla "leads" con los campos especificados
  mycursor.execute("CREATE TABLE IF NOT EXISTS leads (first_name VARCHAR(255), last_name VARCHAR(255), phone_work VARCHAR(255))")

def insert(first_name, last_name, phone_work):
  # Insertar un registro en la tabla "leads"
  sql = "INSERT INTO leads (first_name, last_name, phone_work) VALUES (%s, %s, %s)"
  val = (first_name, last_name, phone_work)
  mycursor.execute(sql, val)
  mydb.commit()

# Default root endpoint
@app.get("/")
async def root():
  return {"message": "Hello world"}


@app.get("/login")
async def login(username: str = 'Demo', password: str = 'Demo'):
  userAuth = {
    'user_name': username,
    'password': hashlib.md5(password.encode()).hexdigest(),
  }
  appName = 'My SuiteCRM REST Client'
  nameValueList = []

  args = {
    'user_auth': userAuth,
    'application_name': appName,
    'name_value_list': nameValueList,
  }

  result = restRequest('login', args)
  sessId = result['id']
  session['sessId'] = sessId

  createTable()
  return result


@app.post("/leads")
async def getDataLeads() -> list[Lead]:

  if session['sessId'] is None: return "you must login first"

  entry_args = {
    'session': session['sessId'],
    'module_name': 'Leads',
    'query': "leads.id IS NOT NULL",
    'order_by': '',
    'offset': 0,
    'select_fields': ['phone_work', 'first_name', 'last_name'],
    'max_results': 1,
    'deleted': 0
  }

  result = restRequest('get_entry_list', entry_args)
  entry_args['max_results'] = result['total_count']
  result = restRequest('get_entry_list', entry_args)

  def save_lead(lead: Lead):
    insert(
      str(lead.name_value_list.first_name.value),
      str(lead.name_value_list.last_name.value),
      str(lead.name_value_list.phone_work.value)
    )
    return lead

  leads = [save_lead(Lead(**lead)) for lead in result['entry_list']]
  return leads
