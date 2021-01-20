from main import app as application

if __name__ == "__main__":
    application.run(threaded=True,ssl_context=('/etc/letsencrypt/live/example.com/fullchain.pem', '/etc/letsencrypt/live/example.com/privkey.pem'))
