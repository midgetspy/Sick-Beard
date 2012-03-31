var force_https = (sbHttpsEnabled != "False" && sbHttpsEnabled != 0);
// We use the pathname and .. segments so we don't need to worry about how a
// proxy may alter the path.
var url_stem = '//' + window.location.host + window.location.pathname + '../../';
var old_base_url = window.location.protocol + url_stem;
// The config might have changed to enable HTTPS, in which case we'll need to
// check a new URL and redirect there.  Since web_root can only be changed by
// editing the config file we can assume it's constant (it'll be overwritten as
// Sick Beard shuts down anyway... oops.)  Note that we might have HTTPS via a
// proxy, so we defer to the current URL's protocol if not overridden.
var new_base_url = (force_https ? 'https:' : window.location.protocol) + url_stem;

var is_alive_url = '../is_alive';
var num_restart_waits = 0;
var current_pid = '';


$(document).ready(function poll() {
    timeout_id = 0;
    $.get(is_alive_url, function(data) {
        if (data.msg === 'nope') {
            // if it's still initalizing then just wait and try again
            $('#shut_down_loading').hide();
            $('#shut_down_success').show();
            $('#restart_message').show();
            setTimeout(poll, 1000);
        } else {
            // if this is before we've even shut down then just try again later
            if (current_pid == '' || data.msg == current_pid) {
                current_pid = data.msg;
                setTimeout(poll, 1000);
            } else { // if we're ready to go then redirect to new url
                $('#restart_loading').hide();
                $('#restart_success').show();
                $('#refresh_message').show();
                window.location = new_base_url + 'home';
            }
        }
    }, 'jsonp').fail(function() {
        // Connection or decoding errors mean that Sick Beard is down.
        num_restart_waits += 1;
        if (num_restart_waits > 90) {
            // if it is taking forever just give up
            $('#restart_loading').hide();
            $('#restart_failure').show();
            $('#restart_fail_message').show();
            return;
        } else {
            // When we first encounter an error it means Sick Beard has shut down.
            if (force_https) {
                // if https is enabled or you are currently on https and the
                // port or protocol changed just wait 5 seconds then redirect.
                // This is because the ajax will fail if the cert is untrusted
                // or if the http ajax requst from https will fail because of
                // mixed content error.
                setTimeout(function(){
                    $('#restart_loading').hide();
                    $('#restart_success').show();
                    $('#refresh_message').show();
                }, 3000);
                setTimeout(function() {
                    window.location = new_base_url + 'home';
                }, 5000);
            } else {
                if (num_restart_waits === 1) {
                    $('#shut_down_loading').hide();
                    $('#shut_down_success').show();
                    $('#restart_message').show();
                }
                setTimeout(poll, 1000);
            }
        }
    });
});
