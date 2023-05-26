import os


class Config:
    TOKEN = os.getenv("BOT_TOKEN")
    CHANNEL_ID = os.getenv("CHANNEL_ID")
    FLASK_ADMIN_ID = os.getenv("FLASK_ADMIN_ID")
    SQLALCHEMY_DATABASE_URI = os.getenv("MAIN_DATABASE")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")


class TestConfig(Config):
    TOKEN = os.getenv("TEST_BOT_TOKEN")
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE")


class ProductionConfig(Config):
    pass


config = {
    'test': TestConfig,
    'product': ProductionConfig
}