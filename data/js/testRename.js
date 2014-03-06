$(document).ready(function() {
    $('.seasonCheck').click(function() {
        var seasCheck = this;
        var seasNo = $(seasCheck).attr('id');

        $('.epCheck:visible').each(function() {
            var epParts = $(this).attr('id').split('x');

            if (epParts[0] == seasNo) {
                this.checked = seasCheck.checked;
            }
        });
    });

    $('input[type=submit]').click(function() {
        var epArr = new Array();

        $('.epCheck').each(function() {
            if (this.checked == true) {
                epArr.push($(this).attr('id'));
            }
        });

        if (epArr.length == 0) {
            return false;
        }

        var url = sbRoot + '/home/doRename?show=' + $('#showID').attr('value') + '&eps=' + epArr.join('|');
        window.location.href = url;
    });

});
