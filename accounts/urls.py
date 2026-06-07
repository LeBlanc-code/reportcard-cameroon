from django.shortcuts import redirect
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('admin/', lambda request: redirect('/admin/')),
    path('login/',       views.login_view,      name='login'),
    path('signup/',      views.signup_view,      name='signup'),
    path('logout/',      views.logout_view,      name='logout'),
    path('dashboard/',   views.dashboard_view,   name='dashboard'),
    path('create-user/', views.create_user_view, name='create_user'),
    path('enter-mark/',  views.enter_mark_view,  name='enter_mark'),
    path('my-classes/',  views.teacher_my_classes_view, name='teacher_my_classes'),
    path('validate-reportcards/', views.validate_reportcards_view, name='validate_reportcards'),
    path('validate-reportcard/<int:reportcard_id>/', views.validate_reportcard_detail_view, name='validate_reportcard_detail'),

    path('class-statistics/', views.class_statistics_view, name='class_statistics'),

    path('my-reportcard/', views.student_reportcard_view, name='student_reportcard'),
    path('my-reportcard/<int:reportcard_id>/', views.student_reportcard_detail_view, name='student_reportcard_detail'),

    path('configure-term/', views.configure_term_view, name='configure_term'),
    path('configure-term/<int:config_id>/delete/', views.delete_term_config_view, name='delete_term_config'),

    path('grant-print-permission/', views.grant_print_permission_view, name='grant_print_permission'),

    path('manage-classes/', views.manage_classes_view, name='manage_classes'),
    path('manage-subjects/', views.manage_subjects_view, name='manage_subjects'),

    path('manage-transcripts/', views.manage_transcripts_view, name='manage_transcripts'),
    path('my-transcript/', views.student_transcript_view, name='student_transcript'),

    path('class-activities/', views.class_activities_view, name='class_activities'),
    path('manage-class-subjects/', views.manage_class_subjects_view, name='manage_class_subjects'),

    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset_form.html',
             email_template_name='accounts/password_reset_email.html',
             success_url='done/'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/password-reset-complete/'
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]
