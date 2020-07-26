$(document).ready(() => {
    $('textarea').each(function () {
        $(this).css('resize', 'none').css('height', this.scrollHeight + 'px').css('overflow-y', 'hidden');
    }).on('input', function () {
        $(this).css('height', 'auto').css('height', this.scrollHeight + 'px');
    });
    $('.form-file-input').change(function () {
        let files = [];
        for (let i = 0; i < $(this)[0].files.length; i++) {
            files.push($(this)[0].files[i].name);
        }
        $(this).parent().find('.form-file-text').text(files.join(', '));
    });
});