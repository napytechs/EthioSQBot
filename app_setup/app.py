from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from . import config

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name):
    from flask import Flask
    app = Flask(__name__)
    app.config.from_object(config.config[config_name])
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context() as context:
        context.push()

    return app

