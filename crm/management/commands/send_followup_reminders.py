from django.core.management.base import BaseCommand
from crm.services import send_followup_reminders


class Command(BaseCommand):
    help = 'Send FCM reminders for follow-ups due today or overdue'

    def handle(self, *args, **options):
        self.stdout.write('Sending follow-up reminders...')
        send_followup_reminders()
        self.stdout.write(self.style.SUCCESS('Successfully sent follow-up reminders'))

