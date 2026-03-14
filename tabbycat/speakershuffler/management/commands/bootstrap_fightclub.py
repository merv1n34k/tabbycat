"""Bootstrap a Fight Club tournament for testing.

Creates a tournament with 8 speakers (cat1-cat8), 4 teams of 2 (BP format),
1 adjudicator, 2 preliminary rounds + 1 Grand Final.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from availability.models import RoundAvailability
from breakqual.models import BreakCategory
from participants.models import Adjudicator, Institution, Speaker, Team
from tournaments.models import Round, Tournament
from venues.models import Venue


class Command(BaseCommand):
    help = 'Create a Fight Club test tournament with 8 cat speakers.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', type=str, default='fightclub',
                            help='Tournament slug (default: fightclub)')
        parser.add_argument('--wipe', action='store_true', default=False,
                            help='Delete existing tournament with this slug first')

    def handle(self, *args, **options):
        slug = options['slug']

        if options['wipe']:
            from draw.models import DebateTeam
            qs = Tournament.objects.filter(slug=slug)
            if qs.exists():
                DebateTeam.objects.filter(debate__round__tournament__slug=slug).delete()
                qs.delete()
            self.stdout.write(f"Deleted existing tournament '{slug}'.")

        if Tournament.objects.filter(slug=slug).exists():
            self.stdout.write(self.style.ERROR(
                f"Tournament '{slug}' already exists. Use --wipe to replace it."))
            return

        # Create tournament
        t = Tournament.objects.create(
            name="Fight Club Cats",
            short_name="FC Cats",
            slug=slug,
        )
        self.stdout.write(f"Created tournament: {t.name} ({t.slug})")

        # Enable fight club mode
        t.preferences['debate_rules__fight_club_mode'] = True
        t.preferences['debate_rules__teams_in_debate'] = 4
        t.preferences['debate_rules__substantive_speakers'] = 2
        t.preferences['debate_rules__side_names'] = 'gov-opp'
        t.preferences['debate_rules__ballots_per_debate_prelim'] = 'per-adj'

        # Create institution
        inst, _ = Institution.objects.get_or_create(
            name="Cat Academy", code="CATS",
        )

        # Create 4 teams with 2 speakers each (cat1-cat8)
        teams = []
        speaker_num = 1
        for i in range(1, 5):
            team = Team.objects.create(
                tournament=t,
                institution=inst,
                reference=f"Team {i}",
                short_reference=f"Team {i}",
                use_institution_prefix=False,
            )
            teams.append(team)

            for _ in range(2):
                Speaker.objects.create(
                    name=f"cat{speaker_num}",
                    team=team,
                )
                speaker_num += 1

        self.stdout.write(f"Created {len(teams)} teams with 8 speakers (cat1-cat8)")

        # Create adjudicator
        adj = Adjudicator.objects.create(
            name="Judge Whiskers",
            institution=inst,
            tournament=t,
            base_score=5.0,
        )
        self.stdout.write(f"Created adjudicator: {adj.name}")

        # Create venue
        venue = Venue.objects.create(
            name="The Arena",
            priority=100,
        )
        self.stdout.write(f"Created venue: {venue.name}")

        # Create 2 preliminary rounds
        r1 = Round.objects.create(
            tournament=t, seq=1, name="Round 1", abbreviation="R1",
            stage=Round.Stage.PRELIMINARY,
            draw_type=Round.DrawType.POWERPAIRED,
        )
        r2 = Round.objects.create(
            tournament=t, seq=2, name="Round 2", abbreviation="R2",
            stage=Round.Stage.PRELIMINARY,
            draw_type=Round.DrawType.POWERPAIRED,
        )
        self.stdout.write("Created rounds: R1, R2")

        # Create break category + Grand Final
        bc = BreakCategory.objects.create(
            tournament=t,
            name="Open",
            slug="open",
            seq=1,
            break_size=2,
            is_general=True,
            priority=100,
        )
        gf = Round.objects.create(
            tournament=t, seq=3, name="Grand Final", abbreviation="GF",
            stage=Round.Stage.ELIMINATION,
            draw_type=Round.DrawType.ELIMINATION,
            break_category=bc,
        )
        self.stdout.write("Created break category 'Open' + Grand Final")

        # Set current round
        t.current_round = r1
        t.save()

        # Mark all teams, adjudicators, and venues as available for R1 and R2
        team_ct = ContentType.objects.get_for_model(Team)
        adj_ct = ContentType.objects.get_for_model(Adjudicator)
        venue_ct = ContentType.objects.get_for_model(Venue)

        for rnd in [r1, r2]:
            for team in teams:
                RoundAvailability.objects.create(
                    content_type=team_ct, object_id=team.pk, round=rnd,
                )
            RoundAvailability.objects.create(
                content_type=adj_ct, object_id=adj.pk, round=rnd,
            )
            RoundAvailability.objects.create(
                content_type=venue_ct, object_id=venue.pk, round=rnd,
            )

        self.stdout.write(self.style.SUCCESS(
            "\nFight Club tournament ready! "
            f"Visit /admin/ or /{slug}/ to start.\n"
            "Speakers: cat1, cat2, cat3, cat4, cat5, cat6, cat7, cat8"
        ))
