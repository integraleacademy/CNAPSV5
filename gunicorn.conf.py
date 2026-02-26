import os

bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

raw_workers = os.getenv('WEB_CONCURRENCY', '1')
try:
    workers = max(1, int(raw_workers))
except ValueError:
    workers = 1

worker_class = 'sync'
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
