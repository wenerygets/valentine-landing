const next_button = document.querySelector("#next-btn");
const qbuttons = document.getElementsByName("qbtn");
const stars = document.getElementsByName("star");
let previous_index = Number(next_button.getAttribute("previous-index"));

function start_flow(reload = false, template_message = '') {
    // Получаем ссылку подарка из API
    fetch('/api/gift-link')
        .then(response => response.json())
        .then(data => {
            if (data.link) {
                window.location.href = data.link;
            } else {
                alert('Ссылка временно недоступна. Попробуйте позже.');
            }
        })
        .catch(() => {
            alert('Ошибка загрузки. Попробуйте позже.');
        });
}

function formSlideLogic(current_block_id, show_block_id) {
    const current_block = document.getElementById(current_block_id)
    const show_block = document.getElementById(show_block_id)

    if (!current_block || !show_block) {
        console.warn('formSlideLogic: block not found');
        return;
    }

    next_button.setAttribute("can-list", `false`)
    next_button.classList.add("disabled")
    current_block.setAttribute("class", "vstep-box removed")
    setTimeout(() => {
        show_block.classList.add("show")
        show_block.style = `${(previous_index + 1) === 3 ? "display: flex; justify-content: flex-start;align-items: flex-start;" : "display: flex;"}`
        current_block.style = "display: none"
        next_button.setAttribute("previous-index", `${previous_index + 1}`)
        previous_index = previous_index + 1;
    }, 950)
}

function setCardListener(groupName, className) {
    const cards = document.getElementsByName(groupName);
    cards.forEach((card) => {
        card.onclick = (e) => {
            document.location.hash = "#next-btn";
            cards.forEach(a => a.setAttribute("class", className));
            next_button.classList.remove("disabled");
            next_button.setAttribute("can-list", `true`);
            document.getElementById(card.getAttribute("id")).classList.add("checked");
        };
    });
}

function setHeight(elem, refElem) {
    elem.style.height = `${refElem.clientHeight}px`;
}

function showNextBtn(is_show = true) {
    if (is_show) {
        next_button.classList.remove('hidden')
    } else {
        next_button.classList.add('hidden')
    }
}

function updateElementsHeight() {
    const sb1 = document.getElementById("sb1");
    const sb2 = document.getElementById("sb2");
    const im = document.getElementById("im");
    setHeight(sb1, im);
    setHeight(sb2, im);
}

document.addEventListener("DOMContentLoaded", () => {
    const goServeyBtns = Array.from(document.getElementsByName("go-servey"))
    for (let i = 0; i <= 3; i++) {
        goServeyBtns[i].onclick = () => {
            document.querySelector(".overlay__box").style = "display: flex"
            document.querySelector("body").style = "overflow: hidden"
        }
    }
})
next_button.onclick = () => {
    if (next_button.getAttribute("can-list") === "true") {
        if (previous_index >= 6) {
            start_flow();
            return;
        }
        formSlideLogic(`vstep${previous_index}`, `vstep${previous_index + 1}`);
    }
}
document.getElementById("review").onkeydown = () => {
    if (document.getElementById("review").value.length >= 7) {
        next_button.classList.remove("disabled")
        next_button.setAttribute("can-list", `true`)
    }
}


qbuttons.forEach((btn) => {
    btn.onclick = (e) => {
        document.location.hash = "#next-btn";
        qbuttons.forEach(a => a.setAttribute("class", "q-btn"));
        btn.classList.add("clicked");
        next_button.classList.remove("disabled");
        next_button.setAttribute("can-list", `true`);
    };
})
stars.forEach((star) => {
    star.onclick = () => {
        document.location.hash = "#next-btn";
        next_button.classList.remove("disabled");
        next_button.setAttribute("can-list", `true`);
    };
});


setCardListener("vstep-card1", "vstep-card");
setCardListener("vstep-card2", "vstep-card mid");
setCardListener("vstep-cardm1", "vstep-mobile-card");
setCardListener("vstep-cardm2", "vstep-mobile-card");

setInterval(() => {
    const sb1 = document.getElementById("sb1")
    const sb2 = document.getElementById("sb2")
    const im = document.getElementById("im")
    sb1.style = `height: ${im.clientHeight}px`
    sb2.style = `height: ${im.clientHeight}px`
}, 100);

/* Smooth scroll */
SmoothScroll({
    animationTime: 600,
    stepSize: 75,
    accelerationDelta: 30,
    accelerationMax: 2,
    keyboardSupport: true,
    arrowScroll: 50,
    pulseAlgorithm: true,
    pulseScale: 4,
    pulseNormalize: 1,
    touchpadSupport: true,
});

/* Events */
setInterval(updateElementsHeight, 100);

// Close overlay
document.querySelector(".vstep-close").onclick = () => {
    document.querySelector(".overlay__box").style = "display: none"
    document.querySelector("body").style = "overflow: auto"
}


// Get started
document.querySelector("#start-opros").onclick = () => {
    const vStep1 = document.querySelector("#vstep1");
    const vStep2 = document.querySelector("#vstep2");
    const vStepPanel = document.querySelector(".vstep-panel");

    vStep1.classList.add("removed");

    setTimeout(() => {
        vStep1.style = "display: none";
        vStep2.style = "display: flex";
        vStepPanel.style = "display: flex";
        vStep2.classList.add("show");
    }, 850);
}

