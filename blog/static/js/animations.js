/**
 * Smoothly scroll to a given position. Can be called before the previous scroll ends. Upon animation, the user cannot
 * manually scroll the page.
 * @param animationTime Milliseconds until arrival.
 */
const sst = (function (animationTime) {
    let st_pos, ed_pos, st_time, rendering = false;
    const scroll = (target) => {
        st_pos = document.documentElement.scrollTop;
        ed_pos = Math.min($(document).height() - $(window).height(),
            Math.floor(typeof (target) === 'string' ? $(target).position().top : target));
        st_time = Date.now();
        // Only renders if the previous animations has ended.
        if (!rendering) {
            render();
        }
    };
    const render = () => {
        rendering = true;
        // The scroll speed should be the fastest at the beginning, then gradually slower and finally drop to zero in
        // end. We use the [0, PI/2] part of the sine wave to implement this effect.
        // The half-amplitude is the total scroll distance, and the angle should relate to the proportion of total
        // scrolling time.
        const scrolled = (ed_pos - st_pos) * Math.sin(
            Math.min((Date.now() - st_time) / animationTime, 1) * Math.PI / 2
        );
        document.documentElement.scrollTop = st_pos + scrolled;
        // Check if the animation if not finished yet.
        if ((st_pos < ed_pos && document.documentElement.scrollTop < ed_pos) ||
            (st_pos > ed_pos && document.documentElement.scrollTop > ed_pos)) {
            window.requestAnimationFrame(render);
        } else {
            rendering = false;
        }
    };
    return scroll;
})(
    500
);

/**
 * Draw a net-liked background animation. This effect increases 10% ~ 20% CPU usage on my computer.
 * @param starDensity Density of dots.
 * @param horizontalSpeed Maximum horizontal speed of dots.
 * @param visionAngle Proportion of the visible area.
 * @param minDistance Lines became 100% solid if they are shorter than this distance.
 * @param maxDistance Lines became completely invisible if they are longer than this distance.
 */
const drawNet = (function (starDensity,
                           horizontalSpeed,
                           visionAngle,
                           minDistance,
                           maxDistance) {
    const visionAngleTan = Math.tan(2 * Math.PI * visionAngle);
    let cvs, ctx, w, h, last = 0, dots = [];
    const create = () => {
        cvs = $('canvas');
        [w, h] = [cvs.get(0).width, cvs.get(0).height] = [window.innerWidth, window.innerHeight];
        ctx = cvs.get(0).getContext('2d');
        // Randomly generate dots.
        for (let i = 0; i < 2 * w * h * starDensity; i++) {
            dots.push({
                r: Math.random(),                  // rotation (angle)
                y: Math.random() * 2 * h,          // vertical position
                k: Math.random() * horizontalSpeed // horizontal speed
            });
        }
        render();
    };
    const render = () => {
        const ms = Date.now();
        // Lock FPS to at most 40 in order to improve performance.
        if (ms - last > 25) {
            ctx.clearRect(0, 0, w, h);
            last = ms;
            const y = (document.documentElement.scrollTop / 2) % (2 * h); // the screen's vetical position.
            for (let i = 0; i < dots.length; i++) {
                // Calculate the x-axis position of this dot in advance, so we can know whether to skip this point.
                const ar = (dots[i].r + dots[i].k * ms) % 1;
                if (0.25 <= ar && ar <= 0.75) {
                    continue;
                }
                // Calculate the y-axis position on the screen.
                let ay = dots[i].y - y;
                if (ay < -0.5 * h) {
                    ay += 2 * h;
                }
                if (ay > 1.5 * h) {
                    ay -= 2 * h;
                }
                for (let j = i + 1; j < dots.length; j++) {
                    const br = (dots[j].r + dots[j].k * ms) % 1;
                    let by = dots[j].y - y;
                    if (by < -0.5 * h) {
                        by += 2 * h;
                    }
                    if (by > 1.5 * h) {
                        by -= 2 * h;
                    }
                    // Ignore if the line between two dots is completely out of the screen.
                    if ((0.25 <= br && br <= 0.75) || (
                        visionAngle <= ar && ar <= 1 - visionAngle &&
                        visionAngle <= br && br <= 1 - visionAngle) || (
                        ay < 0 && by < 0) || (
                        ay > h && by > h)) {
                        continue;
                    }
                    const ax = (1 - Math.tan(ar * 2 * Math.PI) / visionAngleTan) * w / 2;
                    const bx = (1 - Math.tan(br * 2 * Math.PI) / visionAngleTan) * w / 2;
                    const d2 = Math.sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by));
                    if (d2 <= maxDistance) {
                        // The line is solid if the distance is smaller than the minimum value. Otherwise, the alpha
                        // channel goes lower as the distance goes further. We use the [0, PI / 2] part of the sine wave
                        // to implement this effect.
                        const alpha = d2 <= minDistance
                            ? 1.0
                            : (1.0 - Math.sin((d2 - minDistance) / (maxDistance - minDistance) * Math.PI / 2));
                        // Actually draw the line.
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
})(
    0.000045,
    0.0001,
    0.125,
    100,
    550
);

$(document).ready(() => {
    const effects = [drawNet];
    // Choose a random effect.
    effects[Math.floor(Math.random() * effects.length)]();
});