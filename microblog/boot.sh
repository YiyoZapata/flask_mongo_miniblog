#!/bin/bash

# Activa el entorno virtual de Python
source venv/bin/activate

# Configura la variable de entorno MONGODB_URI
export MONGODB_URI="mongodb://mongoserver-container:27017/microblog"



# Compila las traducciones
flask translate compile

# Inicia Gunicorn para servir la aplicación Flask
exec gunicorn -b :5000 --access-logfile - --error-logfile - microblog.microblog:app
