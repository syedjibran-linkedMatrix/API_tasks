# api_task/management/commands/wait_for_db.py
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
import time

class Command(BaseCommand):
    help = 'Wait for the database to be ready'

    def handle(self, *args, **kwargs):
        self.stdout.write('Waiting for database...')
        db_conn = connections['default']
        while True:
            try:
                db_conn.ensure_connection()
                break
            except OperationalError:
                self.stdout.write(self.style.WARNING('Database unavailable, waiting...'))
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS('Database is ready!'))
