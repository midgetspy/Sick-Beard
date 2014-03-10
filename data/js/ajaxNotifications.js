var message_url = sbRoot + '/ui/get_messages/';
$.pnotify.defaults.width = "400px";
$.pnotify.defaults.styling = "jqueryui";
$.pnotify.defaults.history = false;
$.pnotify.defaults.shadow = false;
$.pnotify.defaults.delay = 4000;
$.pnotify.defaults.maxonscreen = 5;

function check_notifications() {
    var poll_interval = 5000;
    $.ajax({
        url: message_url,
        success: function (data) {
            poll_interval = 5000;
            $.each(data, function (name, data) {
                $.pnotify({
                    type: data.type,
                    hide: data.type == 'notice',
                    title: data.title,
                    text: data.message
                });
            });
        },
        error: function () {
            poll_interval = 15000;
        },
        type: "GET",
        dataType: "json",
        complete: function () {
            setTimeout(check_notifications, poll_interval);
        },
        timeout: 15000 // timeout every 15 secs
    });
}

$(document).ready(function () {

    check_notifications();

});
