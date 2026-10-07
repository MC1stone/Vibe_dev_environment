"""Backfill persisted curve data for existing NIRSpectrum records (M-UI fix).

Records uploaded before the curve-persistence feature have empty
wavelengths/intensities fields. This command walks the existing dataset,
loads the measured curve from each record's original file via the
format-agnostic loader chain and persists it. Idempotent: records with an
existing curve are skipped unless --force is given.
"""

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ("Persist spectral curves (wavelengths/intensities/units) for "
            "existing NIRSpectrum records from their original files.")

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Re-extract even when a curve is already persisted')
        parser.add_argument('--limit', type=int, default=0,
                            help='Process at most N records (0 = all)')

    def handle(self, *args, **options):
        from core.models import NIRSpectrum
        from services.spectrum_curve import apply_curve_to_spectrum

        force = options['force']
        limit = options['limit']

        queryset = NIRSpectrum.objects.all().order_by('created_at')
        total = queryset.count()
        pending = queryset if force else queryset.filter(wavelengths=[])
        pending_count = pending.count()
        self.stdout.write(
            f"Backfill: {pending_count} of {total} records need a curve "
            f"(force={force}).")

        done = 0
        extracted = 0
        missing_file = 0
        no_curve = 0
        for spectrum in pending.iterator():
            if limit and done >= limit:
                break
            done += 1
            try:
                file_path = spectrum.get_file_path()
            except Exception:
                file_path = None
            if not file_path:
                missing_file += 1
                continue
            try:
                if apply_curve_to_spectrum(spectrum, file_path):
                    spectrum.save()
                    extracted += 1
                else:
                    no_curve += 1
            except Exception as e:
                no_curve += 1
                logger.exception("Backfill failed for %s: %s", spectrum.id, e)

        self.stdout.write(self.style.SUCCESS(
            f"Backfill finished: {extracted} curves persisted, "
            f"{no_curve} files without extractable curve, "
            f"{missing_file} records without readable original file "
            f"({done} processed)."))
        if missing_file:
            self.stdout.write(self.style.WARNING(
                "Records without a readable original file keep their empty "
                "curve; analysis for them requires a re-upload."))
