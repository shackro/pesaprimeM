from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from investments.tasks import update_assets_prices

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Run job every 4 hours, and run immediately on startup
    scheduler.add_job(
        update_assets_prices,
        trigger='interval',
        hours=4,
        id='update_asset_prices',
        replace_existing=True,
        next_run_time=datetime.now()
    )

    try:
        scheduler.start()
        print("Scheduler started successfully.")
    except Exception as e:
        print("Scheduler failed:", e)
