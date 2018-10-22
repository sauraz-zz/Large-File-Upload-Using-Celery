from flask import Flask, render_template, request, jsonify, url_for
from flask_celery import make_celery
from celery import group
from werkzeug import secure_filename
from celery.result import AsyncResult
import csv
import time
import json
import uuid
import ast
from elasticsearch import Elasticsearch, helpers
from datetime import datetime
from itertools import islice

es = Elasticsearch(['http://elasticsearch:9200'])

#es = Elasticsearch()

# Configuration

app = Flask(__name__)
#app.config['CELERY_RESULT_BACKEND'] = 'amqp://localhost//'
#app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'amqp://admin:mypass@0.0.0.0:5672//'
app.config['CELERY_BROKER_URL'] = 'redis://redis:6379/0'
app.config['CELERY_ACCEPT_CONTENT'] = ['json','application/text']


celery = make_celery(app)

# Home Page

@app.route('/')
def hello_world():
    return render_template('upload.html')

#Uploader Page

@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
	if request.method == 'POST':
		transaction_id = uuid.uuid1()
		print(str(transaction_id))
		f = request.files['file']
		filename = secure_filename(f.filename)
		f.save(filename)
		settings = {
			"mappings" : {
				"sales" : {
					"properties" : {
						"transaction_id" : {
							"type" : "keyword"
						}
					}
				}
			}
		}
		es.indices.create(index="docs",ignore=400, body=json.dumps(settings))
		message = 'Processing File. It may take more time depending on the size of the file'
		task = readCsv.delay(filename,transaction_id)

		insert_taskId(str(task.id),str(transaction_id))
		return render_template('status.html',message=message,transaction_id=transaction_id)
	return '404 - go to home page'

# Stop Upload

@app.route('/cancel', methods=['POST'])
def cancelUpload():
	print('transaction_id - '+request.form.get('transaction_id', 'null'))
	
	query = {
		"query": {
			"constant_score" : {
				"filter" : {
					"term": {
							"transaction_id":request.form.get('transaction_id', 'null')
					}
				}
			}
		}
	}
	result = es.search(index="logs", doc_type='sales', body=json.dumps(query))
	print(result)
	if result['hits']['total'] != 0 :
		task_id = result['hits']['hits'][0]['_source']['task_id']
		print(task_id)
		transaction_id = result['hits']['hits'][0]['_source']['transaction_id']
		res = celery.control.revoke(task_id, terminate=True)
	else :
		transaction_id = 'null'

	message = ''
	if res == 'None' :
		message = 'Task completed or Revoked Already'
	else :
		message = 'Successfully Revoked'

	return render_template('status.html',message=message,transaction_id=transaction_id)

# Delete Data of transaction

@app.route('/delete', methods=['POST'])
def deleteUpload():
	transaction_id = request.form.get('transaction_id', 'null')
	if transaction_id == 'null' :
		message = ' transaction_id is null. Delete manually'
	else :
		delete_upload.delay(0,transaction_id)
		message = 'Delete successful'
	return render_template('status.html',message=message,transaction_id=transaction_id)

#Celery Tasks

@celery.task(name='server.readCsv')
def readCsv(filename,transaction_id):
	limit = 1000
	csv_rows = []
	with open(filename, 'r') as csvfile:
		title = next_n_lines(csvfile,1,[])
		result = next_n_lines(csvfile,limit,title)
		while result :
			uploadChunk.delay(result,transaction_id)
			result = next_n_lines(csvfile,limit,title)


def next_n_lines(file_opened, N, title):
	
	rows = []

	if N == 1 :
		for x in islice(file_opened, N) :
			x = x.rstrip()
			rows = x.split(',')
		return rows

	for x in islice(file_opened, N) :
		x = x.rstrip()
		temp = x.split(',')
		rows.extend([{title[i]:temp[i] for i in range(len(title))}])

	return ast.literal_eval(json.dumps(rows))

@celery.task(name='server.uploadChunk')
def uploadChunk(data,transaction_id):
    actions = [
      {
        "_index": "docs",
        "_type": "sales",
        "_source": {
            'data': row,
            'transaction_id': transaction_id,
            'timestamp': datetime.now()
        }
      }
      for row in data
    ]

    log = helpers.bulk(es, actions,True)
    print(log)


def insert_taskId(task_id,transaction_id):
	settings = {
	    "mappings" : {
	        "sales" : {
	            "properties" : {
	                "transaction_id" : {
	                    "type" : "keyword"
	                }
	            }
	        }
	    }
	}
	# create index
	es.indices.create(index="logs",ignore=400, body=json.dumps(settings))
	doc = {
		'transaction_id': transaction_id,
		'task_id': task_id,
		'doc_type': 'sales',
		'timestamp': datetime.now()
	}
	res = es.index(index="logs", doc_type='sales', body=doc)
	print(res['result'])


@celery.task(name='server.delete_upload')
def delete_upload(timeout,transaction_id):
	delete_query = {

		"conflicts": "proceed",
		"query": {
			"term": {
				"transaction_id": transaction_id
			}
		}
	}
	result = es.delete_by_query(index="docs", doc_type='sales', body=json.dumps(delete_query),scroll_size=5000)
	print(result)
	if result['version_conflicts'] != 0 and timeout < 100 :
		timeout = 2**timeout
		time.sleep(timeout)
		return delete_upload(timeout,transaction_id)
	if result['version_conflicts'] != 0 :
		return {'status':'error'}
	else :
		return {'status':'success'}