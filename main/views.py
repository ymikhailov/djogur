# coding=utf-8

from django.http                    import HttpResponse, HttpResponseRedirect
from django.shortcuts               import render, get_object_or_404
from django.contrib                 import auth
from django.contrib.auth.decorators import login_required
from django.core.mail               import send_mass_mail
from django.db                      import IntegrityError

import json

from main.models import *

TASKS_PER_PAGE = 10

USER_PROFILE  = 0
ADMIN_PROFILE = 1

### helpers

def get_next_prev_page_number(page, items_count, items_per_page):
    has_pages = items_count > items_per_page

    if not has_pages:
        return None, None

    pages_count = items_count / items_per_page
    if items_count % items_per_page > 0:
        pages_count = pages_count + 1

    next_page = page + 1
    prev_page = page - 1

    if page == pages_count:
        next_page = None

    if page == 1:
        prev_page = None

    return next_page, prev_page

def get_next_prev_page_params(request, page_param_key, next_page, prev_page):
    params = "?"
    for k, v in request.GET.iteritems():
        if k != page_param_key:
            params += str(k) + "="
            params += str(v.encode('utf-8')) + "&"

    next_page_params = None
    if next_page != None:
        next_page_params = params + page_param_key + "=" + str(next_page)

    prev_page_params = None
    if prev_page != None:
        prev_page_params = params + page_param_key + "=" + str(prev_page)

    return next_page_params, prev_page_params

def get_user_stats(profile):
    tasks_count = Task.objects.filter(league = profile.league).count()

    if tasks_count == 0:
        return 0, 0

    solved_tasks_count      = profile.solved_tasks.count()
    solved_tasks_rate       = 1.0 * solved_tasks_count / tasks_count
    solved_tasks_percentage = int(100 * solved_tasks_rate)

    return solved_tasks_count, solved_tasks_percentage

def get_points(user, task):
    points = 0
    answer = get_answer(user, task)
    if answer and answer.is_correct:
        if answer.attempts == 1:
            points = 10
        elif answer.attempts == 2:
            points = 9
        elif answer.attempts == 3:
            points = 8
        else:
            points = 5

    return points

def get_users_rating(users):
    # convert QuerySet to list
    users = list(users)

    for user in users:
        user.points = 0
        for task in user.solved_tasks.all():
            user.points = user.points + get_points(user, task)

    users.sort(key = lambda(user) : user.points, reverse = True)

    rating    = 1
    prev_user = None

    for user in users:
        if prev_user != None:
            if prev_user.points != user.points:
                rating = rating + 1

        user.rating = rating
        prev_user   = user

    return users

def get_user_rating(profile, users_rating):
    user_rating = None

    for user in users_rating:
        if user.id == profile.id:
            user_rating = user.rating

    return user_rating

def get_user_points(profile, users_rating):
    points = None

    for user in users_rating:
        if user.id == profile.id:
            points = user.points

    return points

def get_answer(profile, task):
    answer = None

    answer_exists = Answer.objects.filter(profile = profile, task = task).exists()
    if answer_exists:
        answer = Answer.objects.get(profile = profile, task = task)

    return answer

def add_money(profile, amount):
    profile.money = profile.money + amount
    profile.save()

def process_user_answer(profile, task_id, user_answer):
    if user_answer != "":
        task = Task.objects.get(id = int(task_id))

        answer = get_answer(profile, task)
        if answer != None:
            if answer.is_correct == False and answer.answer != user_answer:
                answer.answer   = user_answer
                answer.attempts = answer.attempts + 1

                if task.right_answer == user_answer:
                    answer.is_correct = True
                    answer.save()

                    profile.solved_tasks.add(task)
                    add_money(profile, get_points(profile, task))
                else:
                    answer.save()
        else:
            answer = Answer()

            answer.profile  = profile
            answer.task     = task
            answer.answer   = user_answer
            answer.attempts = 1

            if task.right_answer == user_answer:
                answer.is_correct = True
                answer.save()
                
                profile.solved_tasks.add(task)
                add_money(profile, get_points(profile, task))
            else:
                answer.save()

