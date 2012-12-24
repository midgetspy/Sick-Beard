$(document).ready(function(){
    $('#testBoxcar').click(function(){
        $('#testBoxcar-result').html(loading);
        var boxcar_username = $("#boxcar_username").val();
        $.get(sbRoot+"/home/testBoxcar", {'username': boxcar_username},
        function (data){ $('#testBoxcar-result').html(data); });
    });
});
