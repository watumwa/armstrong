"""Scheduled fleet alert scanner. Run: python manage.py scan_fleet_alerts"""
from django.core.management.base import BaseCommand
from operations.fleet_alerts import detect_alerts

class Command(BaseCommand):
    help="Detect overdue fleet departures and stale GPS; persist deduplicated alerts."

    def handle(self,*args,**options):
        created=detect_alerts()
        self.stdout.write(self.style.SUCCESS(f"Fleet scan complete: {created} new alerts"))