def get_profile_type(user):
    profile_type = None
    if hasattr(user, "profile"):
        profile_type = USER_PROFILE
    elif hasattr(user, "adminprofile"):
        profile_type = ADMIN_PROFILE
    return profile_type

def get_league_text(league):
    for lg in LEAGUE:
        if lg[0] == league:
            return lg[1]

    return None

### request handlers

def index(request):
    has_error     = False
    error_message = ""

    authorized = request.user.is_authenticated()

    if authorized:
        profile_type = get_profile_type(request.user)
        if profile_type == USER_PROFILE:
            return HttpResponseRedirect("/profile/")
        elif profile_type == ADMIN_PROFILE:
            return HttpResponseRedirect("/admin_panel/")

    if request.method == "POST":
        if "login" in request.POST:
            username = request.POST["username"]
            password = request.POST["password"]

        user = auth.authenticate(username = username, password = password)
        if user != None and user.is_active:
            auth.login(request, user)

            profile_type = get_profile_type(user)
            if profile_type == USER_PROFILE:
                return HttpResponseRedirect("/profile/")
            elif profile_type == ADMIN_PROFILE:
                return HttpResponseRedirect("/admin_panel/")
        else:
            has_error     = True
            error_message = "Не удалось войти в систему"

    return render(request, 'main/index.html', locals())

def profile(request):
    authorized = request.user.is_authenticated()

    if not authorized:
        return HttpResponseRedirect("/")

    profile_type = get_profile_type(request.user)
    if profile_type == USER_PROFILE:
        profile = request.user.profile
    else:
        return HttpResponseRedirect("/")

    # process user answer

    if request.method == "POST" and "send_answer" in request.POST:
        task_id     = request.POST["task_id"]
        user_answer = request.POST["answer"]

        process_user_answer(profile, task_id, user_answer)

    # filter

    filter = None

    if request.method == "GET" and "filter" in request.GET:
        filter = request.GET["filter"]

    if request.method == "POST" and "filter" in request.POST:
        filter = request.POST["filter"]
        print filter

    # current page

    page  = 1
    count = TASKS_PER_PAGE
    if 'page' in request.GET:
        page  = int(request.GET['page'])

    # tasks

    st = (page - 1) * count
    en = st + count

    tasks_count = 0
    tasks       = []

    if not filter or filter == "all":
        tasks_count = Task.objects.filter(league = profile.league).count()
        tasks       = Task.objects.filter(league = profile.league).order_by("date_created")[st:en]
    elif filter == "solved":
        tasks_count = profile.solved_tasks.count()
        tasks       = profile.solved_tasks.order_by("date_created")[st:en]
    elif filter == "unsolved":
        tasks_count = Task.objects.filter(league = profile.league).exclude(id__in = profile.solved_tasks.values('id')).count()
        tasks       = Task.objects.filter(league = profile.league).exclude(id__in = profile.solved_tasks.values('id')).order_by("date_created")[st:en]

    # extend tasks

    for task in tasks:
        task.solved   = False
        task.status   = "не решено"
        task.answer   = ""
        task.attempts = 0

        answer = get_answer(profile, task)
        if answer != None:
            task.answer   = answer.answer
            task.attempts = answer.attempts
            if answer.is_correct:
                task.solved = True
                task.status = "решено"

    # league

    league = get_league_text(profile.league)

    # money

    money = profile.money

    # user statistics

    solved_tasks_count, solved_tasks_percentage = get_user_stats(profile)

    # rating

    users        = Profile.objects.filter(league = profile.league)
    users_rating = get_users_rating(users)

    my_rating = get_user_rating(profile, users_rating)
    my_points = get_user_points(profile, users_rating)
    top10     = users_rating[:10]

    # next and prev page

    next_page_number, prev_page_number = get_next_prev_page_number(page, tasks_count, TASKS_PER_PAGE)
    next_page_params, prev_page_params = get_next_prev_page_params(request, "page", next_page_number, prev_page_number)

    return render(request, 'main/profile.html', locals())

