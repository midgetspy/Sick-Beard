$(document).ready(function() {

  $('#submitMassEdit').click(function() {
    var editArr = new Array();

    $('.editCheck').each(function() {
      if (this.checked == true) {
        editArr.push($(this).attr('id').split('-')[1]);
      }
    });

    if (editArr.length == 0) {
        return;
    }

    url = 'massEdit?toEdit=' + editArr.join('|');
    window.location.href = url;
  });


  $('#submitMassUpdate').click(function() {

    var updateArr = new Array();
    var refreshArr = new Array();
    var renameArr = new Array();
    var deleteArr = new Array();
    var metadataArr = new Array();

    $('.updateCheck').each(function() {
      if (this.checked == true) {
        updateArr.push($(this).attr('id').split('-')[1]);
      }
    });

    $('.refreshCheck').each(function() {
      if (this.checked == true) {
        refreshArr.push($(this).attr('id').split('-')[1]);
      }
    });

    $('.renameCheck').each(function() {
      if (this.checked == true) {
        renameArr.push($(this).attr('id').split('-')[1]);
      }
    });

    $('.deleteCheck').each(function() {
      if (this.checked == true) {
        deleteArr.push($(this).attr('id').split('-')[1]);
      }
    });

/*
    $('.metadataCheck').each(function() {
      if (this.checked == true) {
        metadataArr.push($(this).attr('id').split('-')[1]);
      }
    });
*/
    if (updateArr.length + refreshArr.length + renameArr.length + deleteArr.length + metadataArr.length == 0) {
      return false;
    }

    url = 'massUpdate?toUpdate=' + updateArr.join('|') + '&toRefresh=' + refreshArr.join('|') + '&toRename=' + renameArr.join('|') + '&toDelete=' + deleteArr.join('|') + '&toMetadata=' + metadataArr.join('|');

    window.location.href = url;

  });

  $('.bulkCheck').click(function() {

    var bulkCheck = this;
    var whichBulkCheck = $(bulkCheck).attr('id');

    $('.'+whichBulkCheck).each(function() {
        if (!this.disabled) {
            this.checked = !this.checked;
        }
    });
  });

  ['.editCheck', '.updateCheck', '.refreshCheck', '.renameCheck', '.deleteCheck'].forEach(function(name) {
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
            if (!this.disabled) {
              this.checked = lastCheck.checked;
            }
        }

        if (this == check || this == lastCheck) {
          found++;
        }
      });

      lastClick = this;
    });

  });

});
