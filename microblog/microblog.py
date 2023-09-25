from microblog.app import create_app, cli


app,mongo = create_app()
if __name__ == '__main__':
    app.run()
cli.register(app)

