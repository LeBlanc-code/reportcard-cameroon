from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Avg, Count, Max, Min, Sum, Q
from django_ratelimit.decorators import ratelimit
from .forms import LoginForm, CreateUserForm, MarkForm, TermConfigForm, SignupForm
from .models import ReportCard, Mark, StudentProfile, Subject, TermConfig, CustomUser, Class, Transcript, Activity
from .decorators import role_required
from .services import MarkSubmissionService


@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    was_limited = getattr(request, 'limited', False)
    if was_limited:
        messages.error(request, 'Too many login attempts. Please try again in 5 minutes.')
        return render(request, 'accounts/login.html', {'form': LoginForm()})

    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@ratelimit(key='ip', rate='5/m', method='POST')
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    was_limited = getattr(request, 'limited', False)
    if was_limited:
        messages.error(request, 'Too many signup attempts. Please try again in 5 minutes.')
        return render(request, 'accounts/signup.html', {'form': SignupForm()})

    form = SignupForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            role = user.role
            messages.success(request, f'Account created! Welcome, {user.get_full_name()} ({role.title()}).')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def dashboard_view(request):
    user = request.user
    context = {'user': user}

    if user.role in ('principal', 'vice_principal'):
        pending_count = ReportCard.objects.filter(validated=False).count()
        unprinted_count = ReportCard.objects.filter(validated=True, print_permission=False).count()
        context['pending_count'] = pending_count
        context['unprinted_count'] = unprinted_count

    if user.role == 'class_master':
        my_class = Class.objects.filter(class_master=user).first()
        if my_class:
            student_count = StudentProfile.objects.filter(school_class=my_class).count()
            context['my_class'] = my_class
            context['student_count'] = student_count

    if user.role in ('teacher', 'class_master'):
        today = timezone.now().date()
        deadlines = TermConfig.objects.filter(
            school=user.school,
            marks_deadline__isnull=False,
            marks_deadline__gte=today
        ).order_by('marks_deadline')
        past_deadlines = TermConfig.objects.filter(
            school=user.school,
            marks_deadline__isnull=False,
            marks_deadline__lt=today
        ).order_by('-marks_deadline')[:3]
        context['deadlines'] = deadlines
        context['past_deadlines'] = past_deadlines

    return render(request, 'accounts/dashboard.html', context)


@login_required
@role_required('school_admin', 'principal', 'vice_principal')
def create_user_view(request):
    form = CreateUserForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data['role']
            assigned_class = form.cleaned_data.get('assigned_class')

            if role == 'student' and assigned_class:
                StudentProfile.objects.create(user=user, school_class=assigned_class)
                ReportCard.objects.create(student=user.studentprofile, term='Term 1')
                messages.success(request, f'Student {user.get_full_name()} added to {assigned_class.name}.')

            elif role == 'class_master' and assigned_class:
                assigned_class.class_master = user
                assigned_class.save()
                messages.success(request, f'Class Master {user.get_full_name()} assigned to {assigned_class.name}.')

            elif role == 'teacher':
                messages.success(request, f'Teacher {user.get_full_name()} created.')

            else:
                messages.success(request, f'User {user.get_full_name()} created.')

            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'accounts/create_user.html', {'form': form})


@login_required
@role_required('teacher')
def teacher_my_classes_view(request):
    user = request.user
    classes = Class.objects.filter(
        subjects__teacher=user
    ).prefetch_related('subjects').distinct()

    class_data = []
    for cls in classes:
        my_subjects = cls.subjects.filter(teacher=user)
        student_count = StudentProfile.objects.filter(school_class=cls).count()
        marks_count = Mark.objects.filter(
            subject__in=my_subjects,
            student__school_class=cls
        ).count()
        class_data.append({
            'class': cls,
            'subjects': my_subjects,
            'student_count': student_count,
            'marks_count': marks_count,
        })

    return render(request, 'accounts/teacher_my_classes.html', {
        'class_data': class_data,
    })


@login_required
@role_required('teacher', 'class_master', 'principal', 'vice_principal', 'school_admin')
def enter_mark_view(request):
    class_id = request.GET.get('class_id')
    if class_id:
        try:
            class_id = int(class_id)
        except (ValueError, TypeError):
            class_id = None

    if request.method == 'POST':
        form = MarkForm(request.POST, user=request.user, class_id=class_id)
        if form.is_valid():
            try:
                student = form.cleaned_data['student']
                subject = form.cleaned_data['subject']
                score = form.cleaned_data['score']
                term = form.cleaned_data['term']

                success, message, mark = MarkSubmissionService.submit_mark(
                    user=request.user,
                    student=student,
                    subject=subject,
                    score=score,
                    term=term
                )

                if success:
                    messages.success(request, message)
                    redirect_url = reverse('enter_mark')
                    if class_id:
                        redirect_url += f'?class_id={class_id}'
                    return redirect(redirect_url)
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, str(error))
    else:
        form = MarkForm(user=request.user, class_id=class_id)

    target_class = form.target_class if hasattr(form, 'target_class') else None

    return render(request, 'accounts/enter_mark.html', {
        'form': form,
        'target_class': target_class,
    })


