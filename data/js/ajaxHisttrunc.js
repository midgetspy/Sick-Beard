(function(){
	$.fn.ajaxHisttrunc = function(){
       
        $('.histTrunc').click(function () {
            var hist = $(this).parent();

            // put the ajax spinner (for non white bg) placeholder while we wait
            hist.empty();
            hist.append($("<img/>").attr({"src": sbRoot+"/images/loading16_dddddd.gif", "alt": "", "title": "loading"}));

            $.getJSON($(this).attr('href'), function (data) {
                // if they failed then just put the red X
                if (data.result == 'failure') {
                    img_name = 'no16.png';
                    img_result = 'failed';

                // if the snatch was successful then apply the corresponding class and fill in the row appropriately
                } else {
                    img_name = 'yes16.png';
                    img_result = 'success';
                    
                }

                // put the corresponding image as the result for the the row
                hist.empty();
                hist.append($("<img/>").attr({"src": sbRoot + "/images/" + img_name, "height": 16, "alt": img_result, "title": img_result}));
            });

            // fon't follow the link
            return false;
        });
    };
})();
