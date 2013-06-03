var message_url = sbRoot + '/ui/get_messages';
$.pnotify.defaults.width = "400px";
$.pnotify.defaults.styling = "jqueryui";
$.pnotify.defaults.history = false;
$.pnotify.defaults.shadow = false;
$.pnotify.defaults.delay = 4000;

function check_notifications() {
    $.getJSON(message_url, function (data) {
        $.each(data, function (name, data) {
            $.pnotify({
                type: data.type,
                hide: data.type == 'notice',
                title: data.title,
                text: data.message
            });
        });
    });

    setTimeout(check_notifications, 3000);
}

$(document).ready(function () {

    check_notifications();

});