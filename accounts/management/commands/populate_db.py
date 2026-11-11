import random

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from accounts.models import Course, Enrolment, Preference, User


class Command(BaseCommand):
    help = "Create development students, coordinators, courses and preferences."

    def handle(self, *args, **options):
        #generate ids for users and courses
        student_usernames = [f"student_{i:03d}" for i in range(1, 101)]
        coordinator_usernames = [f"coordinator_{i:02d}" for i in range(1, 6)]
        course_ids = [f"course_{i:02d}" for i in range(1, 6)]
        password = "Password123!"
        enrolment_count = 0
        preference_count = 0

        # cancel all changes if fails
        try:
            with transaction.atomic():
                #check if any users or courses exist
                existing_users = list(User.objects.filter(
                    username__in=student_usernames + coordinator_usernames,
                ).values_list("username", flat=True))
                existing_courses = list(Course.objects.filter(
                    course_id__in=course_ids,
                ).values_list("course_id", flat=True))
                #stop if overwriting
                if existing_users or existing_courses:
                    conflicts = existing_users + existing_courses
                    raise CommandError(
                        "Population stopped: generated usernames or course IDs "
                        "already exist: " + ", ".join(sorted(conflicts))
                    )
#create 100 students and 5 coordinators
                students = []
                coordinators = []
                for usernames, role, users in (
                    (student_usernames, User.Role.STUDENT, students),
                    (coordinator_usernames, User.Role.COORDINATOR, coordinators),
                ):
                    for username in usernames:
                        user = User(username=username, role=role)
                        user.set_password(password)
                        user.full_clean()
                        user.save()
                        users.append(user)

#create 5 courses
                courses = []
                for index, coordinator in enumerate(coordinators):
                    course = Course(
                        course_id=course_ids[index],
                        title=f"Development Course {index + 1}",
                        coordinator=coordinator,
                    )
                    course.full_clean()
                    course.save()
                    courses.append(course)
#store students in courses
                classmates = {course.pk: [] for course in courses}
                for index, student in enumerate(students):
                    # Give every course at 20 students
                    primary_course = courses[index % len(courses)]
                    #add students into additional courses
                    other_courses = [c for c in courses if c != primary_course]
                    selected_courses = [primary_course] + random.sample(
                        other_courses, random.randint(0, len(other_courses)),
                    )
                    #save enrollemnt
                    for course in selected_courses:
                        enrolment = Enrolment(user=student, course=course)
                        enrolment.full_clean()
                        enrolment.save()
                        classmates[course.pk].append(student)
                        enrolment_count += 1
#generate preferneces by coorse
                for course in courses:
                    enrolled_students = classmates[course.pk]
                    for index, chooser in enumerate(enrolled_students):
                        #can only rank other studnets
                        candidates = [s for s in enrolled_students if s != chooser]
                        # include incomplete preferences
                        if index == 0:
                            count = 0
                        else:
                            count = random.randint(0, min(course.max_preferences, len(candidates)))
                            #randomly select classmates and rank from1
                        for rank, chosen in enumerate(
                            random.sample(candidates, count), start=1,
                        ):
                            preference = Preference(
                                course=course, chooser=chooser, chosen=chosen, rank=rank,
                            )
                            #validate preferneces before saving
                            preference.full_clean()
                            preference.save()
                            preference_count += 1
        #return error, dont save data
        except (ValidationError, IntegrityError) as exc:
            raise CommandError(
                f"Population failed; no records were created. {exc}"
            ) from exc
        #print stats
        print("Created 100 students, 5 coordinators, 5 courses, " f"{enrolment_count} enrolments and {preference_count} preferences.")
        