@login_required
@role_required('principal', 'vice_principal')
def validate_reportcards_view(request):
    pending_cards = ReportCard.objects.filter(validated=False).select_related(
        'student__user', 'student__school_class'
    ).order_by('student__user__first_name', 'student__user__last_name')

    validated_cards = ReportCard.objects.filter(validated=True).select_related(
        'student__user', 'student__school_class', 'validated_by'
    ).order_by('-validated_at')[:10]

    classes = Class.objects.filter(school=request.user.school)

    if request.method == 'POST':
        action = request.POST.get('action')
        now = timezone.now()

        if action == 'validate_all':
            count = pending_cards.update(validated=True, validated_by=request.user, validated_at=now)
            messages.success(request, f"Validated {count} report card(s) at once.")
            return redirect('validate_reportcards')

        elif action == 'validate_by_class':
            class_id = request.POST.get('class_id')
            if class_id:
                count = pending_cards.filter(
                    student__school_class_id=class_id
                ).update(validated=True, validated_by=request.user, validated_at=now)
                cls = get_object_or_404(Class, id=class_id)
                messages.success(request, f"Validated {count} report card(s) for {cls.name}.")
            return redirect('validate_reportcards')

    context = {
        'pending_cards': pending_cards,
        'validated_cards': validated_cards,
        'pending_count': pending_cards.count(),
        'classes': classes,
    }
    return render(request, 'accounts/validate_reportcards.html', context)


@login_required
@role_required('principal', 'vice_principal')
def validate_reportcard_detail_view(request, reportcard_id):
    reportcard = get_object_or_404(ReportCard, id=reportcard_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            reportcard.validated = True
            reportcard.validated_by = request.user
            reportcard.validated_at = timezone.now()
            reportcard.save()
            messages.success(
                request,
                f"Report card for {reportcard.student.user.get_full_name()} has been approved."
            )
            return redirect('validate_reportcards')

        elif action == 'reject':
            reportcard.validated = False
            reportcard.validated_by = None
            reportcard.validated_at = None
            reportcard.save()
            messages.info(
                request,
                f"Report card for {reportcard.student.user.get_full_name()} has been marked as pending."
            )
            return redirect('validate_reportcards')

        elif action == 'grant_print':
            reportcard.print_permission = True
            reportcard.print_permission_granted_by = request.user
            reportcard.print_permission_granted_at = timezone.now()
            reportcard.save()
            messages.success(
                request,
                f"Print permission granted for {reportcard.student.user.get_full_name()}."
            )
            return redirect('validate_reportcard_detail', reportcard_id=reportcard.id)

    marks = Mark.objects.filter(
        student=reportcard.student,
        term=reportcard.term
    ).select_related('subject', 'subject__teacher')

    context = {
        'reportcard': reportcard,
        'marks': marks,
        'total_score': reportcard.total_score(),
        'average_score': reportcard.average_score(),
    }
    return render(request, 'accounts/validate_reportcard_detail.html', context)


@login_required
@role_required('class_master')
def class_statistics_view(request):
    user = request.user
    my_class = get_object_or_404(Class, class_master=user)
    students = StudentProfile.objects.filter(school_class=my_class).select_related('user')

    terms = Mark.objects.filter(
        student__school_class=my_class
    ).values_list('term', flat=True).distinct().order_by('term')

    selected_term = request.GET.get('term', terms.first() if terms else None)

    stats = []
    if selected_term:
        for student in students:
            marks = Mark.objects.filter(
                student=student,
                term=selected_term
            ).select_related('subject')
            if marks.exists():
                avg = sum(m.score for m in marks) / marks.count()
                total = sum(m.score for m in marks)
                stats.append({
                    'student': student,
                    'marks': marks,
                    'average': avg,
                    'total': total,
                    'mark_count': marks.count(),
                })

        stats.sort(key=lambda x: x['average'], reverse=True)

    subject_averages = {}
    if selected_term and stats:
        all_marks = Mark.objects.filter(
            student__school_class=my_class,
            term=selected_term
        ).values('subject__name').annotate(
            avg=Avg('score'),
            max=Max('score'),
            min=Min('score'),
            count=Count('id')
        ).order_by('subject__name')
        subject_averages = list(all_marks)

    class_average = sum(s['average'] for s in stats) / len(stats) if stats else 0

    context = {
        'my_class': my_class,
        'students': students,
        'selected_term': selected_term,
        'terms': terms,
        'stats': stats,
        'class_average': class_average,
        'subject_averages': subject_averages,
        'student_count': students.count(),
    }
    return render(request, 'accounts/class_statistics.html', context)


@login_required
@role_required('student')
def student_reportcard_view(request):
    user = request.user
    try:
        student_profile = user.studentprofile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'No student profile found.')
        return redirect('dashboard')

    reportcards = ReportCard.objects.filter(
        student=student_profile
    ).order_by('-term')

    context = {
        'student': student_profile,
        'reportcards': reportcards,
    }
    return render(request, 'accounts/student_reportcard.html', context)


