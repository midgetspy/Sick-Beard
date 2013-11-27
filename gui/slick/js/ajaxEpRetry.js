(function () {

    $.ajaxEpRetry = {
        defaults: {
            size:               16,
            colorRow:           false,
            loadingImage:       'loading16_dddddd.gif',
            noImage:            'no16.png',
            yesImage:           'yes16.png'
        }
    };

    $.fn.ajaxEpRetry = function (options) {
        options = $.extend({}, $.ajaxEpRetry.defaults, options);

        $('.epRetry').click(function () {
            if ( !confirm("Mark download as bad and retry?") )
                return false;

            var parent = $(this).parent();

            // put the ajax spinner (for non white bg) placeholder while we wait
            parent.empty();
            parent.append($("<img/>").attr({"src": sbRoot + "/images/" + options.loadingImage, "height": options.size, "alt": "", "title": "loading"}));

            $.getJSON($(this).attr('href'), function (data) {
                // if they failed then just put the red X
                if (data.result == 'failure') {
                    img_name = options.noImage;
                    img_result = 'failed';

                // if the snatch was successful then apply the corresponding class and fill in the row appropriately
                } else {
                    img_name = options.yesImage;
                    img_result = 'success';
                    // color the row
                    if (options.colorRow) {
                        parent.parent().removeClass('skipped wanted qual good unaired snatched').addClass('snatched');
                    }
                }

                // put the corresponding image as the result for the the row
                parent.empty();
                parent.append($("<img/>").attr({"src": sbRoot + "/images/" + img_name, "height": options.size, "alt": img_result, "title": img_result}));
            });

            // don't follow the link
            return false;
        });
    };
})();
