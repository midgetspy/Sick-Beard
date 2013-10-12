$(document).ready(function(){

    $.fn.showHideProviders = function() {
        $('.providerDiv').each(function(){
            var providerName = $(this).attr('id');
            var selectedProvider = $('#editAProvider :selected').val();

            if (selectedProvider+'Div' == providerName)
                $(this).show();
            else
                $(this).hide();

        });
    }

    $.fn.addProvider = function (id, name, url, key, isDefault) {

        url = $.trim(url);
        if (!url)
            return;

        if (!/^https?:\/\//i.test(url))
            url = "http://" + url;

        if (url.match('/$') == null)
            url = url + '/';

        var newData = [isDefault, [name, url, key]];
        newznabProviders[id] = newData;

        if (!isDefault) {
            $('#editANewznabProvider').addOption(id, name);
            $(this).populateNewznabSection();
        }

        if ($('#providerOrderList > #'+id).length == 0) {
            var toAdd = '<li class="ui-state-default" id="'+id+'"> <input type="checkbox" id="enable_'+id+'" class="provider_enabler" CHECKED> <a href="'+url+'" class="imgLink" target="_new"><img src="'+sbRoot+'/images/providers/newznab.png" alt="'+name+'" width="16" height="16"></a> '+name+'</li>';

            $('#providerOrderList').append(toAdd);
            $('#providerOrderList').sortable("refresh");
        }

        $(this).makeNewznabProviderString();

    }

    $.fn.updateProvider = function (id, url, key) {

        newznabProviders[id][1][1] = url;
        newznabProviders[id][1][2] = key;

        $(this).populateNewznabSection();

        $(this).makeNewznabProviderString();

    }

    $.fn.deleteProvider = function (id) {

        $('#editANewznabProvider').removeOption(id);
        delete newznabProviders[id];
        $(this).populateNewznabSection();

        $('#providerOrderList > #'+id).remove();

        $(this).makeNewznabProviderString();

    }

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
            $('#newznab_name').removeAttr("disabled");
            $('#newznab_url').removeAttr("disabled");
        } else {

            $('#newznab_name').attr("disabled", "disabled");

            if (isDefault) {
                $('#newznab_url').attr("disabled", "disabled");
                $('#newznab_delete').attr("disabled", "disabled");
            } else {
                $('#newznab_url').removeAttr("disabled");
                $('#newznab_delete').removeAttr("disabled");
            }
        }

    }

    $.fn.makeNewznabProviderString = function() {

        var provStrings = new Array();

        for (var id in newznabProviders) {
            provStrings.push(newznabProviders[id][1].join('|'));
        }

        $('#newznab_string').val(provStrings.join('!!!'));

    }

    $.fn.refreshProviderList = function() {
            var idArr = $("#providerOrderList").sortable('toArray');
            var finalArr = new Array();
            $.each(idArr, function(key, val) {
                    var checked = + $('#enable_'+val).prop('checked') ? '1' : '0';
                    finalArr.push(val + ':' + checked);
            });

            $("#provider_order").val(finalArr.join(' '));
    }

    var newznabProviders = new Array();

    $('.newznab_key').change(function(){

        var provider_id = $(this).attr('id');
        provider_id = provider_id.substring(0, provider_id.length-'_hash'.length);

        var url = $('#'+provider_id+'_url').val();
        var key = $(this).val();

        $(this).updateProvider(provider_id, url, key);

    });

    $('#newznab_key,#newznab_url').change(function(){

        var selectedProvider = $('#editANewznabProvider :selected').val();

        if (selectedProvider == "addNewznab")
            return;

        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();

        $(this).updateProvider(selectedProvider, url, key);

    });

    $('#editAProvider').change(function(){
        $(this).showHideProviders();
    });

    $('#editANewznabProvider').change(function(){
        $(this).populateNewznabSection();
    });

    $('.provider_enabler').live('click', function(){
        $(this).refreshProviderList();
    });


    $('#newznab_add').click(function(){

        var selectedProvider = $('#editANewznabProvider :selected').val();

        var name = $('#newznab_name').val();
        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();

        var params = { name: name };

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

    $('.newznab_delete').click(function(){

        var selectedProvider = $('#editANewznabProvider :selected').val();

        $(this).deleteProvider(selectedProvider);

    });

    // torrent rss

    var torrentRSSProviders = new Array();

    $.fn.addTorrentRSSProvider = function (id, name, url, isDefault) {
        url = $.trim(url);
        if (!url)
            return;

        if (!/^https?:\/\//i.test(url))
            url = "http://" + url;

        var newData = [isDefault, [name, url]];
        torrentRSSProviders[id] = newData;

        if (!isDefault) {
            $('#editTorrentRSSProvider').addOption(id, name);
            $(this).populateTorrentRSSSection();
        }

        if ($('#providerOrderList > #'+id).length == 0) {
            var toAdd = '<li class="ui-state-default" id="'+id+'"> <input type="checkbox" id="enable_'+id+'" class="provider_enabler" CHECKED> <a href="'+url+'" class="imgLink" target="_new"><img src="'+sbRoot+'/images/providers/torrentrss.png" alt="'+name+'" width="16" height="16"></a> '+name+'</li>';

            $('#providerOrderList').append(toAdd);
            $('#providerOrderList').sortable("refresh");
        }

        $(this).makeTorrentRSSProviderString();
    }

    $.fn.updateTorrentRSSProvider = function (id, url) {
        torrentRSSProviders[id][1][1] = url;
        $(this).populateTorrentRSSSection();
        $(this).makeTorrentRSSProviderString();
    }

    $.fn.deleteTorrentRSSProvider = function (id) {
        $('#editTorrentRSSProvider').removeOption(id);
        delete torrentRSSProviders[id];
        $(this).populateTorrentRSSSection();

        $('#providerOrderList > #'+id).remove();

        $(this).makeTorrentRSSProviderString();
    }

    $.fn.populateTorrentRSSSection = function() {
        var selectedProvider = $('#editTorrentRSSProvider :selected').val();

        if (selectedProvider == 'addTorrentRSS') {
            var data = ['','',''];
            var isDefault = 0;
            $('#torrentrss_add_div').show();
            $('#torrentrss_update_div').hide();
        } else {
            var data = torrentRSSProviders[selectedProvider][1];
            var isDefault = torrentRSSProviders[selectedProvider][0];
            $('#torrentrss_add_div').hide();
            $('#torrentrss_update_div').show();
        }

        $('#torrentrss_name').val(data[0]);
        $('#torrentrss_url').val(data[1]);

        if (selectedProvider == 'addTorrentRSS') {
            $('#torrentrss_name').removeAttr("disabled");
            $('#torrentrss_url').removeAttr("disabled");
        } else {
            $('#torrentrss_name').attr("disabled", "disabled");

            if (isDefault) {
                $('#torrentrss_url').attr("disabled", "disabled");
                $('#torrentrss_delete').attr("disabled", "disabled");
            } else {
                $('#torrentrss_url').removeAttr("disabled");
                $('#torrentrss_delete').removeAttr("disabled");
            }
        }
    }

    $.fn.makeTorrentRSSProviderString = function() {
        var provStrings = new Array();

        for (var id in torrentRSSProviders) {
            provStrings.push(torrentRSSProviders[id][1].join('|'));
        }

        $('#torrentrss_string').val(provStrings.join('!!!'));
    }

    $('#torrentrss_url').change(function(){
        var selectedProvider = $('#editTorrentRSSProvider :selected').val();

        if (selectedProvider == "addTorrentRSS")
            return;

        var url = $('#torrentrss_url').val();

        $(this).updateTorrentRSSProvider(selectedProvider, url);
    });

    $('#editTorrentRSSProvider').change(function(){
        $(this).populateTorrentRSSSection();
    });

    $('#torrentrss_add').click(function(){
        var selectedProvider = $('#editTorrentRSSProvider :selected').val();

        var name = $('#torrentrss_name').val();
        var url = $('#torrentrss_url').val();

        var params = { name: name };

        // send to the form with ajax, get a return value
        $.getJSON(sbRoot + '/config/providers/canAddTorrentRSSProvider', params,
            function(data){
                if (data.error != undefined) {
                    alert(data.error);
                    return;
                }

                $(this).addTorrentRSSProvider(data.success, name, url, 0);
        });


    });

    $('.torrentrss_delete').click(function(){
        var selectedProvider = $('#editTorrentRSSProvider :selected').val();
        $(this).deleteTorrentRSSProvider(selectedProvider);
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