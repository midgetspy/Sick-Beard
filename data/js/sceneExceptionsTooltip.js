$(function () {
    $('.showTitle a').each(function () {
        match = $(this).parent().attr("id").match(/^scene_exception_(\d+)$/);
        $(this).qtip({
            content: {
                text: 'Loading...',
                ajax: {
                    url: $("#sbRoot").val() + '/home/sceneExceptions',
                    type: 'GET',
                    data: {
                        show: match[1]
                    },
                    success: function (data, status) {
                        this.set('content.text', data);
                    }
                }
            },
            show: {
                solo: true
            },
            position: {
                viewport: $(window),
                my: 'top center',
                at: 'bottom center',
                adjust: {
                    y: 3,
                    x: 0
                }
            },
            style: {
                tip: {
                    corner: true,
                    method: 'polygon'
                },
                classes: 'ui-tooltip-rounded ui-tooltip-shadow ui-tooltip-sb'
            }
        });
    });
});
