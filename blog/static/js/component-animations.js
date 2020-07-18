const smoothScroll = (function () {
    const scroll_time = 500;
    let st_pos, ed_pos, st_time, rendering = false;
    const scroll = (position) => {
        st_pos = document.documentElement.scrollTop;
        ed_pos = Math.floor(position);
        if (!rendering) {
            render(st_time = Date.now());
        }
    };
    const render = () => {
        rendering = true;
        document.documentElement.scrollTop = st_pos + (ed_pos - st_pos) *
            Math.sin(Math.min((Date.now() - st_time) / scroll_time, 1) * Math.PI / 2);
        if ((st_pos < ed_pos && document.documentElement.scrollTop < ed_pos) ||
            (st_pos > ed_pos && document.documentElement.scrollTop > ed_pos)) {
            window.requestAnimationFrame(render);
        } else {
            rendering = false;
        }
    };
    return scroll;
})();

const drawNet = (function () {
    const star_density = 0.000045;
    const star_speed = 1 / 20000;
    const window_alpha = 1 / 8;
    const window_alpha_tan = Math.tan(2 * Math.PI * window_alpha);
    const line_min_d = 100;
    const line_max_d = 550;
    let cvs, ctx, w, h, last = 0, dots = [];
    const create = () => {
        cvs = $('canvas');
        [w, h] = [cvs.get(0).width, cvs.get(0).height] = [window.innerWidth, window.innerHeight];
        ctx = cvs.get(0).getContext('2d');
        for (let i = 0; i < 2 * w * h * star_density; i++) {
            dots.push({r: Math.random(), y: Math.random() * 2 * h, k: Math.random() * star_speed});
        }
        render();
    };
    const render = () => {
        const ms = Date.now();
        if (ms - last > 25) {
            ctx.clearRect(0, 0, w, h);
            last = ms;
            const y = (document.documentElement.scrollTop / 2) % (2 * h);
            for (let i = 0; i < dots.length; i++) {
                const ar = (dots[i].r + dots[i].k * ms) % 1;
                if (0.25 <= ar && ar <= 0.75) {
                    continue;
                }
                let ay = dots[i].y - y;
                if (ay < -0.5 * h) ay += 2 * h;
                if (ay > 1.5 * h) ay -= 2 * h;
                for (let j = i + 1; j < dots.length; j++) {
                    const br = (dots[j].r + dots[j].k * ms) % 1;
                    let by = dots[j].y - y;
                    if (by < -0.5 * h) by += 2 * h;
                    if (by > 1.5 * h) by -= 2 * h;
                    if ((0.25 <= br && br <= 0.75) || (
                        window_alpha <= ar && ar <= 1 - window_alpha &&
                        window_alpha <= br && br <= 1 - window_alpha) || (
                        ay < 0 && by < 0) || (
                        ay > h && by > h)) {
                        continue;
                    }
                    const ax = (1 - Math.tan(ar * 2 * Math.PI) / window_alpha_tan) * w / 2;
                    const bx = (1 - Math.tan(br * 2 * Math.PI) / window_alpha_tan) * w / 2;
                    const d2 = Math.sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by));
                    if (d2 <= line_max_d) {
                        const alpha = d2 <= line_min_d
                            ? 1.0
                            : (1.0 - Math.sin((d2 - line_min_d) / (line_max_d - line_min_d) * Math.PI / 2));
                        ctx.strokeStyle = `rgba(0, 0, 0, ${alpha})`;
                        ctx.beginPath();
                        ctx.moveTo(ax, ay);
                        ctx.lineTo(bx, by);
                        ctx.closePath();
                        ctx.stroke();
                    }
                }
            }
        }
        window.requestAnimationFrame(render);
    };
    return create;
})();

$(document).ready(() => {
    const smoothState = $('#main').smoothState({
        blacklist: '.no-smooth, .markdown-body a',
        onStart: {
            duration: 500,
            render: (old_page) => {
                old_page.find('.sidebar, .content').addClass('animate__animated animate__faster animate__fadeOutLeft');
                old_page.find('.footer').addClass('animate__animated animate__faster animate__fadeOut');
                smoothScroll(0);
                smoothState.restartCSSAnimations();
            }
        },
        onReady: {
            duration: 500,
            render: (old_page, new_page) => {
                old_page.html(new_page);
                new_page.find('.sidebar, .content').addClass('animate__animated animate__faster animate__fadeInRight');
                new_page.find('.footer').addClass('animate__animated animate__faster animate__fadeIn');
                smoothState.restartCSSAnimations();
            }
        }
    }).data('smoothState');
    drawNet();
});