@login_required
@role_required('student')
def student_reportcard_detail_view(request, reportcard_id):
    user = request.user
    try:
        student_profile = user.studentprofile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'No student profile found.')
        return redirect('dashboard')

    reportcard = get_object_or_404(ReportCard, id=reportcard_id, student=student_profile)

    if not reportcard.validated:
        messages.warning(request, 'This report card has not been validated yet.')
        return redirect('student_reportcard')

    try:
        term_config = TermConfig.objects.get(
            school=student_profile.school_class.school,
            term=reportcard.term
        )
    except TermConfig.DoesNotExist:
        messages.error(request, 'Term closing date has not been configured yet.')
        return redirect('student_reportcard')

    now = timezone.now()
    closing_datetime = timezone.make_aware(
        timezone.datetime.combine(term_config.closing_date, term_config.closing_time)
    )

    if now < closing_datetime:
        time_remaining = closing_datetime - now
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes = remainder // 60
        messages.warning(
            request,
            f"Report cards for {reportcard.term} will be available on "
            f"{term_config.closing_date.strftime('%B %d, %Y')} at "
            f"{term_config.closing_time.strftime('%I:%M %p')}. "
            f"Time remaining: {hours}h {minutes}m."
        )
        return redirect('student_reportcard')

    marks = Mark.objects.filter(
        student=student_profile,
        term=reportcard.term
    ).select_related('subject', 'subject__teacher')

    context = {
        'reportcard': reportcard,
        'marks': marks,
        'total_score': reportcard.total_score(),
        'average_score': reportcard.average_score(),
        'term_config': term_config,
    }
    return render(request, 'accounts/student_reportcard_detail.html', context)


@login_required
@role_required('principal', 'vice_principal')
def configure_term_view(request):
    configs = TermConfig.objects.select_related('created_by').order_by('-created_at')

    if request.method == 'POST':
        form = TermConfigForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.school = request.user.school
            config.created_by = request.user
            try:
                config.save()
                messages.success(request, f"Term '{config.term}' configured successfully.")
                return redirect('configure_term')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = TermConfigForm()

    context = {
        'form': form,
        'configs': configs,
    }
    return render(request, 'accounts/configure_term.html', context)


@login_required
@role_required('principal', 'vice_principal')
def delete_term_config_view(request, config_id):
    config = get_object_or_404(TermConfig, id=config_id)
    if request.user.school != config.school:
        raise PermissionDenied
    config.delete()
    messages.success(request, f"Term '{config.term}' configuration deleted.")
    return redirect('configure_term')


@login_required
@role_required('principal', 'vice_principal')
def grant_print_permission_view(request):
    user = request.user
    validated_cards = ReportCard.objects.filter(
        validated=True,
        print_permission=False
    ).select_related(
        'student__user', 'student__school_class'
    ).order_by('student__user__first_name', 'student__user__last_name')

    printed_cards = ReportCard.objects.filter(
        print_permission=True
    ).select_related(
        'student__user', 'student__school_class', 'print_permission_granted_by'
    ).order_by('-print_permission_granted_at')[:20]

    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        action = request.POST.get('action')
        if card_id:
            reportcard = get_object_or_404(ReportCard, id=card_id, validated=True)
            if action == 'grant':
                reportcard.print_permission = True
                reportcard.print_permission_granted_by = user
                reportcard.print_permission_granted_at = timezone.now()
                reportcard.save()
                messages.success(
                    request,
                    f"Print permission granted for {reportcard.student.user.get_full_name()}."
                )
            elif action == 'revoke':
                reportcard.print_permission = False
                reportcard.print_permission_granted_by = None
                reportcard.print_permission_granted_at = None
                reportcard.save()
                messages.info(
                    request,
                    f"Print permission revoked for {reportcard.student.user.get_full_name()}."
                )
        return redirect('grant_print_permission')

    context = {
        'validated_cards': validated_cards,
        'printed_cards': printed_cards,
        'pending_print_count': validated_cards.count(),
    }
    return render(request, 'accounts/grant_print_permission.html', context)


