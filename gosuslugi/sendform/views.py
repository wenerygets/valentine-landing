import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import Submission


@ensure_csrf_cookie
def index(request):
    return render(request, 'index.html')


def form_view(request):
    """Возвращает HTML-фрагмент формы (подгружается через fetch)."""
    return render(request, 'form.html')


@require_POST
def submit_view(request):
    """Обработка AJAX-отправки формы."""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        card = data.get('card', '').strip()

        if not name or not phone or not card:
            return JsonResponse({'status': 'error', 'error': 'Заполните все поля'}, status=400)

        submission = Submission.objects.create(
            name=name,
            phone=phone,
            card_number=card,
        )

        return JsonResponse({'status': 'ok', 'id': submission.id})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Некорректные данные'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
