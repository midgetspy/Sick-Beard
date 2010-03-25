$(function(){
        $('body').append('<div id="tooltip" />');
        $('.plotInfo').tooltip(
        {
                position:     'bottom right',
                delay:        100,
                effect:       'fade',
                tip:          '#tooltip',
                onBeforeShow: function(e) {
                        match = this.getTrigger().attr("id").match(/^plot_info_(\d+)_(\d+)_(\d+)$/);
                        $('#tooltip').html($.ajax({
                                async:   false,
                                data:    { show: match[1], episode: match[3], season: match[2] },
                                url:     $("#sbRoot").val()+'/home/plotDetails'
                        }).responseText);
                }
        })
})
