from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse

from .models import Course, User


class RoleLoginView(LoginView):
    def get_default_redirect_url(self):
        #student gets sent to my courses
        if self.request.user.role == User.Role.STUDENT:
            return reverse('student_courses')
        return super().get_default_redirect_url()


@login_required(login_url='login')
def student_courses(request):
    #must be a student
    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied

    #list courses by id
    courses = Course.objects.filter(
        enrolments__user=request.user,
    ).order_by('course_id')
    return render(request, 'accounts/student_courses.html', {'courses': courses})
