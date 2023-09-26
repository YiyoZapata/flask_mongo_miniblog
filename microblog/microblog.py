from microblog.app import create_app, cli


app,mongo = create_app()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
cli.register(app)

