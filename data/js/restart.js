if (sbHttpsEnabled != "False" && sbHttpsEnabled != 0) 
	var sb_base_url = 'https://'+sbHost+':'+sbHttpPort+sbRoot;
else
    var sb_base_url = 'http://'+sbHost+':'+sbHttpPort+sbRoot;

var base_url = window.location.protocol+'//'+window.location.host+sbRoot;
var is_alive_url = sbRoot+'/home/is_alive';
var timeout_id;
var current_pid = '';
var num_restart_waits = 0;

function is_alive() {
    timeout_id = 0;
    $.get(is_alive_url, function(data) {
                                        
        // if it's still initalizing then just wait and try again
        if (data.msg == 'nope') {
            $('#shut_down_loading').hide();
            $('#shut_down_success').show();
            $('#restart_message').show();
            setTimeout('is_alive()', 1000);
        } else {
            // if this is before we've even shut down then just try again later
            if (current_pid == '' || data.msg == current_pid) {
                current_pid = data.msg;
                setTimeout(is_alive, 1000);

            // if we're ready to go then redirect to new url
            } else {
                $('#restart_loading').hide();
                $('#restart_success').show();
                $('#refresh_message').show();
                window.location = sb_base_url+'/home';
            }
        }
    }, 'jsonp');
}

$(document).ready(function() 
{ 

    is_alive();
    
    $('#shut_down_message').ajaxError(function(e, jqxhr, settings, exception) {
        num_restart_waits += 1;

        $('#shut_down_loading').hide();
        $('#shut_down_success').show();
        $('#restart_message').show();
        is_alive_url = sb_base_url+'/home/is_alive';

        // if https is enabled or you are currently on https and the port or protocol changed just wait 5 seconds then redirect. 
        // This is because the ajax will fail if the cert is untrusted or the the http ajax requst from https will fail because of mixed content error.
        if ((sbHttpsEnabled != "False" && sbHttpsEnabled != 0) || window.location.protocol == "https:") {
            if (base_url != sb_base_url) {
                timeout_id = 1;
                setTimeout(function(){
                    $('#restart_loading').hide();
                    $('#restart_success').show();
                    $('#refresh_message').show();
                }, 3000);
                setTimeout("window.location = sb_base_url+'/home'", 5000);
            }
        }

        // if it is taking forever just give up
        if (num_restart_waits > 90) {
            $('#restart_loading').hide();
            $('#restart_failure').show();
            $('#restart_fail_message').show();
            return;
        }

        if (timeout_id == 0)
            timeout_id = setTimeout('is_alive()', 1000);
    });

});
