$(function(){
        $('body').append('<div id="tooltip" />');
        $('.showTitle a').tooltip(
        {
                position:     'bottom right',
                offset:       [5, 0],
                delay:        100,
                effect:       'fade',
                tip:          '#tooltip',
                onBeforeShow: function(e) {
                        match = this.getTrigger().parent().attr("id").match(/^scene_exception_(\d+)$/);
                        $('#tooltip').html($.ajax({
                                async:   false,
                                data:    { show: match[1] },
                                url:     $("#sbRoot").val()+'/home/sceneExceptions'
                        }).responseText);
                }
        })
})
