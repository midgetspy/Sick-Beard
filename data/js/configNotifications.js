$(document).ready(function () {
    var loading = '<img src="' + sbRoot + '/images/loading16.gif" height="16" width="16" />';

    $("#testGrowl").click(function () {
        var growl_host = $.trim($("#growl_host").val());
        var growl_password = $.trim($("#growl_password").val());
        if (!growl_host) {
            $("#testGrowl-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).attr("disabled", true);
        $("#testGrowl-result").html(loading);
        $.get(sbRoot + "/home/testGrowl", {'host': growl_host, 'password': growl_password})
            .done(function (data) {
                $("#testGrowl-result").html(data);
                $("#testGrowl").attr("disabled", false);
            });
    });

    $("#testProwl").click(function () {
        var prowl_api = $.trim($("#prowl_api").val());
        var prowl_priority = $("#prowl_priority").val();
        if (!prowl_api) {
            $("#testProwl-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).attr("disabled", true);
        $("#testProwl-result").html(loading);
        $.get(sbRoot + "/home/testProwl", {'prowl_api': prowl_api, 'prowl_priority': prowl_priority})
            .done(function (data) {
                $("#testProwl-result").html(data);
                $("#testProwl").attr("disabled", false);
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
        $(this).attr("disabled", true);
        $("#testXBMC-result").html(loading);
        $.get(sbRoot + "/home/testXBMC", {'host': xbmc_host, 'username': xbmc_username, 'password': xbmc_password})
            .done(function (data) {
                $("#testXBMC-result").html(data);
                $("#testXBMC").attr("disabled", false);
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
        $(this).attr("disabled", true);
        $("#testPLEX-result").html(loading);
        $.get(sbRoot + "/home/testPLEX", {'host': plex_host, 'username': plex_username, 'password': plex_password})
            .done(function (data) {
                $("#testPLEX-result").html(data);
                $("#testPLEX").attr("disabled", false);
            });
    });

    $("#testBoxcar").click(function () {
        var boxcar_username = $.trim($("#boxcar_username").val());
        if (!boxcar_username) {
            $("#testBoxcar-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).attr("disabled", true);
        $("#testBoxcar-result").html(loading);
        $.get(sbRoot + "/home/testBoxcar", {'username': boxcar_username})
            .done(function (data) {
                $("#testBoxcar-result").html(data);
                $("#testBoxcar").attr("disabled", false);
            });
    });
    
    $('#testBoxcar2').click(function () {
        $('#testBoxcar2-result').html(loading);
        var boxcar2_access_token = $("#boxcar2_access_token").val();
        $.get(sbRoot + "/home/testBoxcar2", {'accessToken': boxcar2_access_token},
            function (data) { $('#testBoxcar2-result').html(data); });
    });

    $("#testPushover").click(function () {
        var pushover_userkey = $.trim($("#pushover_userkey").val());
        if (!pushover_userkey) {
            $("#testPushover-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).attr("disabled", true);
        $("#testPushover-result").html(loading);
        $.get(sbRoot + "/home/testPushover", {'userKey': pushover_userkey})
            .done(function (data) {
                $("#testPushover-result").html(data);
                $("#testPushover").attr("disabled", false);
            });
    });

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
                    $("#nmj_database").removeAttr("readonly");
                    $("#nmj_mount").removeAttr("readonly");
                }
                var JSONData = $.parseJSON(data);
                $("#testNMJ-result").html(JSONData.message);
                $("#nmj_database").val(JSONData.database);
                $("#nmj_mount").val(JSONData.mount);

                if (JSONData.database) {
                    $("#nmj_database").attr("readonly", true);
                } else {
                    $("#nmj_database").removeAttr("readonly");
                }
                if (JSONData.mount) {
                    $("#nmj_mount").attr("readonly", true);
                } else {
                    $("#nmj_mount").removeAttr("readonly");
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
        $(this).attr("disabled", true);
        $("#testNMJ-result").html(loading);
        $.get(sbRoot + "/home/testNMJ", {'host': nmj_host, 'database': nmj_database, 'mount': nmj_mount})
            .done(function (data) {
                $("#testNMJ-result").html(data);
                $("#testNMJ").attr("disabled", false);
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
                $("#nmjv2_database").removeAttr("readonly");
            }
            var JSONData = $.parseJSON(data || "null");
            $("#testNMJv2-result").html(JSONData.message);
            $("#nmjv2_database").val(JSONData.database);

            if (JSONData.database) {
                $("#nmjv2_database").attr("readonly", true);
            } else {
                $("#nmjv2_database").removeAttr("readonly");
            }
        });
    });

    $("#testNMJv2").click(function () {
        var nmjv2_host = $.trim($("#nmjv2_host").val());
        if (!nmjv2_host) {
            $("#testNMJv2-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).attr("disabled", true);
        $("#testNMJv2-result").html(loading);
        $.get(sbRoot + "/home/testNMJv2", {'host': nmjv2_host})
            .done(function (data) {
                $("#testNMJv2-result").html(data);
                $("#testNMJv2").attr("disabled", false);
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
        $(this).attr("disabled", true);
        $("#testTrakt-result").html(loading);
        $.get(sbRoot + "/home/testTrakt", {'api': trakt_api, 'username': trakt_username, 'password': trakt_password})
            .done(function (data) {
                $("#testTrakt-result").html(data);
                $("#testTrakt").attr("disabled", false);
            });
    });

    $("#testNMA").click(function () {
        var nma_api = $.trim($("#nma_api").val());
        var nma_priority = $("#nma_priority").val();
        if (!nma_api) {
            $("#testNMA-result").html("Please fill out the necessary fields above.");
            return;
        }
        $(this).attr("disabled", true);
        $("#testNMA-result").html(loading);
        $.get(sbRoot + "/home/testNMA", {'nma_api': nma_api, 'nma_priority': nma_priority})
            .done(function (data) {
                $("#testNMA-result").html(data);
                $("#testNMA").attr("disabled", false);
            });
    });

    $("#testSynoNotify").click(function () {
        $(this).attr("disabled", true);
        $("#testSynoNotify-result").html(loading);
        $.get(sbRoot + "/home/testSynoNotify")
            .done(function (data) {
                $("#testSynoNotify-result").html(data);
                $("#testSynoNotify").attr("disabled", false);
            });
    });

});
