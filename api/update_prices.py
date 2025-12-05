from django.core.wsgi import get_wsgi_application
import os
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pesaprime.settings")
application = get_wsgi_application()

from investments.management.commands import update_asset_prices  # your logic

def handler(request):
    try:
        update_asset_prices()
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Prices updated successfully"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