def admin_panel(request):
    authorized = request.user.is_authenticated()

    if not authorized:
        return HttpResponseRedirect("/")

    profile_type = get_profile_type(request.user)
    if profile_type == ADMIN_PROFILE:
        profile = request.user.adminprofile
    else:
        return HttpResponseRedirect("/")

    league_1_code = LEAGUE[0][0]
    league_2_code = LEAGUE[1][0]

    league_1 = LEAGUE[0][1]
    league_2 = LEAGUE[1][1]

    # filter

    filter = None

    if request.method == "GET" and "filter" in request.GET:
        filter = request.GET["filter"]

    if request.method == "POST" and "filter" in request.POST:
        filter = request.POST["filter"]

    # process create task button click

    if request.method == "POST" and "create_task" in request.POST:
        return HttpResponseRedirect("/create_task/")

    # process edit task button click

    if request.method == "POST" and "edit_task" in request.POST:
        task_id = request.POST["task_id"]

        return HttpResponseRedirect("/edit_task/" + task_id)

    # process delete task button click

    if request.method == "POST" and "delete_task" in request.POST:
        task_id = request.POST["task_id"]

        task = Task.objects.get(id = int(task_id))
        task.delete()

    # current page

    page  = 1
    count = TASKS_PER_PAGE
    if 'page' in request.GET:
        page  = int(request.GET['page'])

    # tasks

    st = (page - 1) * count
    en = st + count

    if filter == None or filter == league_1_code:
        tasks_count = Task.objects.filter(league = league_1_code).count()
        tasks       = Task.objects.filter(league = league_1_code).order_by("date_created")[st:en]
    elif filter == league_2_code:
        tasks_count = Task.objects.filter(league = league_2_code).count()
        tasks       = Task.objects.filter(league = league_2_code).order_by("date_created")[st:en]

    # tasks count

    league_1_tasks_count = Task.objects.filter(league = league_1_code).count()
    league_2_tasks_count = Task.objects.filter(league = league_2_code).count()

    # rating

    users_1        = Profile.objects.filter(league = league_1_code)
    users_rating_1 = get_users_rating(users_1)

    users_2         = Profile.objects.filter(league = league_2_code)
    users_rating_2 = get_users_rating(users_2)

    top10_1 = users_rating_1[:10]
    top10_2 = users_rating_2[:10]

    # next and prev page

    next_page_number, prev_page_number = get_next_prev_page_number(page, tasks_count, TASKS_PER_PAGE)
    next_page_params, prev_page_params = get_next_prev_page_params(request, "page", next_page_number, prev_page_number)

    return render(request, 'main/admin_panel.html', locals())

def create_task(request):
    has_error     = False
    error_message = ""

    authorized = request.user.is_authenticated()

    if not authorized:
        return HttpResponseRedirect("/")

    profile_type = get_profile_type(request.user)
    if profile_type == ADMIN_PROFILE:
        profile = request.user.adminprofile
    else:
        return HttpResponseRedirect("/")

    league_1_code = LEAGUE[0][0]
    league_2_code = LEAGUE[1][0]

    league_1 = LEAGUE[0][1]
    league_2 = LEAGUE[1][1]

    if request.method == "POST" and "create" in request.POST:
        league       = request.POST["league"]
        title        = request.POST["title"]
        content      = request.POST["content"]
        image        = ""
        right_answer = request.POST["right_answer"]

        if "image" in request.FILES:
            image = request.FILES["image"]

        if league == "" or title == "" or content == "" or right_answer == "":
            has_error     = True
            error_message = "Необходимо заполнить все обязательные поля"

            return render(request, 'main/create_task.html', locals())

        task = Task()

        task.league       = league
        task.title        = title
        task.content      = content
        task.image        = image
        task.right_answer = right_answer

        task.save()

        return HttpResponseRedirect("/admin_panel/?filter=" + league)

    return render(request, 'main/create_task.html', locals())

