from django.core.management.base import BaseCommand

from myapp.tasks import populate_data


class Command(BaseCommand):
    help = 'Populates the database with fake data using Celery'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting data population task...")
        populate_data.apply_async()
        self.stdout.write("Data population task has been sent to Celery.")
