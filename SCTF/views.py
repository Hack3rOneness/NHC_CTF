import json
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count
from django.shortcuts import render, redirect
from datetime import timedelta
from django.utils import timezone
from SCTF.utils import set_game_duration, send_pause_message, send_start_message, send_resume_message, send_end_message, send_reset_message
from accounts.models import Team, UserProfile
from challenges.models import Challenge, ChallengeSolved, ChallengeFail
from cities_light.models import Country
from constance import config

def index(request):
    countries = Country.objects\
        .annotate(num_user=Count('userprofile'))\
        .filter(num_user__gt=0)
    parameters = {
        'users_count': get_user_model().objects.count(),
        'teams_count': Team.objects.count(),
        'challenges_count': Challenge.objects.count(),
        'total_points_count': Challenge.objects.total_points(),
        'user_points_count': request.user.profile.total_points,
        'countries_users': json.dumps({c.code2.lower(): c.num_user for c in countries}),
    }
    return render(request, 'sctf/base.html', parameters)

def _return_back_redirect(request):
    return redirect('/')

@user_passes_test(lambda u: u.is_superuser)
def game_play(request):
    if config.GAME_STATUS == settings.GAME_STATUS_SETUP:
        send_start_message()
    elif config.GAME_STATUS == settings.GAME_STATUS_PAUSE:
        send_resume_message()
    else:
        return _return_back_redirect(request)

    config.GAME_STATUS = settings.GAME_STATUS_PLAY
    config.GAME_START_DATETIME = timezone.now()
    return _return_back_redirect(request)

@user_passes_test(lambda u: u.is_superuser)
def game_pause(request):
    if config.GAME_STATUS == settings.GAME_STATUS_PLAY:
        send_pause_message()
        config.GAME_STATUS = settings.GAME_STATUS_PAUSE
        set_game_duration(timezone.now() - config.GAME_START_DATETIME)
    return _return_back_redirect(request)

@user_passes_test(lambda u: u.is_superuser)
def game_end(request):
    if config.GAME_STATUS in (settings.GAME_STATUS_PLAY, settings.GAME_STATUS_PAUSE):
        send_end_message()
        config.GAME_STATUS = settings.GAME_STATUS_FINISH
        set_game_duration(timedelta())
    return _return_back_redirect(request)

@user_passes_test(lambda u: u.is_superuser)
def game_reset(request):
    send_reset_message()
    _reset_game_status_challenges()
    return _return_back_redirect(request)

@user_passes_test(lambda u: u.is_superuser)
def game_reset_users(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    send_reset_message()
    UserProfile.objects.filter(user__is_staff=False).all().delete()
    User.objects.filter(is_staff=False).all().delete()
    _reset_game_status_challenges()
    return _return_back_redirect(request)

def _reset_game_status_challenges():
    config.GAME_STATUS = settings.GAME_STATUS_SETUP
    config.GAME_DURATION_DAYS = settings.CONSTANCE_CONFIG['GAME_DURATION_DAYS'][0]
    config.GAME_DURATION_HOURS = settings.CONSTANCE_CONFIG['GAME_DURATION_HOURS'][0]
    config.GAME_DURATION_MINS = settings.CONSTANCE_CONFIG['GAME_DURATION_MINS'][0]
    ChallengeSolved.objects.all().delete()
    ChallengeFail.objects.all().delete()

def game_paused_view(request):
    if config.GAME_STATUS != settings.GAME_STATUS_PAUSE:
        return _return_back_redirect(request)
    return render(request, 'sctf/game_paused.html')

def game_stopped_view(request):
    if config.GAME_STATUS != settings.GAME_STATUS_FINISH:
        return _return_back_redirect(request)
    return render(request, 'sctf/game_stopped.html', {
        'teams': Team.objects.ordered()[:3],
    })

def game_setup_state_view(request):
    if config.GAME_STATUS != settings.GAME_STATUS_SETUP:
        return _return_back_redirect(request)
    return render(request, 'sctf/game_setup.html')