from django.core.management.base import BaseCommand

from operations.sms_reminders import dispatch_due_reminders, queue_due_reminders


class Command(BaseCommand):
    help = "Queue consented collection/balance reminders; use --send to dispatch through the configured SMS provider."

    def add_arguments(self, parser):
        parser.add_argument("--send", action="store_true", help="Send queued reminders after building the outbox")

    def handle(self, *args, **options):
        queued = queue_due_reminders()
        self.stdout.write(self.style.SUCCESS(f"SMS outbox queued: {queued}"))
        if options["send"]:
            result = dispatch_due_reminders()
            self.stdout.write(self.style.SUCCESS(f"SMS dispatch: {result}"))
