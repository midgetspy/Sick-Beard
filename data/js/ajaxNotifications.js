var message_url = sbRoot + '/ui/get_messages';
$.pnotify.defaults.pnotify_width = "340px";
$.pnotify.defaults.styling = "jqueryui";
$.pnotify.defaults.pnotify_history = false;
$.pnotify.defaults.pnotify_delay = 4000;

function check_notifications() {
    $.getJSON(message_url, function (data) {
        $.each(data, function (name, data) {
            $.pnotify({
                pnotify_type: data.type,
                pnotify_hide: data.type == 'notice',
                pnotify_title: data.title,
                pnotify_text: data.message,
                pnotify_shadow: false
            });
        });
    });

    setTimeout(check_notifications, 3000);
}

$(document).ready(function () {

    check_notifications();

});