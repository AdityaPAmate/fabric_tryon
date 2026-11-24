import time
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from fabricapp.models import VideoJob
from fabricapp.video.service import process_job
from fabricapp.video.worker_lock import exclusive_worker


class Command(BaseCommand):
    help = 'Process durable video jobs sequentially. Run beside Django with the same DB and MEDIA_ROOT.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Process at most one pending job, then exit.')

    def handle(self, *args, **options):
        if not settings.GIMMECLIP_API_KEY:
            raise CommandError('Set GIMMECLIP_API_KEY before starting the video worker.')
        with exclusive_worker():
            self.stdout.write('Video worker ready (one job at a time).')
            try:
                while True:
                    close_old_connections()
                    # Recover interrupted stages before new requests. A submission whose
                    # response was lost is marked for manual reconciliation, never resubmitted.
                    job = VideoJob.objects.exclude(status__in=['completed', 'failed', 'preparing']).first()
                    if job:
                        process_job(job)
                        self.stdout.write(f'{job.pk}: {job.status}')
                    if options['once']:
                        return
                    if not job:
                        time.sleep(2)
            except KeyboardInterrupt:
                self.stdout.write('Worker stopped. Saved stages will resume on restart.')
