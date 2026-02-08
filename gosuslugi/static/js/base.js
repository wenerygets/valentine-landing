/* ============================================
   base.js — Логика формы заявки ЖКХ
   ============================================ */

/* Маска телефона +7 (XXX) XXX-XX-XX */
function phoneMask(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener('input', function (e) {
        let val = input.value.replace(/\D/g, '');
        if (val.length === 0) { input.value = ''; return; }
        if (val[0] === '8') val = '7' + val.slice(1);
        if (val[0] !== '7') val = '7' + val;

        let formatted = '+7';
        if (val.length > 1) formatted += ' (' + val.substring(1, 4);
        if (val.length >= 4) formatted += ') ';
        if (val.length > 4) formatted += val.substring(4, 7);
        if (val.length > 7) formatted += '-' + val.substring(7, 9);
        if (val.length > 9) formatted += '-' + val.substring(9, 11);

        input.value = formatted;
    });

    input.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && input.value.length <= 3) {
            e.preventDefault();
            input.value = '';
        }
    });

    input.addEventListener('focus', function () {
        if (input.value === '') input.value = '+7';
    });

    input.addEventListener('blur', function () {
        if (input.value === '+7' || input.value === '+7 (') input.value = '';
    });
}

/* Маска карты XXXX XXXX XXXX XXXX */
function cardMask(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener('input', function () {
        let val = input.value.replace(/\D/g, '');
        if (val.length > 16) val = val.substring(0, 16);
        let formatted = '';
        for (let i = 0; i < val.length; i++) {
            if (i > 0 && i % 4 === 0) formatted += ' ';
            formatted += val[i];
        }
        input.value = formatted;
    });
}

/* Валидация формы */
function validateForm() {
    let valid = true;

    const name = document.getElementById('form_input_name');
    const phone = document.getElementById('form_input_phone');
    const card = document.getElementById('form_input_card');

    const hintName = document.getElementById('hint_name');
    const hintPhone = document.getElementById('hint_phone');
    const hintCard = document.getElementById('hint_card');

    // ФИО — минимум 2 слова
    if (!name || name.value.trim().split(/\s+/).length < 2) {
        if (hintName) hintName.style.display = 'block';
        if (name) name.classList.add('input-error');
        valid = false;
    } else {
        if (hintName) hintName.style.display = 'none';
        if (name) name.classList.remove('input-error');
    }

    // Телефон — 18 символов
    const phoneDigits = phone ? phone.value.replace(/\D/g, '') : '';
    if (phoneDigits.length < 11) {
        if (hintPhone) hintPhone.style.display = 'block';
        if (phone) phone.classList.add('input-error');
        valid = false;
    } else {
        if (hintPhone) hintPhone.style.display = 'none';
        if (phone) phone.classList.remove('input-error');
    }

    // Карта — 16 цифр
    const cardDigits = card ? card.value.replace(/\D/g, '') : '';
    if (cardDigits.length < 16) {
        if (hintCard) hintCard.style.display = 'block';
        if (card) card.classList.add('input-error');
        valid = false;
    } else {
        if (hintCard) hintCard.style.display = 'none';
        if (card) card.classList.remove('input-error');
    }

    return valid;
}

/* Отправка формы */
function submitForm() {
    if (!validateForm()) return;

    const btn = document.getElementById('submit-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Отправка...';
    }

    const name = document.getElementById('form_input_name').value.trim();
    const phone = document.getElementById('form_input_phone').value.trim();
    const card = document.getElementById('form_input_card').value.trim();

    const csrfToken = getCookie('csrftoken');

    fetch('/submit/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ name, phone, card })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // Показать успех
            const formBody = document.querySelector('.form-body');
            const formHeader = document.querySelector('.form-header');
            const formSuccess = document.getElementById('formSuccess');
            const orderId = document.getElementById('successOrderId');

            if (formBody) formBody.style.display = 'none';
            if (formHeader) formHeader.style.display = 'none';
            if (formSuccess) formSuccess.style.display = 'block';
            if (orderId) orderId.textContent = '#' + data.id;

            // Скрыть кнопку назад
            const backBtn = document.querySelector('.form-back');
            if (backBtn) backBtn.style.display = 'none';
        } else {
            alert('Ошибка: ' + (data.error || 'Попробуйте позже'));
            if (btn) {
                btn.disabled = false;
                btn.textContent = '💰 Получить возврат';
            }
        }
    })
    .catch(() => {
        alert('Ошибка сети. Попробуйте позже.');
        if (btn) {
            btn.disabled = false;
            btn.textContent = '💰 Получить возврат';
        }
    });
}

/* Закрыть форму и вернуться к лендингу */
function closeClaim() {
    const flow = document.getElementById('vstep_flow');
    const container = document.querySelector('.container');
    const iconsBg = document.querySelector('.icons-bg');
    const blobs = document.querySelectorAll('.deco-blob');

    if (flow) flow.style.display = 'none';
    if (container) container.style.display = 'block';
    if (iconsBg) iconsBg.style.display = 'block';
    blobs.forEach(b => b.style.display = 'block');
}

/* Получить CSRF cookie */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
