$(document).ready(function(){
    $('#settingsNMJ').click(function(){
        if (!$('#nmj_host').val()) {
            alert('Please fill in the Popcorn IP address');
            $('#nmj_host').focus();
            return;
        }
        $('#testNMJ-result').html(loading);
        var nmj_host = $('#nmj_host').val();
        
        $.get(sbRoot+"/home/settingsNMJ", {'host': nmj_host}, 
        function (data){
            if (data == null) {
                $('#nmj_database').removeAttr('readonly');
                $('#nmj_mount').removeAttr('readonly');
            }
            var JSONData = $.parseJSON(data);
            $('#testNMJ-result').html(JSONData.message);
            $('#nmj_database').val(JSONData.database);
            $('#nmj_mount').val(JSONData.mount);
            
            if (JSONData.database)
                $('#nmj_database').attr('readonly', true);
            else
                $('#nmj_database').removeAttr('readonly');
            
            if (JSONData.mount)
                $('#nmj_mount').attr('readonly', true);
            else
                $('#nmj_mount').removeAttr('readonly');
        });
    });

    $('#testNMJ').click(function(){
        $('#testNMJ-result').html(loading);
        var nmj_host = $("#nmj_host").val();
        var nmj_database = $("#nmj_database").val();
        var nmj_mount = $("#nmj_mount").val();
        
        $.get(sbRoot+"/home/testNMJ", {'host': nmj_host, 'database': nmj_database, 'mount': nmj_mount}, 
        function (data){ $('#testNMJ-result').html(data); });
    });
});
