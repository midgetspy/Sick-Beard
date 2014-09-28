$(document).ready(function () {
    // restore all buttons on page load just in case
    $("input").prop("disabled", false);

    $(".enabler").each(function () {
        if (!$(this).prop('checked')) {
            $('#content_' + $(this).attr('id')).hide();
        }
    });

    $(".enabler").click(function () {
        if ($(this).prop('checked')) {
            $('#content_' + $(this).attr('id')).fadeIn("fast", "linear");
        } else {
            $('#content_' + $(this).attr('id')).fadeOut("fast", "linear");
        }
    });

    // bind 'myForm' and provide a simple callback function 
    $('#configForm').ajaxForm({
        beforeSubmit: function () {
            $('.config_submitter').each(function () {
                $(this).prop("disabled", true);
                $(this).after('<span><img src="' + sbRoot + '/images/loading16.gif"> Saving...</span>');
                $(this).hide();
            });
        },
        success: function () {
            setTimeout('config_success()', 2000);
        }
    });

    $('#api_key').click(function () { $('#api_key').select(); });
    $("#generate_new_apikey").click(function () {
        $.get(sbRoot + '/config/general/generateKey/',
            function (data) {
                if (data.error != undefined) {
                    alert(data.error);
                    return;
                }
                $('#api_key').val(data).select();
            });
    });

});

function config_success() {
    $('.config_submitter').each(function () {
        $(this).prop("disabled", false);
        $(this).next().remove();
        $(this).show();
    });
}
