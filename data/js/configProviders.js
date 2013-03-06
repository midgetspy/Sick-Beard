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

    $.fn.addProvider = function (id, name, url, key, isDefault, showProvider) {

        if (url.match('/$') == null)
            url = url + '/'

        var newData = [isDefault, [name, url, key]];
        newznabProviders[id] = newData;

        if (!isDefault)
        {
            $('#editANewznabProvider').addOption(id, name);
            $(this).populateNewznabSection();
        }

        if ($('#providerOrderList > #'+id).length == 0 && showProvider != false) {
            var toAdd = '<li class="ui-state-default" id="'+id+'"> <input type="checkbox" id="enable_'+id+'" class="provider_enabler" CHECKED> <a href="'+url+'" class="imgLink" target="_new"><img src="'+sbRoot+'/images/providers/newznab.png" alt="'+name+'" width="16" height="16"></a> '+name+'</li>'

            $('#providerOrderList').append(toAdd);
            $('#providerOrderList').sortable("refresh");
        }

        $(this).makeNewznabProviderString();

    }

    $.fn.addTorrentProvider = function (id, name, url, isDefault, showProvider) {

        var newData = [isDefault, [name, url]];
        torrentProviders[id] = newData;

        if (!isDefault)
        {
            $('#editATorrentProvider').addOption(id, name);
            $(this).populateTorrentSection();
        }

        if ($('#providerOrderList > #'+id).length == 0 && showProvider != false) {
            var toAdd = '<li class="ui-state-default" id="'+id+'"> <input type="checkbox" id="enable_'+id+'" class="provider_enabler" CHECKED> <a href="'+url+'" class="imgLink" target="_new"><img src="'+sbRoot+'/images/providers/templateshares.png" alt="'+name+'" width="16" height="16"></a> '+name+'</li>'

            $('#providerOrderList').append(toAdd);
            $('#providerOrderList').sortable("refresh");
        }

        $(this).makeTorrentProviderString();

    }

    $.fn.updateProvider = function (id, url, key) {

        newznabProviders[id][1][1] = url;
        newznabProviders[id][1][2] = key;

        $(this).populateNewznabSection();

        $(this).makeNewznabProviderString();
    
    }

    $.fn.updateTorrentProvider = function (id, url) {

        torrentProviders[id][1][1] = url;

        $(this).populateTorrentSection();

        $(this).makeTorrentProviderString();
    
    }

    $.fn.deleteProvider = function (id) {
    
        $('#editANewznabProvider').removeOption(id);
        delete newznabProviders[id];
        $(this).populateNewznabSection();

        $('#providerOrderList > #'+id).remove();

        $(this).makeNewznabProviderString();

    }

    $.fn.deleteTorrentProvider = function (id) {
    
        $('#editATorrentProvider').removeOption(id);
        delete torrentProviders[id];
        $(this).populateTorrentSection();

        $('#providerOrderList > #'+id).remove();

        $(this).makeTorrentProviderString();

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

    $.fn.populateTorrentSection = function() {

        var selectedProvider = $('#editATorrentProvider :selected').val();

        if (selectedProvider == 'addTorrent') {
            var data = ['','',''];
            var isDefault = 0;
            $('#torrent_add_div').show();
            $('#torrent_update_div').hide();
        } else {
            var data = torrentProviders[selectedProvider][1];
            var isDefault = torrentProviders[selectedProvider][0];
            $('#torrent_add_div').hide();
            $('#torrent_update_div').show();
        }

        $('#torrent_name').val(data[0]);
        $('#torrent_url').val(data[1]);
        
        if (selectedProvider == 'addTorrent') {
            $('#torrent_name').removeAttr("disabled");
            $('#torrent_url').removeAttr("disabled");
        } else {

            $('#torrent_name').attr("disabled", "disabled");

            if (isDefault) {
                $('#torrent_url').attr("disabled", "disabled");
                $('#torrent_delete').attr("disabled", "disabled");
            } else {
                $('#torrent_url').removeAttr("disabled");
                $('#torrent_delete').removeAttr("disabled");
            }
        }

    }
    
    $.fn.makeNewznabProviderString = function() {

        var provStrings = new Array();
        
        for (var id in newznabProviders) {
            provStrings.push(newznabProviders[id][1].join('|'));
        }

        $('#newznab_string').val(provStrings.join('!!!'))

    }
	
	$.fn.makeTorrentProviderString = function() {

        var provStrings = new Array();
        
        for (var id in torrentProviders) {
            provStrings.push(torrentProviders[id][1].join('|'));
        }

        $('#torrent_string').val(provStrings.join('!!!'))

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
	var torrentProviders = new Array();

    $('.newznab_key').change(function(){

        var provider_id = $(this).attr('id');
        provider_id = provider_id.substring(0, provider_id.length-'_hash'.length);

        var url = $('#'+provider_id+'_url').val();
        var key = $(this).val();

        $(this).updateProvider(provider_id, url, key);

    });
	
    $('.torrent_key').change(function(){

        var provider_id = $(this).attr('id');
        provider_id = provider_id.substring(0, provider_id.length-'_hash'.length);

        var url = $('#'+provider_id+'_url').val();

        $(this).updateTorrentProvider(provider_id, url);

    });
    
    $('#newznab_key').change(function(){
        
        var selectedProvider = $('#editANewznabProvider :selected').val();

        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();
        
        $(this).updateProvider(selectedProvider, url, key);
        
    });
    
    $('#torrent_key').change(function(){
        
        var selectedProvider = $('#editATorrentProvider :selected').val();

        var url = $('#torrent_url').val();
        
        $(this).updateTorrentProvider(selectedProvider, url);
        
    });
    
    $('#editAProvider').change(function(){
        $(this).showHideProviders();
    });

    $('#editANewznabProvider').change(function(){
        $(this).populateNewznabSection();
    });

    $('#editATorrentProvider').change(function(){
        $(this).populateTorrentSection();
    });
    
    $('.provider_enabler').live('click', function(){
        $(this).refreshProviderList();
    }); 
    

    $('#newznab_add').click(function(){
        
        var selectedProvider = $('#editANewznabProvider :selected').val();
        
        var name = $('#newznab_name').val();
        var url = $('#newznab_url').val();
        var key = $('#newznab_key').val();
        
        var params = { name: name }
        
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

    $('#torrent_add').click(function(){
        
        var selectedProvider = $('#editATorrentProvider :selected').val();
        
        var name = $('#torrent_name').val();
        var url = $('#torrent_url').val();
        
        var params = { name: name }
        
        // send to the form with ajax, get a return value
        $.getJSON(sbRoot + '/config/providers/canAddTorrentProvider', params,
            function(data){
                if (data.error != undefined) {
                    alert(data.error);
                    return;
                }

                $(this).addTorrentProvider(data.success, name, url, 0);
        });


    });

    $('.newznab_delete').click(function(){
    
        var selectedProvider = $('#editANewznabProvider :selected').val();

        $(this).deleteProvider(selectedProvider);

    });

    $('.torrent_delete').click(function(){
    
        var selectedProvider = $('#editATorrentProvider :selected').val();

        $(this).deleteTorrentProvider(selectedProvider);

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