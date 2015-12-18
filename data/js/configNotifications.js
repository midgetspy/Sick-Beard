$(document).ready(function () {
    var loading = '<img src="' + sbRoot + '/images/loading16.gif" height="16" width="16" />';

    $("#testGrowl").click(function () {
        var growl_host = $.trim($("#growl_host").val());
        var growl_password = $.trim($("#growl_password").val());
        if (!growl_host) {
            $("#testGrowl-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testGrowl-result").html(loading);
        $.get(sbRoot + "/home/testGrowl", {'host': growl_host, 'password': growl_password})
            .done(function (data) {
                $("#testGrowl-result").html(data);
                $("#testGrowl").prop("disabled", false);
            });
    });

    $("#testProwl").click(function () {
        var prowl_api = $.trim($("#prowl_api").val());
        var prowl_priority = $("#prowl_priority").val();
        if (!prowl_api) {
            $("#testProwl-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testProwl-result").html(loading);
        $.get(sbRoot + "/home/testProwl", {'prowl_api': prowl_api, 'prowl_priority': prowl_priority})
            .done(function (data) {
                $("#testProwl-result").html(data);
                $("#testProwl").prop("disabled", false);
            });
    });

    $("#testXBMC").click(function () {
        var xbmc_host = $.trim($("#xbmc_host").val());
        var xbmc_username = $.trim($("#xbmc_username").val());
        var xbmc_password = $.trim($("#xbmc_password").val());
        if (!xbmc_host) {
            $("#testXBMC-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testXBMC-result").html(loading);
        $.get(sbRoot + "/home/testXBMC", {'host': xbmc_host, 'username': xbmc_username, 'password': xbmc_password})
            .done(function (data) {
                $("#testXBMC-result").html(data);
                $("#testXBMC").prop("disabled", false);
            });
    });

    $("#testPLEX").click(function () {
        var plex_host = $.trim($("#plex_host").val());
        var plex_username = $.trim($("#plex_username").val());
        var plex_password = $.trim($("#plex_password").val());
        if (!plex_host) {
            $("#testPLEX-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testPLEX-result").html(loading);
        $.get(sbRoot + "/home/testPLEX", {'host': plex_host, 'username': plex_username, 'password': plex_password})
            .done(function (data) {
                $("#testPLEX-result").html(data);
                $("#testPLEX").prop("disabled", false);
            });
    });

    $("#testBoxcar2").click(function () {
        var boxcar2_access_token = $.trim($("#boxcar2_access_token").val());
        var boxcar2_sound = $("#boxcar2_sound").val() || "default";
        if (!boxcar2_access_token) {
            $("#testBoxcar2-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testBoxcar2-result").html(loading);
        $.get(sbRoot + "/home/testBoxcar2", {'accessToken': boxcar2_access_token, 'sound': boxcar2_sound})
            .done(function (data) {
                $("#testBoxcar2-result").html(data);
                $("#testBoxcar2").prop("disabled", false);
            });
    });

    $("#testPushover").click(function () {
        var pushover_userkey = $.trim($("#pushover_userkey").val());
        var pushover_priority = $("#pushover_priority").val();
        var pushover_device = $("#pushover_device").val();
        var pushover_sound = $("#pushover_sound").val();
        if (!pushover_userkey) {
            $("#testPushover-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testPushover-result").html(loading);
        $.get(sbRoot + "/home/testPushover", {'userKey': pushover_userkey, 'priority': pushover_priority, 'device': pushover_device, 'sound': pushover_sound})
            .done(function (data) {
                $("#testPushover-result").html(data);
                $("#testPushover").prop("disabled", false);
            });
    });

    function get_pushover_devices (msg) {
        var pushover_userkey = $.trim($("#pushover_userkey").val());
        if (!pushover_userkey) {
            $("#testPushover-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        if (msg) {
            $("#testPushover-result").html(loading);
        }
        var current_pushover_device = $("#pushover_device").val();
        $.get(sbRoot + "/home/getPushoverDevices", {'userKey': pushover_userkey})
            .done(function (data) {
                var devices = jQuery.parseJSON(data || '{}').devices;
                $("#pushover_device_list").html('');
                // add default option to send to all devices
                $("#pushover_device_list").append('<option value="all" selected="selected">-- All Devices --</option>');
                if (devices) {
                    for (var i = 0; i < devices.length; i++) {
                        // if a device in the list matches our current iden, select it
                        if (current_pushover_device == devices[i]) {
                            $("#pushover_device_list").append('<option value="' + devices[i] + '" selected="selected">' + devices[i] + '</option>');
                        } else {
                            $("#pushover_device_list").append('<option value="' + devices[i] + '">' + devices[i] + '</option>');
                        }
                    }
                }
                $("#getPushoverDevices").prop("disabled", false);
                if (msg) {
                    $('#testPushover-result').html(msg);
                }
            });

        $("#pushover_device_list").change(function () {
            $("#pushover_device").val($("#pushover_device_list").val());
            $('#testPushover-result').html("Don't forget to save your new Pushover settings.");
        });
    }

    $("#getPushoverDevices").click(function () {
        get_pushover_devices("Device list updated. Select specific device to use.");
    });

    if ($("#use_pushover").prop('checked')) {
        get_pushover_devices();
    }

    $("#testLibnotify").click(function () {
        $("#testLibnotify-result").html(loading);
        $.get(sbRoot + "/home/testLibnotify",
            function (data) { $("#testLibnotify-result").html(data); });
    });

    $("#twitterStep1").click(function () {
        $("#testTwitter-result").html(loading);
        $.get(sbRoot + "/home/twitterStep1", function (data) {window.open(data); })
            .done(function () { $("#testTwitter-result").html("<b>Step1:</b> Confirm Authorization"); });
    });

    $("#twitterStep2").click(function () {
        var twitter_key = $.trim($("#twitter_key").val());
        if (!twitter_key) {
            $("#testTwitter-result").html("Please fill out the necessary fields above.");
            return;
        }
        $("#testTwitter-result").html(loading);
        $.get(sbRoot + "/home/twitterStep2", {'key': twitter_key},
            function (data) { $("#testTwitter-result").html(data); });
    });

    $("#testTwitter").click(function () {
        $.get(sbRoot + "/home/testTwitter",
            function (data) { $("#testTwitter-result").html(data); });
    });

    $("#settingsNMJ").click(function () {
        var nmj_host = $.trim($("#nmj_host").val());
        if (!nmj_host) {
            alert("Please fill in the Popcorn IP address");
            $("#nmj_host").focus();
            return;
        }
        $("#testNMJ-result").html(loading);
        $.get(sbRoot + "/home/settingsNMJ", {'host': nmj_host},
            function (data) {
                if (data === null) {
                    $("#nmj_database").prop("readonly", false);
                    $("#nmj_mount").prop("readonly", false);
                }
                var JSONData = $.parseJSON(data);
                $("#testNMJ-result").html(JSONData.message);
                $("#nmj_database").val(JSONData.database);
                $("#nmj_mount").val(JSONData.mount);

                if (JSONData.database) {
                    $("#nmj_database").prop("readonly", true);
                } else {
                    $("#nmj_database").prop("readonly", false);
                }
                if (JSONData.mount) {
                    $("#nmj_mount").prop("readonly", true);
                } else {
                    $("#nmj_mount").prop("readonly", false);
                }
            });
    });

    $("#testNMJ").click(function () {
        var nmj_host = $.trim($("#nmj_host").val());
        var nmj_database = $("#nmj_database").val();
        var nmj_mount = $("#nmj_mount").val();
        if (!nmj_host) {
            $("#testNMJ-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testNMJ-result").html(loading);
        $.get(sbRoot + "/home/testNMJ", {'host': nmj_host, 'database': nmj_database, 'mount': nmj_mount})
            .done(function (data) {
                $("#testNMJ-result").html(data);
                $("#testNMJ").prop("disabled", false);
            });
    });

    $("#settingsNMJv2").click(function () {
        var nmjv2_host = $.trim($("#nmjv2_host").val());
        if (!nmjv2_host) {
            alert("Please fill in the Popcorn IP address");
            $("#nmjv2_host").focus();
            return;
        }

        var nmjv2_dbloc;
        var radios = document.getElementsByName("nmjv2_dbloc");
        for (var i = 0; i < radios.length; i++) {
            if (radios[i].checked) {
                nmjv2_dbloc=radios[i].value;
                break;
            }
        }

        var nmjv2_dbinstance = $("#NMJv2db_instance").val();
        $("#testNMJv2-result").html(loading);
        $.get(sbRoot + "/home/settingsNMJv2", {'host': nmjv2_host, 'dbloc': nmjv2_dbloc, 'instance': nmjv2_dbinstance},
        function (data) {
            if (data == null) {
                $("#nmjv2_database").prop("readonly", false);
            }
            var JSONData = $.parseJSON(data || "null");
            $("#testNMJv2-result").html(JSONData.message);
            $("#nmjv2_database").val(JSONData.database);

            if (JSONData.database) {
                $("#nmjv2_database").prop("readonly", true);
            } else {
                $("#nmjv2_database").prop("readonly", false);
            }
        });
    });

    $("#testNMJv2").click(function () {
        var nmjv2_host = $.trim($("#nmjv2_host").val());
        if (!nmjv2_host) {
            $("#testNMJv2-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testNMJv2-result").html(loading);
        $.get(sbRoot + "/home/testNMJv2", {'host': nmjv2_host})
            .done(function (data) {
                $("#testNMJv2-result").html(data);
                $("#testNMJv2").prop("disabled", false);
            });
    });

    $("#testTrakt").click(function () {
        var trakt_api = $.trim($("#trakt_api").val());
        var trakt_username = $.trim($("#trakt_username").val());
        var trakt_password = $.trim($("#trakt_password").val());
        if (!trakt_api || !trakt_username || !trakt_password) {
            $("#testTrakt-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testTrakt-result").html(loading);
        $.get(sbRoot + "/home/testTrakt", {'api': trakt_api, 'username': trakt_username, 'password': trakt_password})
            .done(function (data) {
                $("#testTrakt-result").html(data);
                $("#testTrakt").prop("disabled", false);
            });
    });

    $("#testNMA").click(function () {
        var nma_api = $.trim($("#nma_api").val());
        var nma_priority = $("#nma_priority").val();
        if (!nma_api) {
            $("#testNMA-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testNMA-result").html(loading);
        $.get(sbRoot + "/home/testNMA", {'nma_api': nma_api, 'nma_priority': nma_priority})
            .done(function (data) {
                $("#testNMA-result").html(data);
                $("#testNMA").prop("disabled", false);
            });
    });

    $("#testPushalot").click(function () {
        var pushalot_authorizationtoken = $.trim($("#pushalot_authorizationtoken").val());
        var pushalot_silent = ($("#pushalot_silent").prop('checked') == true) ? 'True' : 'False';
        var pushalot_important = ($("#pushalot_important").prop('checked') == true) ? 'True' : 'False';
        if (!pushalot_authorizationtoken) {
            $("#testPushalot-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testPushalot-result").html(loading);
        $.get(sbRoot + "/home/testPushalot", {'authtoken': pushalot_authorizationtoken, 'silent': pushalot_silent, 'important': pushalot_important})
            .done(function (data) {
                $("#testPushalot-result").html(data);
                $("#testPushalot").prop("disabled", false);
            });
    });

    $("#testSynoNotify").click(function () {
        $(this).prop("disabled", true);
        $("#testSynoNotify-result").html(loading);
        $.get(sbRoot + "/home/testSynoNotify")
            .done(function (data) {
                $("#testSynoNotify-result").html(data);
                $("#testSynoNotify").prop("disabled", false);
            });
    });

    $("#testPushbullet").click(function () {
        var pushbullet_access_token = $.trim($("#pushbullet_access_token").val());
        var pushbullet_device_iden = $("#pushbullet_device_iden").val();
        if (!pushbullet_access_token) {
            $("#testPushbullet-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        $("#testPushbullet-result").html(loading);
        $.get(sbRoot + "/home/testPushbullet", {'accessToken': pushbullet_access_token, 'device_iden': pushbullet_device_iden})
            .done(function (data) {
                $("#testPushbullet-result").html(data);
                $("#testPushbullet").prop("disabled", false);
            });
    });

    function get_pushbullet_devices (msg) {
        var pushbullet_access_token = $.trim($("#pushbullet_access_token").val());
        if (!pushbullet_access_token) {
            $("#testPushbullet-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).prop("disabled", true);
        if (msg) {
            $("#testPushbullet-result").html(loading);
        }
        var current_pushbullet_device = $("#pushbullet_device_iden").val();
        $.get(sbRoot + "/home/getPushbulletDevices", {'accessToken': pushbullet_access_token})
            .done(function (data) {
                var devices = jQuery.parseJSON(data || '{}').devices;
                $("#pushbullet_device_list").html('');
                // add default option to send to all devices
                $("#pushbullet_device_list").append('<option value="" selected="selected">-- All Devices --</option>');
                if (devices) {
                    for (var i = 0; i < devices.length; i++) {
                        // only list active device targets
                        if (devices[i].active == true) {
                            // if a device in the list matches our current iden, select it
                            if (current_pushbullet_device == devices[i].iden) {
                                $("#pushbullet_device_list").append('<option value="' + devices[i].iden + '" selected="selected">' + devices[i].manufacturer + ' ' + devices[i].nickname + '</option>');
                            } else {
                                $("#pushbullet_device_list").append('<option value="' + devices[i].iden + '">' + devices[i].manufacturer + ' ' + devices[i].nickname + '</option>');
                            }
                        }
                    }
                }
                $("#getPushbulletDevices").prop("disabled", false);
                if (msg) {
                    $('#testPushbullet-result').html(msg);
                }
            });

        $("#pushbullet_device_list").change(function () {
            $("#pushbullet_device_iden").val($("#pushbullet_device_list").val());
            $('#testPushbullet-result').html("Don't forget to save your new Pushbullet settings.");
        });
    }

    $("#getPushbulletDevices").click(function () {
        get_pushbullet_devices("Device list updated. Select specific device to use.");
    });

    if ($("#use_pushbullet").prop('checked')) {
        get_pushbullet_devices();
    }

});