@login_required
@role_required('principal', 'vice_principal', 'school_admin')
def manage_classes_view(request):
    user = request.user
    school = user.school
    if not school:
        messages.error(request, "You are not assigned to a school. Contact the system administrator.")
        return redirect('dashboard')
    classes = Class.objects.filter(school=school).select_related('class_master').prefetch_related('subjects')
    class_masters = CustomUser.objects.filter(role='class_master', school=school)
    all_subjects = Subject.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_class':
            name = request.POST.get('name', '').strip()
            series = request.POST.get('series', '')
            section = request.POST.get('section', '').strip()
            master_id = request.POST.get('class_master') or None
            if name:
                cls = Class.objects.create(name=name, series=series, section=section, school=school)
                if master_id:
                    cls.class_master = get_object_or_404(CustomUser, id=master_id, role='class_master', school=school)
                    cls.save()
                messages.success(request, f"Class '{cls.name}' created.")
            return redirect('manage_classes')

        elif action == 'assign_master':
            class_id = request.POST.get('class_id')
            master_id = request.POST.get('class_master')
            if class_id and master_id:
                cls = get_object_or_404(Class, id=class_id, school=school)
                new_master = get_object_or_404(CustomUser, id=master_id, role='class_master', school=school)
                cls.class_master = new_master
                cls.save()
                messages.success(request, f"Class master for {cls.name} updated.")
            return redirect('manage_classes')

        elif action == 'add_subject_to_class':
            class_id = request.POST.get('class_id')
            subject_id = request.POST.get('subject_id')
            if class_id and subject_id:
                cls = get_object_or_404(Class, id=class_id, school=school)
                subject = get_object_or_404(Subject, id=subject_id)
                cls.subjects.add(subject)
                messages.success(request, f"'{subject.name}' added to {cls.name}.")
            return redirect('manage_classes')

        elif action == 'remove_subject_from_class':
            class_id = request.POST.get('class_id')
            subject_id = request.POST.get('subject_id')
            if class_id and subject_id:
                cls = get_object_or_404(Class, id=class_id, school=school)
                subject = get_object_or_404(Subject, id=subject_id)
                cls.subjects.remove(subject)
                messages.success(request, f"'{subject.name}' removed from {cls.name}.")
            return redirect('manage_classes')

        return redirect('manage_classes')

    context = {
        'classes': classes,
        'class_masters': class_masters,
        'series_choices': Class.SERIES_CHOICES,
        'all_subjects': all_subjects,
    }
    return render(request, 'accounts/manage_classes.html', context)


@login_required
@role_required('principal', 'vice_principal', 'school_admin')
def manage_subjects_view(request):
    user = request.user
    school = user.school
    subjects = Subject.objects.prefetch_related('classes__school').all()
    teachers = CustomUser.objects.filter(
        role__in=('teacher', 'class_master', 'principal', 'vice_principal', 'school_admin'),
        school=school
    )
    classes = Class.objects.filter(school=school)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            teacher_id = request.POST.get('teacher') or None
            if name:
                teacher = CustomUser.objects.filter(id=teacher_id, is_active=True).first() if teacher_id else None
                Subject.objects.create(name=name, teacher=teacher)
                messages.success(request, f"Subject '{name}' added.")
        elif action == 'assign':
            subject_id = request.POST.get('subject_id')
            teacher_id = request.POST.get('teacher_id') or None
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id)
                subject.teacher = CustomUser.objects.filter(id=teacher_id, is_active=True).first() if teacher_id else None
                subject.save()
                messages.success(request, f"Teacher assigned to '{subject.name}'.")
        elif action == 'delete':
            subject_id = request.POST.get('subject_id')
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id)
                name = subject.name
                subject.delete()
                messages.success(request, f"Subject '{name}' permanently deleted.")
        elif action == 'remove_from_class':
            subject_id = request.POST.get('subject_id')
            class_id = request.POST.get('class_id')
            if subject_id and class_id:
                subject = get_object_or_404(Subject, id=subject_id)
                cls = get_object_or_404(Class, id=class_id, school=school)
                cls.subjects.remove(subject)
                messages.success(request, f"'{subject.name}' removed from {cls.name}.")
        return redirect('manage_subjects')

    context = {
        'subjects': subjects,
        'teachers': teachers,
        'classes': classes,
    }
    return render(request, 'accounts/manage_subjects.html', context)


