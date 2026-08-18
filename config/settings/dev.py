from .base import *
import os

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]