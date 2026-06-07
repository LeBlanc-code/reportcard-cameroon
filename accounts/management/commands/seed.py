from django.core.management.base import BaseCommand
from accounts.models import (
    School, CustomUser, Class, StudentProfile, Subject, ReportCard, TermConfig
)
from datetime import date, time, timedelta


class Command(BaseCommand):
    help = 'Seed the database with test data for development'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # School
        school, _ = School.objects.get_or_create(
            name='Government Bilingual High School Yaounde',
            defaults={'address': 'Yaounde, Centre Region'}
        )

        # Users
        users = {
            'admin': ('System', 'Admin', 'school_admin', True),
            'principal1': ('Jean', 'Mbarga', 'principal', False),
            'vice1': ('Marie', 'Etoundi', 'vice_principal', False),
            'master1': ('Paul', 'Biya', 'class_master', False),
            'teacher1': ('Alice', 'Ndongo', 'teacher', False),
            'student1': ('Junior', 'Kamga', 'student', False),
        }

        created_users = {}
        for username, (first, last, role, is_super) in users.items():
            try:
                user = CustomUser.objects.get(username=username)
                created = False
            except CustomUser.DoesNotExist:
                user = CustomUser(
                    username=username,
                    email=f'{username}@school.cm',
                    first_name=first,
                    last_name=last,
                    role=role,
                    school=school,
                    is_superuser=is_super,
                    is_staff=is_super,
                )
                user.set_password('pass123')
                user.save()
                created = True
            created_users[username] = user
            self.stdout.write(f'  User: {username} ({role})')

        # Subjects
        subjects_list = [
            'Mathematics', 'English', 'French', 'Geography', 'Biology',
            'Chemistry', 'Physics', 'Sports', 'Manual Labour',
            'Home Economics', 'History', 'Citizenship', 'Religious Studies', 'Computer'
        ]
        for name in subjects_list:
            Subject.objects.get_or_create(name=name)

        # Assign teacher to subjects
        teacher = created_users['teacher1']
        for name in ['Mathematics', 'Physics', 'Chemistry']:
            subj = Subject.objects.get(name=name)
            subj.teacher = teacher
            subj.save()

        # Classes - Form 1 to 5
        for i in range(1, 6):
            cls, _ = Class.objects.get_or_create(
                name=f'Form {i}', school=school,
                defaults={'series': '', 'section': ''}
            )
            cls.subjects.set(Subject.objects.all())

        # Assign class master to Form 1
        form1 = Class.objects.get(name='Form 1', school=school)
        form1.class_master = created_users['master1']
        form1.save()

        # Lower Sixth classes
        for code in ['A1', 'A2', 'A3', 'A4', 'S1', 'S2', 'S3', 'S4']:
            series_type = 'Arts' if code.startswith('A') else 'Sciences'
            Class.objects.get_or_create(
                name=f'Lower Sixth {series_type} {code}',
                school=school,
                defaults={'series': code, 'section': ''}
            )
            Class.objects.get_or_create(
                name=f'Upper Sixth {series_type} {code}',
                school=school,
                defaults={'series': code, 'section': ''}
            )

        # Student profile
        student_user = created_users['student1']
        sp, _ = StudentProfile.objects.get_or_create(
            user=student_user,
            defaults={'school_class': form1}
        )
        sp.school_class = form1
        sp.save()

        # Report card
        ReportCard.objects.get_or_create(student=sp, term='Term 1')

        # Term configs (past, current, future)
        past = date.today() - timedelta(days=30)
        past_deadline = past - timedelta(days=2)
        future = date.today() + timedelta(days=14)
        deadline = future - timedelta(days=2)
        TermConfig.objects.get_or_create(
            school=school, term='Term 1',
            defaults={
                'closing_date': past,
                'closing_time': time(15, 30),
                'marks_deadline': past_deadline,
                'created_by': created_users['principal1'],
            }
        )
        TermConfig.objects.get_or_create(
            school=school, term='Term 2',
            defaults={
                'closing_date': future,
                'closing_time': time(15, 30),
                'marks_deadline': deadline,
                'created_by': created_users['principal1'],
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeding complete! {Class.objects.filter(school=school).count()} classes, '
            f'{Subject.objects.count()} subjects, {CustomUser.objects.count()} users.'
        ))
        self.stdout.write('\nTest accounts (password: pass123):')
        self.stdout.write('  admin / admin123 (superuser)')
        for username in ['principal1', 'vice1', 'master1', 'teacher1', 'student1']:
            self.stdout.write(f'  {username} / pass123')
