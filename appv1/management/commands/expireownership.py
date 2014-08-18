"""Expire ownership in 2 days."""
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from appv1.models import User
from datetime import datetime, date, timedelta
from appv1.models import StackOwnership
import sys


class Command(BaseCommand):
        """Extend Base class and define options with values."""
        option_list = BaseCommand.option_list +	(
        make_option('--days',
        action='store',
        type='int',
        dest='expiry_days',
        help='expiry time in days'),
    ) + (
        make_option('--hrs',
                                action='store',
                                type='int',
                                dest='expiry_hours',
                                help='expiry time in hours'),
        ) + (
        make_option('--mins',
                                action='store',
                                type='int',
                                dest='expiry_minutes',
                                help='expiry time in minutes'),
        )


        def handle(self, *args, **options):
                """Handle options and supplied arguments."""
                if options['expiry_minutes']:
                        self.expire_stack_ownership(options['expiry_minutes'], "minutes")
                if options['expiry_days']:
                        self.expire_stack_ownership(options['expiry_days'], "days")
                if options['expiry_hours']:
                        self.expire_stack_ownership(options['expiry_hours'], "hours")


        def expire_stack_ownership(self,expirytime, timetype):
                """Expire stack ownership in the specified time in days, hours or minutes."""
                try:
                        ownership_details = StackOwnership.objects.all()

                        if ownership_details:

                                for record in ownership_details:
                                        if timetype == "days":
                                                if datetime.now().replace(tzinfo=None) >= record.start_time.replace(tzinfo=None) + timedelta(days=expirytime):
                                                        ownership_details.get(id=record.id).delete()

                                        elif timetype == "hours":
                                                if datetime.now().replace(tzinfo=None) >= record.start_time.replace(tzinfo=None) + timedelta(hours=expirytime):
                                                        ownership_details.get(id=record.id).delete()

                                        elif timetype == "minutes":
                                                if datetime.now().replace(tzinfo=None) >= record.start_time.replace(tzinfo=None)+ timedelta(minutes=expirytime):
                                                        ownership_details.get(id=record.id).delete()

                except Exception as exp_object:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        return
