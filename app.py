from flask import Flask

# 1. Initialize the application
app = Flask(__name__)

# 2. Define a route (URL) and bind it to a function
@app.route("/")
def home():
    return "Hello, World!"

# 3. Start the local development server (optional block)
if __name__ == "__main__":
    app.run(debug=True)
