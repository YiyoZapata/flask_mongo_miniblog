from flask import render_template
from app import app

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    # Manejo de excepciones relacionadas con MongoDB
    try:
        # Aquí puedes realizar operaciones relacionadas con MongoDB
        # Por ejemplo, realizar un rollback en caso de error
        # Asegúrate de importar MongoClient y obtener la colección necesaria
        from pymongo import MongoClient
        client = MongoClient(app.config['MONGO_URI'])
        db = client[app.config['MONGO_DBNAME']]
        user_collection = db['users']

        # Realiza tus operaciones de manejo de errores aquí

    except Exception as e:
        # Maneja la excepción de MongoDB aquí
        print("Error en MongoDB:", str(e))

    return render_template('500.html'), 500
