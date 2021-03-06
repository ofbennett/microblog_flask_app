import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
if not os.environ.get('USE_DOCKER'):
    load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POSTS_PER_PAGE = 10
    MS_TRANSLATION_KEY = os.environ.get('MS_TRANSLATION_KEY') or 'this-is-my-key'
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    STORE_EMAIL = False