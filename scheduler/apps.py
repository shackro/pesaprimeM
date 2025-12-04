# scheduler/apps.py
from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler

class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'

    def ready(self):
        from .tasks import update_all_assets
        scheduler = BackgroundScheduler()
        # Schedule job every 4 hours
        scheduler.add_job(update_all_assets, 'interval', hours=1, id='update_assets_job', replace_existing=True)
        scheduler.start()
