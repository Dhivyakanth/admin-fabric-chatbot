web: gunicorn flask_server:app --chdir backend --bind 0.0.0.0:$PORT --workers 2 --worker-class gthread --threads 8 --timeout 180 --graceful-timeout 30 --keep-alive 5 --preload

