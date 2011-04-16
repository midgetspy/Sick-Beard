var message_url = sbRoot + '/ui/get_messages';

function check_notifications() {
    $.getJSON(message_url, function(data){
        $.each(data, function(name,data){
            $.pnotify({
                pnotify_type: data.type,
                pnotify_hide: data.type == 'notice',
                pnotify_title: data.title,
                pnotify_text: data.message
            });
        });
    });
    
    setTimeout(check_notifications, 3000)
}

$(document).ready(function(){

    check_notifications();

});