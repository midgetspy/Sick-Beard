$(document).ready(function(){

    $.fn.showHideProviders = function() {
        $('.providerDiv').each(function(){
            var providerName = $(this).attr('id');
            var selectedProvider = $('#editAProvider :selected').val();

            if (selectedProvider + 'Div' == providerName) {
                $(this).show();
            } else {
                $(this).hide();
            }

        });
    };

    // create a new newznab provider from the given data and add it to our newznab string
    $.fn.addProvider = function (id, name, url, key, isDefault) {

        url = $.trim(url);
        if (!url) {
            return;
        }

        if (!/^https?:\/\//i.test(url)) {
            url = "http://" + url;
        }

        if (url.match('/$') == null) {
            url = url + '/';
        }

        // add the data to the provider dict
        var newData = [isDefault, [name, url, key]];
        newznabProviders[id] = newData;

        // default providers will get edited in the built-in section
        if (!isDefault) {
            $('#editANewznabProvider').addOption(id, name);
            $(this).populateNewznabSection();
        }

        // add the provider to the provider list so it can be enabled/sorted
        if ($('#providerOrderList > #' + id).length == 0) {
            var toAdd = '<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="provider_enabler" CHECKED> <a href="' + url + '" class="imgLink" target="_new"><img src="' + sbRoot + '/images/providers/newznab.png" alt="' + name + '" width="16" height="16"></a> ' + name + '<span class="ui-icon ui-icon-arrowthick-2-n-s pull-right"></span></li>';

            $('#providerOrderList').append(toAdd);
            $('#providerOrderList').sortable("refresh");
        }

        // build up the hidden form element that contains the config string
        $(this).makeNewznabProviderString();

    };

    // updates the newznab provider dict with the new config info for a provider
    $.fn.updateProvider = function (id, url, key) {

        newznabProviders[id][1][1] = url;
        newznabProviders[id][1][2] = key;

        $(this).populateNewznabSection();

        $(this).makeNewznabProviderString();

    };

    // removes a provider from the lists
    $.fn.deleteProvider = function (id) {

        $('#editANewznabProvider').removeOption(id);
        delete newznabProviders[id];
        $(this).populateNewznabSection();

        $('#providerOrderList > #' + id).remove();

        $(this).makeNewznabProviderString();

    };

    // populates the custom newznab section with the relevant info for whatever is selected in the dropbox
    $.fn.populateNewznabSection = function() {

        var selectedProvider = $('#editANewznabProvider :selected').val();

        if (selectedProvider == 'addNewznab') {
            var data = ['','',''];
            var isDefault = 0;
            $('#newznab_add_div').show();
            $('#newznab_update_div').hide();
        } else {
            var data = newznabProviders[selectedProvider][1];
            var isDefault = newznabProviders[selectedProvider][0];
            $('#newznab_add_div').hide();
            $('#newznab_update_div').show();
        }

        $('#newznab_name').val(data[0]);
        $('#newznab_url').val(data[1]);
        $('#newznab_key').val(data[2]);

        if (selectedProvider == 'addNewznab') {
            $('#newznab_name').prop("disabled", false);
            $('#newznab_url').prop("disabled", false);
        } else {

            $('#newznab_name').prop("disabled", true);

            if (isDefault) {
                $('#newznab_url').prop("disabled", true);
                $('#newznab_delete').prop("disabled", true);
            } else {
                $('#newznab_url').prop("disabled", false);
                $('#newznab_delete').prop("disabled", false);
            }
        }

    };

    // build up the config string that goes in the hidden form field 
    $.fn.makeNewznabProviderString = function() {

        var provStrings = new Array();

        for (var id in newznabProviders) {
            provStrings.push(newznabProviders[id][1].join('|'));
        }

        $('#newznab_string').val(provStrings.join('!!!'));

    };

    $.fn.refreshProviderList = function() {
            var idArr = $("#providerOrderList").sortable('toArray');
            var finalArr = new Array();
            $.each(idArr, function(key, val) {
                    var checked = + $('#enable_' + val).prop('checked') ? '1' : '0';
                    finalArr.push(val + ':' + checked);
            });

            $("#provider_order").val(finalArr.join(' '));
    };

    var newznabProviders = new Array();

    $('.newznab_key').change(function(){

        var provider_id = $(this).attr('id');
        provider_id = provider_id.substring(0, provider_id.length-'_hash'.length);

        var url = $('#' + provider_id + '_url').val();
        var key = $(this).val();

        $(this).updateProvider(provider_id, url, key);

    });

    $('#newznab_key,#newznab_url').change(function(){

        var selectedProvider = $('#editANewznabProvider :selected').val();

        if (selectedProvider == "addNewznab") {
            return;
        }

        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();

        $(this).updateProvider(selectedProvider, url, key);

    });

    $('#editAProvider').change(function() {
        $(this).showHideProviders();
    });

    $('#editANewznabProvider').change(function() {
        $(this).populateNewznabSection();
    });

    $('#providerOrderList').on('click', '.provider_enabler', function() {
        $(this).refreshProviderList();
    });

    // checks with the server that we can add a new provider and then does the required actions
    $('#newznab_add').click(function(){

        var selectedProvider = $('#editANewznabProvider :selected').val();

        var name = $.trim($('#newznab_name').val());
        var url = $.trim($('#newznab_url').val());
        var key = $.trim($('#newznab_key').val());

        if (!name || !url || !key) {
            return;
        }

        var params = {name: name};

        // send to the form with ajax, get a return value
        $.getJSON(sbRoot + '/config/providers/canAddNewznabProvider', params,
            function(data){
                if (data.error != undefined) {
                    alert(data.error);
                    return;
                }

                $(this).addProvider(data.success, name, url, key, 0);
        });


    });

    // deletes a provider from our local backend
    $('.newznab_delete').click(function(){

        var selectedProvider = $('#editANewznabProvider :selected').val();

        $(this).deleteProvider(selectedProvider);

    });


    // initialization stuff
    $(this).showHideProviders();

    $("#providerOrderList").sortable({
        placeholder: 'ui-state-highlight',
        update: function (event, ui) {
            $(this).refreshProviderList();
        }
    });

    $("#providerOrderList").disableSelection();

});
