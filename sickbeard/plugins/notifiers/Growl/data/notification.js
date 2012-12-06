$(document).ready(function(){
    $('#testGrowl').click(function(){
        $('#testGrowl-result').html(loading);
        var growl_host = $("#growl_host").val();
        var growl_password = $("#growl_password").val();
        var growl_result = $.get(sbRoot+"/home/testGrowl", {'host': growl_host, 'password': growl_password}, 
        function (data){ $('#testGrowl-result').html(data); });
    });
});