@login_required
@role_required('school_admin', 'principal')
def manage_transcripts_view(request):
    transcripts = Transcript.objects.select_related(
        'student__user', 'student__school_class', 'generated_by', 'validated_by'
    ).order_by('-created_at')

    students = StudentProfile.objects.select_related('user', 'school_class').order_by(
        'school_class__name', 'user__last_name'
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate':
            student_id = request.POST.get('student_id')
            if student_id:
                student = get_object_or_404(StudentProfile, id=student_id)
                if not Transcript.objects.filter(student=student).exists():
                    Transcript.objects.create(student=student, generated_by=request.user)
                    messages.success(request, f"Transcript generated for {student.user.get_full_name()}.")
                else:
                    messages.warning(request, f"Transcript already exists for {student.user.get_full_name()}.")

        elif action == 'validate':
            transcript_id = request.POST.get('transcript_id')
            decision = request.POST.get('decision')
            if transcript_id:
                transcript = get_object_or_404(Transcript, id=transcript_id)
                if decision == 'approve':
                    transcript.validated = True
                    transcript.validated_by = request.user
                    transcript.validated_at = timezone.now()
                    transcript.save()
                    messages.success(request, f"Transcript validated for {transcript.student.user.get_full_name()}.")
                elif decision == 'reject':
                    transcript.validated = False
                    transcript.validated_by = None
                    transcript.validated_at = None
                    transcript.save()
                    messages.info(request, f"Transcript validation revoked for {transcript.student.user.get_full_name()}.")

        elif action == 'grant_print':
            transcript_id = request.POST.get('transcript_id')
            if transcript_id:
                transcript = get_object_or_404(Transcript, id=transcript_id, validated=True)
                transcript.print_permission = True
                transcript.save()
                messages.success(request, f"Print permission granted for transcript of {transcript.student.user.get_full_name()}.")

        return redirect('manage_transcripts')

    context = {
        'transcripts': transcripts,
        'students': students,
    }
    return render(request, 'accounts/manage_transcripts.html', context)


@login_required
@role_required('student')
def student_transcript_view(request):
    user = request.user
    try:
        student_profile = user.studentprofile
    except StudentProfile.DoesNotExist:
        messages.error(request, 'No student profile found.')
        return redirect('dashboard')

    transcripts = Transcript.objects.filter(student=student_profile).order_by('-created_at')

    if not transcripts:
        messages.info(request, 'No transcript has been generated for you yet.')
        return redirect('dashboard')

    context = {
        'student': student_profile,
        'transcripts': transcripts,
    }
    return render(request, 'accounts/student_transcript.html', context)


@login_required
@role_required('class_master')
def class_activities_view(request):
    user = request.user
    my_class = get_object_or_404(Class, class_master=user)
    activities = Activity.objects.filter(school_class=my_class).order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            max_score = request.POST.get('max_score', 20)
            if name:
                Activity.objects.create(name=name, school_class=my_class, max_score=max_score, created_by=user)
                messages.success(request, f"Activity '{name}' added to {my_class.name}.")
        elif action == 'delete':
            activity_id = request.POST.get('activity_id')
            if activity_id:
                activity = get_object_or_404(Activity, id=activity_id, school_class=my_class)
                activity.delete()
                messages.success(request, f"Activity '{activity.name}' removed.")
        return redirect('class_activities')

    context = {
        'my_class': my_class,
        'activities': activities,
    }
    return render(request, 'accounts/class_activities.html', context)


@login_required
@role_required('class_master')
def manage_class_subjects_view(request):
    user = request.user
    my_class = get_object_or_404(Class, class_master=user)
    all_subjects = Subject.objects.all()
    assigned_subjects = my_class.subjects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            subject_id = request.POST.get('subject_id')
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id)
                my_class.subjects.add(subject)
                messages.success(request, f"'{subject.name}' added to {my_class.name}.")
        elif action == 'remove':
            subject_id = request.POST.get('subject_id')
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id)
                my_class.subjects.remove(subject)
                messages.success(request, f"'{subject.name}' removed from {my_class.name}.")
        return redirect('manage_class_subjects')

    available_subjects = all_subjects.exclude(id__in=assigned_subjects.values_list('id', flat=True))

    context = {
        'my_class': my_class,
        'assigned_subjects': assigned_subjects,
        'available_subjects': available_subjects,
    }
    return render(request, 'accounts/manage_class_subjects.html', context)