def edit_task(request, task_id):
    has_error     = False
    error_message = ""

    authorized = request.user.is_authenticated()

    if not authorized:
        return HttpResponseRedirect("/")

    profile_type = get_profile_type(request.user)
    if profile_type == ADMIN_PROFILE:
        profile = request.user.adminprofile
    else:
        return HttpResponseRedirect("/")

    league_1_code = LEAGUE[0][0]
    league_2_code = LEAGUE[1][0]

    league_1 = LEAGUE[0][1]
    league_2 = LEAGUE[1][1]

    task = Task.objects.get(id = task_id)

    league       = task.league
    title        = task.title
    content      = task.content
    image        = task.image
    remove_image = False
    new_image    = ""
    right_answer = task.right_answer

    if request.method == "POST" and "save" in request.POST:
        league       = request.POST["league"]
        title        = request.POST["title"]
        content      = request.POST["content"]
        right_answer = request.POST["right_answer"]

        if "remove_image" in request.POST:
            remove_image = True

        if "new_image" in request.FILES:
            new_image = request.FILES["new_image"]

        if league == "" or title == "" or content == "" or right_answer == "":
            has_error     = True
            error_message = "Необходимо заполнить все обязательные поля"

            return render(request, 'main/edit_task.html', locals())

        if new_image != "":
            image = new_image
        else:
            if remove_image:
                image = ""

        task.league       = league
        task.title        = title
        task.content      = content
        task.image        = image
        task.right_answer = right_answer

        task.save()

        return HttpResponseRedirect("/admin_panel/?filter=" + league)

    return render(request, 'main/edit_task.html', locals())

def users(request):
    authorized = request.user.is_authenticated()

    if not authorized:
        profile = None
    else:
        profile_type = get_profile_type(request.user)
        if profile_type == USER_PROFILE:
            profile = request.user.profile
        else:
            profile = request.user.adminprofile

    user_profile  = USER_PROFILE
    admin_profile = ADMIN_PROFILE

    league_1_code = LEAGUE[0][0]
    league_2_code = LEAGUE[1][0]

    league_1 = LEAGUE[0][1]
    league_2 = LEAGUE[1][1]

    # rating

    users_1        = Profile.objects.filter(league = league_1_code)
    users_rating_1 = get_users_rating(users_1)

    users_2         = Profile.objects.filter(league = league_2_code)
    users_rating_2 = get_users_rating(users_2)

    return render(request, 'main/users.html', locals())

def money(request):
    authorized = request.user.is_authenticated()

    if not authorized:
        return HttpResponseRedirect("/")

    profile_type = get_profile_type(request.user)
    if profile_type == ADMIN_PROFILE:
        profile = request.user.adminprofile
    else:
        return HttpResponseRedirect("/")

    user_profile  = USER_PROFILE
    admin_profile = ADMIN_PROFILE

    league_1_code = LEAGUE[0][0]
    league_2_code = LEAGUE[1][0]

    league_1 = LEAGUE[0][1]
    league_2 = LEAGUE[1][1]

    users_1 = Profile.objects.filter(league = league_1_code)
    users_2 = Profile.objects.filter(league = league_2_code)

    return render(request, 'main/money.html', locals())

def logout(request):
    auth.logout(request)

    return HttpResponseRedirect("/")

### API ###

def api_get_balance(request):
    id = int(request.GET["id"])

    result = {}
    if Profile.objects.filter(pk = id).exists():
        profile = Profile.objects.get(pk = id)
        result  = {"code": 0, "balance": profile.money, "name": profile.first_name + " " + profile.last_name}
    else:
        result = {"code": 1}

    return HttpResponse(json.dumps(result))

def api_deposit(request):
    id     = int(request.GET["id"])
    amount = int(request.GET["amount"])

    result = {"code": 0}
    if Profile.objects.filter(pk = id).exists():
        profile = Profile.objects.get(pk = id)
        profile.money = profile.money + amount
        profile.save()
    else:
        result = {"code": 1}

    return HttpResponse(json.dumps(result))

def api_withdraw(request):
    id     = int(request.GET["id"])
    amount = int(request.GET["amount"])

    result = {"code": 0}
    if Profile.objects.filter(pk = id).exists():
        profile = Profile.objects.get(pk = id)
        profile.money = profile.money - amount
        profile.save()
    else:
        result = {"code": 1}

    return HttpResponse(json.dumps(result))
