$(document).ready(function(){
    $('#testProwl').click(function(){
        $('#testProwl-result').html(loading);
        var prowl_api = $("#prowl_api").val();
        var prowl_priority = $("#prowl_priority").val();
        var prowl_result = $.get(sbRoot+"/home/testProwl", {'prowl_api': prowl_api, 'prowl_priority': prowl_priority}, 
        function (data){ $('#testProwl-result').html(data); });
    });
});
