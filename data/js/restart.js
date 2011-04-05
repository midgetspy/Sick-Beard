var is_alive_url = sbRoot+'/home/is_alive';
var timeout_id;
var current_pid = '';
var num_restart_waits = 0;

function is_alive() {
    timeout_id = 0;
    $.get(is_alive_url, function(data) {
                                        
        // if it's still initalizing then just wait and try again
        if (data == 'nope') {
            $('#shut_down_loading').hide();
            $('#shut_down_success').show();
            $('#restart_message').show();
            setTimeout('is_alive()', 1000);
        } else {
            // if this is before we've even shut down then just try again later
            if (current_pid == '' || data == current_pid) {
                current_pid = data;
                setTimeout(is_alive, 1000);

            // if we're ready to go then refresh the page which'll forward to /home
            } else {
                $('#restart_loading').hide();
                $('#restart_success').show();
                $('#refresh_message').show();
                location.reload();
            }
        }
    });
}

$(document).ready(function() 
{ 

    is_alive();
    
    $('#shut_down_message').ajaxError(function(e, jqxhr, settings, exception) {
        if (settings.url != is_alive_url)
            return;
        num_restart_waits += 1;

        $('#shut_down_loading').hide();
        $('#shut_down_success').show();
        $('#restart_message').show();

        // if it is taking forever just give up
        if (num_restart_waits > 30) {
            $('#restart_loading').hide();
            $('#restart_failure').show();
            $('#restart_fail_message').show();
            return;
        }

        if (timeout_id == 0)
            timeout_id = setTimeout('is_alive()', 1000);
    });

});
