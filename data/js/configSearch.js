$(document).ready(function(){

    $.fn.nzb_method_handler = function() {
        
        var selectedProvider = $('#nzb_method :selected').val();

        if (selectedProvider == "blackhole") {
            $('#blackhole_settings').show();
            $('#sabnzbd_settings').hide();
        } else {
            $('#blackhole_settings').hide();
            $('#sabnzbd_settings').show();
        }

    }

    $('#nzb_method').change($(this).nzb_method_handler);

    $(this).nzb_method_handler();

});
