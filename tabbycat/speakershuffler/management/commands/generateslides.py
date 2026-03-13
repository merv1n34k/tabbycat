"""Management command to generate Fight Club slides for a round."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from tournaments.models import Round, Tournament


class Command(BaseCommand):
    help = 'Generate Fight Club slides with speaker photos for a round.'

    def add_arguments(self, parser):
        parser.add_argument('tournament', type=str,
                            help='Tournament slug')
        parser.add_argument('round', type=int,
                            help='Round sequence number')
        parser.add_argument('--photos-dir', type=str, required=True,
                            help='Path to directory containing speaker photos')
        parser.add_argument('--output-dir', type=str, default='./slides',
                            help='Path to output directory for generated slides (default: ./slides)')
        parser.add_argument('--template', type=str, default=None,
                            help='Path to a template PNG to use as the slide background')

    def handle(self, *args, **options):
        try:
            tournament = Tournament.objects.get(slug=options['tournament'])
        except Tournament.DoesNotExist:
            raise CommandError(f"Tournament '{options['tournament']}' not found.")

        try:
            round_obj = Round.objects.get(tournament=tournament, seq=options['round'])
        except Round.DoesNotExist:
            raise CommandError(f"Round {options['round']} not found in tournament '{tournament.name}'.")

        if round_obj.draw_status == Round.Status.NONE:
            raise CommandError(f"Round {round_obj.name} has no draw yet.")

        photos_dir = Path(options['photos_dir']).resolve()
        if not photos_dir.is_dir():
            raise CommandError(f"Photos directory '{photos_dir}' does not exist.")

        output_dir = Path(options['output_dir']).resolve()

        template_path = None
        if options['template']:
            template_path = Path(options['template']).resolve()
            if not template_path.is_file():
                raise CommandError(f"Template file '{template_path}' does not exist.")

        self.stdout.write(f"Generating slides for {round_obj.name}...")
        self.stdout.write(f"  Photos: {photos_dir}")
        if template_path:
            self.stdout.write(f"  Template: {template_path}")
        self.stdout.write(f"  Output: {output_dir}")

        from speakershuffler.slides import generate_round_slides
        slides = generate_round_slides(round_obj, str(photos_dir), str(output_dir),
                                       template_path=str(template_path) if template_path else None)

        self.stdout.write(self.style.SUCCESS(f"Generated {len(slides)} slide(s):"))
        for s in slides:
            self.stdout.write(f"  {s}")
