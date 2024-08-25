from flask import Flask
from service import routes

app = Flask(__name__)

# Register the routes
routes.init_routes(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
