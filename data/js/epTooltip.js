$(function(){

    $('img[rel]').each(function() {
        $(this).qtip( {
            content: {
                text: function(api) {
                    return $( 'div.details_'+$(this).attr('rel') ).html();
                },
                title: {
                    text: function(api) {
                        return $( 'div.title_'+$(this).attr('rel') ).html();
                    },
                    button: true
                }
            },
            position: {
                at: 'center',
                my: 'center',
                viewport: $(window),
                adjust: { screen: true }
            },
            show: { event: 'click mouseenter', solo: true },
            hide: 'click unfocus',
            style: { classes: 'ui-tooltip-rounded ui-tooltip-shadow ui-tooltip-sb' }
        })

        .click(function() { return false; });
    });

});
