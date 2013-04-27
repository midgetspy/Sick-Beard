$(document).ready(function () {

    $("table td.tvShow").live('click', function (e) {
        // Check the primary click button is pressed, different in IE
        var is_correct_button = (!$.browser.msie && e.button == 0) || ($.browser.msie && e.button == 1);

        // Handle ctrl/cmd/shift click as open in new-window (or tab)
        var is_modified_pressed = (e.ctrlKey || e.metaKey || e.shiftKey);

        // If clicked on <a>, let the browser handle things
        var is_link = (e.srcElement instanceof HTMLAnchorElement);

        if (is_correct_button && !is_link) {
            var href = $(this).find("a").attr("href");
            if (!href) { return; } // No link found
            if (is_modified_pressed) {
                // New window or tab
                window.open(href, "_blank");
            } else {
                window.location = href;
            }
        }
    });

});
