from app import create_app

if __name__ == '__main__':
    print("Starting Flask application...")
    app = create_app()
    print("App created, starting server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
    print("Server started!") 