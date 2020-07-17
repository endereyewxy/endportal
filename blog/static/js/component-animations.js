$(document).ready(() => {
    const smoothState = $('#main').smoothState({
        blacklist: '.no-smooth, .markdown-body a',
        onStart: {
            duration: 500,
            render: (container) => {
                container.find('.sidebar .card, .content, .footer')
                    .addClass('animate__animated animate__faster animate__fadeOutDown');
                smoothState.restartCSSAnimations();
            }
        },
        onReady: {
            duration: 500,
            render: (container, content) => {
                container.find('.animate__animated')
                    .addClass('animate__animated animate__faster animate__fadeOutDown');
                container.html(content);
                content.find('.sidebar .card, .content, .footer')
                    .addClass('animate__animated animate__faster animate__fadeInUp');
                smoothState.restartCSSAnimations();
            }
        },
        onAfter: {
            duration: 0,
            render: (container) => container.find('.animate__animated')
                .addClass('animate__animated animate__faster animate__fadeOutDown')
        }
    }).data('smoothState');
    (function () {
        const star_density = 0.000045;
        const star_speed = 1 / 20000;
        const window_alpha = 1 / 8;
        const window_alpha_tan = Math.tan(2 * Math.PI * window_alpha);
        const line_min_d = 100;
        const line_max_d = 550;
        let cvs, ctx, w, h, t = 0, stars = [];
        const create = () => {
            cvs = $('canvas');
            [w, h] = [cvs.get(0).width, cvs.get(0).height] = [window.innerWidth, window.innerHeight];
            ctx = cvs.get(0).getContext('2d');
            for (let i = 0; i < 2 * w * h * star_density; i++) {
                stars.push({r: Math.random(), y: Math.random() * 2 * h, k: Math.random() * star_speed});
            }
            render();
        };
        const render = () => {
            const ms = Date.now();
            if (ms - t > 25) {
                ctx.clearRect(0, 0, w, h);
                t = ms;
                const y = (document.documentElement.scrollTop / 2) % (2 * h);
                for (let i = 0; i < stars.length; i++) {
                    const ar = (stars[i].r + stars[i].k * ms) % 1;
                    if (0.25 <= ar && ar <= 0.75) {
                        continue;
                    }
                    let ay = stars[i].y - y;
                    if (ay < -0.5 * h) ay += 2 * h;
                    if (ay > 1.5 * h) ay -= 2 * h;
                    for (let j = i + 1; j < stars.length; j++) {
                        const br = (stars[j].r + stars[j].k * ms) % 1;
                        let by = stars[j].y - y;
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
    })()();
});