from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

#user model for roles
class User(AbstractUser):
    class Role(models.TextChoices):
       STUDENT = "student", "Student"
       COORDINATOR = "coordinator", "Coordinator"
       ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

#courses and coordinators
class Course(models.Model):
    course_id = models.CharField(max_length=20, primary_key=True)
    title = models.CharField(max_length=255)
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="coordinated_courses",
    )

#checks assigned coordinator is a coordinator
    def clean(self):
        super().clean()
        if self.coordinator_id and self.coordinator.role != User.Role.COORDINATOR:
            raise ValidationError({"coordinator": "The user must be a coordinator."})

    def __str__(self):
        return f"{self.course_id}: {self.title}"

#link student to course
class Enrolment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrolments",
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrolments")

#cant enrol in one class twice
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_course_enrolment"),
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != User.Role.STUDENT:
            raise ValidationError({"user": "Only students can enrol in a course."})

    def __str__(self):
        return f"{self.user} enrolled in {self.course_id}"

#preference for groupmates
class Preference(models.Model):
    preference_id = models.BigAutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="preferences")
    chooser = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submitted_preferences",
    )
    chosen = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_preferences",
    )
    rank = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    class Meta:
        constraints = [
            #rank each classmate once
            models.UniqueConstraint(
                fields=["course", "chooser", "chosen"], name="unique_preferred_classmate",
            ),
            #only give one classmate each rank
            models.UniqueConstraint(
                fields=["course", "chooser", "rank"], name="unique_preference_rank",
            ),
            #ranks between 1-5
            models.CheckConstraint(
                condition=models.Q(rank__gte=1, rank__lte=5), name="preference_rank_1_to_5",
            ),
            #cant rank themself
            models.CheckConstraint(
                condition=~models.Q(chooser=models.F("chosen")), name="preference_not_self",
            ),
        ]

#checks student is a sutdent and in the course
    def clean(self):
        super().clean()
        errors = {}
        if self.chooser_id and self.chooser_id == self.chosen_id:
            errors["chosen"] = "Students cannot rank themselves."
        for field in ("chooser", "chosen"):
            user_id = getattr(self, f"{field}_id")
            if user_id:
                if getattr(self, field).role != User.Role.STUDENT:
                    errors[field] = "The user must be a student."
                elif self.course_id and not Enrolment.objects.filter(
                    course_id=self.course_id, user_id=user_id,
                ).exists():
                    errors[field] = "The student must be enrolled in this course."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.course_id}: {self.chooser} ranks {self.chosen} #{self.rank}"

#current allocation
class AllocationRun(models.Model):
    """Current results; a future service must replace them atomically on success.

    Solve reruns separately so a failed attempt leaves successful results intact.
    """
#states of allocation
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"
        FAILED = "failed", "Failed"

    run_id = models.BigAutoField(primary_key=True)
    course = models.OneToOneField(
        Course, on_delete=models.CASCADE, related_name="allocation_run",
    )
    min_team_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    max_team_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    time_limit_seconds = models.PositiveIntegerField(default=300, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    runtime_seconds = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    is_published = models.BooleanField(default=False)

#checks team sizes, runtimes and statuses
    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(min_team_size__gte=1), name="positive_min_team_size"),
            models.CheckConstraint(
                condition=models.Q(max_team_size__gte=models.F("min_team_size")),
                name="valid_team_size_range",
            ),
            models.CheckConstraint(condition=models.Q(time_limit_seconds__gte=1), name="positive_solver_time_limit"),
            models.CheckConstraint(
                condition=models.Q(runtime_seconds__isnull=True) | models.Q(runtime_seconds__gte=0),
                name="nonnegative_allocation_runtime",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["running", "finished", "failed"]),
                name="valid_allocation_status",
            ),
        ]

    def clean(self):
        super().clean()
        if (self.min_team_size is not None and self.max_team_size is not None
                and self.max_team_size < self.min_team_size):
            raise ValidationError({"max_team_size": "Must be at least the minimum team size."})

    def __str__(self):
        return f"{self.course_id}: allocation {self.run_id} ({self.status})"

#team made by allocation
class Team(models.Model):
    team_id = models.BigAutoField(primary_key=True)
    run = models.ForeignKey(AllocationRun, on_delete=models.CASCADE, related_name="teams")
    team_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])

#check each team number is unique in each run
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "team_number"], name="unique_team_number_per_run"),
            models.CheckConstraint(condition=models.Q(team_number__gte=1), name="positive_team_number"),
        ]

    def __str__(self):
        return f"{self.run.course_id}: team {self.team_number}"

#link student ot team
class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_memberships",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "student"], name="unique_team_student"),
        ]

#check is a sutdent and only in 1 team
    def clean(self):
        super().clean()
        errors = {}
        if self.student_id and self.student.role != User.Role.STUDENT:
            errors["student"] = "The user must be a student."
        if self.team_id and self.student_id:
            run = self.team.run
            if not Enrolment.objects.filter(course_id=run.course_id, user_id=self.student_id).exists():
                errors["student"] = "The student must be enrolled in the team's course."
            memberships = TeamMember.objects.filter(team__run_id=run.pk, student_id=self.student_id)
            if self.pk:
                memberships = memberships.exclude(pk=self.pk)
            if memberships.exists():
                errors["team"] = "The student already belongs to a team in this allocation."
        if errors:
            raise ValidationError(errors)

#readable student and team
    def __str__(self):
        return f"{self.student}: {self.team}"
