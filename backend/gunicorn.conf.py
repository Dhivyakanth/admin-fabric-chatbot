import os
import multiprocessing

# Get port from environment variable, default to 8000 for local development
port = os.getenv('PORT', '8000')
bind = f"0.0.0.0:{port}"

# Workers and threading
workers = 1
worker_class = 'sync'
threads = 1
worker_connections = 1000

# Timeouts
timeout = 300
graceful_timeout = 30
keepalive = 2

# Logging
loglevel = 'debug'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# App loading
preload_app = True

# Security
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
forwarded_allow_ips = ['*']
