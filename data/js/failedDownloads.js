$(document).ready(function(){
  $('#submitMassRemove').click(function(){

    var removeArr = new Array()

    $('.removeCheck').each(function() {
      if (this.checked == true) {
        removeArr.push($(this).attr('id').split('-')[1])
      }
    });

    if (removeArr.length == 0)
      return false

    url = sbRoot + '/manage/failedDownloads?toRemove='+removeArr.join('|')

    window.location.href = url

  });

  $('.bulkCheck').click(function(){

    var bulkCheck = this;
    var whichBulkCheck = $(bulkCheck).attr('id');

    $('.'+whichBulkCheck).each(function(){
        if (!this.disabled)
            this.checked = !this.checked
    });
  });

  ['.removeCheck'].forEach(function(name) {
    var lastCheck = null;

    $(name).click(function(event) {

      if(!lastCheck || !event.shiftKey) {
        lastCheck = this;
        return;
      }

      var check = this;
      var found = 0;

      $(name).each(function() {
        switch (found) {
          case 2: return false;
          case 1:
            if (!this.disabled)
              this.checked = lastCheck.checked;
        }

        if (this == check || this == lastCheck)
          found++;
      });

      lastClick = this;
    });

  });

  $('#addFailedRelease').click(function(){
    releasename = $('#failedRelease').val()
    if (releasename) {
      url = sbRoot + '/manage/failedDownloads?add='+releasename
      window.location.href = url
    } else {
      return false
    }

  })

});
