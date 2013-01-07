$(document).ready(function() {
    function setFromPresets (preset) {
        if (preset == 0) {
            $('#customQuality').show();
            return;
        } else {
            $('#customQuality').hide();
        }

        $('#anyQualities option').each(function(i) {
            var result = preset & $(this).val();
            if (result > 0) {
                $(this).attr('selected', 'selected');
            } else {
                $(this).attr('selected', false);
            }
        });

        $('#bestQualities option').each(function(i) {
            var result = preset & ($(this).val() << 16);
            if (result > 0) {
                $(this).attr('selected', 'selected');
            } else {
                $(this).attr('selected', false);
            }
        });

        return;
    }

    $('#qualityPreset').change(function() {
        setFromPresets($('#qualityPreset :selected').val());
    });

    setFromPresets($('#qualityPreset :selected').val());
});
