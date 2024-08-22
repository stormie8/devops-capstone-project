from flask import Flask
from flask_talisman import Talisman
from service import config
from service.common import log_handlers

# Create Flask application
app = Flask(__name__)
app.config.from_object(config)

# Initialize Talisman
talisman = Talisman(app)

# Set up logging for production
log_handlers.init_logging(app, "gunicorn.error")

# Import the routes After the Flask app is created
from service import routes, models  # noqa: F401 E402
from service.common import error_handlers, cli_commands  # noqa: F401 E402

# Initialize the database
models.init_db(app)

app.logger.info("Service initialized!")