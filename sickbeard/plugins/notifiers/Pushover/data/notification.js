$(document).ready(function(){
    $('#testPushover').click(function(){
        $('#testPushover-result').html(loading);
        var pushover_userkey = $("#pushover_userkey").val();
        $.get(sbRoot+"/home/testPushover", {'userKey': pushover_userkey},
        function (data){ $('#testPushover-result').html(data); });
    });
});
