"""
Celery Application Configuration
Background task processing for campaigns and messaging
"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Create Celery app
celery_app = Celery(
    'ektola',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.campaign_tasks',  # Import campaign tasks
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=False,
    
    # Task routing
    task_routes={
        'app.tasks.campaign_tasks.*': {'queue': 'campaigns'},
    },
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Reject if worker crashes
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Retry settings
    task_default_retry_delay=60,  # Retry after 1 minute
    task_max_retries=3,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster'
    },
    
    # Worker settings
    worker_prefetch_multiplier=4,  # Tasks per worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        'check-pending-campaigns': {
            'task': 'app.tasks.campaign_tasks.check_pending_campaigns',
            'schedule': crontab(minute='*/1'),  # Every minute
        },
    },
)

# Optional: Configure task result backend
celery_app.conf.result_backend = settings.REDIS_URL

# Task autodiscovery (finds tasks in registered modules)
celery_app.autodiscover_tasks(['app.tasks'])
