# Large-File-Upload-Using-Celery

Technology Stack used:
	Python
	Gunicorn
	Flask
	RabbitMq
	Redis
	Celery
	Flower
	ElasticSearch
	Kibana

Prerequisite:
	kompose
	kubectl
	for local setup:
		minikube
		oracle VM

Run commands:
	1.start minikube
	2.Run these commands where you have downloaded the docker-compose.yaml
		kompose convert (to convert docker-compose to kubernetes)
		kompose up
	4.kubectl get pods (wait for all pods to start)
	3.kubectl get services
	4.kubectl expose deployment worker --name=social --type=NodePort
	5.kubectl expose deployment elasticsearch --name=es --type=NodePort
	6.machine ip (get ip addr of machine)
	7.kubectl describe service social (get NodePort port-1  for gunicorn flask)
	8.kubectl describe service social (get NodePort port-2  for flower)
	9.kubectl describe service es (get NodePort port-2  for elasticsearch)

Visit website:
	1.Flask web server - <machineip>:<NodePort port-1>
	2.Flower CeleryMonitoring - <machineip>:<NodePort port-2>
	3.ElasticSearch - <machineip>:<NodePort port-2>/docs/_search

