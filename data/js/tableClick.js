$(document).ready(function(){

    $("table.sickbeardTable td.tvShow").live('click', function(e) {
        if( (!$.browser.msie && e.button == 0) || ($.browser.msie && e.button == 1) ) {
            if(!e.shiftKey) {
                var href = $(this).find("a").attr("href");
                if(href) { window.location = href; }
            }
        }
    });

});
