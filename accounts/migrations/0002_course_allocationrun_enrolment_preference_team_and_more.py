import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('course_id', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('coordinator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='coordinated_courses', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AllocationRun',
            fields=[
                ('run_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('min_team_size', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('max_team_size', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('time_limit_seconds', models.PositiveIntegerField(default=300, validators=[django.core.validators.MinValueValidator(1)])),
                ('status', models.CharField(choices=[('running', 'Running'), ('finished', 'Finished'), ('failed', 'Failed')], default='running', max_length=10)),
                ('runtime_seconds', models.FloatField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('is_published', models.BooleanField(default=False)),
                ('course', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='allocation_run', to='accounts.course')),
            ],
        ),
        migrations.CreateModel(
            name='Enrolment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrolments', to='accounts.course')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrolments', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Preference',
            fields=[
                ('preference_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('rank', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('chooser', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submitted_preferences', to=settings.AUTH_USER_MODEL)),
                ('chosen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_preferences', to=settings.AUTH_USER_MODEL)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to='accounts.course')),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('team_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('team_number', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teams', to='accounts.allocationrun')),
            ],
        ),
        migrations.CreateModel(
            name='TeamMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_memberships', to=settings.AUTH_USER_MODEL)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='accounts.team')),
            ],
        ),
        migrations.AddConstraint(
            model_name='allocationrun',
            constraint=models.CheckConstraint(condition=models.Q(('min_team_size__gte', 1)), name='positive_min_team_size'),
        ),
        migrations.AddConstraint(
            model_name='allocationrun',
            constraint=models.CheckConstraint(condition=models.Q(('max_team_size__gte', models.F('min_team_size'))), name='valid_team_size_range'),
        ),
        migrations.AddConstraint(
            model_name='allocationrun',
            constraint=models.CheckConstraint(condition=models.Q(('time_limit_seconds__gte', 1)), name='positive_solver_time_limit'),
        ),
        migrations.AddConstraint(
            model_name='allocationrun',
            constraint=models.CheckConstraint(condition=models.Q(('runtime_seconds__isnull', True), ('runtime_seconds__gte', 0), _connector='OR'), name='nonnegative_allocation_runtime'),
        ),
        migrations.AddConstraint(
            model_name='allocationrun',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['running', 'finished', 'failed'])), name='valid_allocation_status'),
        ),
        migrations.AddConstraint(
            model_name='enrolment',
            constraint=models.UniqueConstraint(fields=('user', 'course'), name='unique_course_enrolment'),
        ),
        migrations.AddConstraint(
            model_name='preference',
            constraint=models.UniqueConstraint(fields=('course', 'chooser', 'chosen'), name='unique_preferred_classmate'),
        ),
        migrations.AddConstraint(
            model_name='preference',
            constraint=models.UniqueConstraint(fields=('course', 'chooser', 'rank'), name='unique_preference_rank'),
        ),
        migrations.AddConstraint(
            model_name='preference',
            constraint=models.CheckConstraint(condition=models.Q(('rank__gte', 1), ('rank__lte', 5)), name='preference_rank_1_to_5'),
        ),
        migrations.AddConstraint(
            model_name='preference',
            constraint=models.CheckConstraint(condition=models.Q(('chooser', models.F('chosen')), _negated=True), name='preference_not_self'),
        ),
        migrations.AddConstraint(
            model_name='team',
            constraint=models.UniqueConstraint(fields=('run', 'team_number'), name='unique_team_number_per_run'),
        ),
        migrations.AddConstraint(
            model_name='team',
            constraint=models.CheckConstraint(condition=models.Q(('team_number__gte', 1)), name='positive_team_number'),
        ),
        migrations.AddConstraint(
            model_name='teammember',
            constraint=models.UniqueConstraint(fields=('team', 'student'), name='unique_team_student'),
        ),
    ]
