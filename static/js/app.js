//App specific JavaScript//App specific JavaScript
$(function () {
  $('[data-toggle="tooltip"]').tooltip()
})

//custom jquery to trigger dat picker, info pop-over and print category text
$(document).ready(function() {
    $('.datepicker').datepicker();
    $('.btn-del').click(function(e) {
        e.preventDefault();
        var msg = e.currentTarget.title;
        if (msg == undefined || msg.length == 0) {
            msg = "Are you sure you want to delete?";
        }
        var response = confirm(msg);
        if (response == true) {
            window.location = $(this).attr('href');
        }
    });
});

$('input[type="file"]').each(function() {
    var $file = $(this), $form = $file.closest('.upload-form');
    $file.ajaxSubmitInput({
        url: '/incident/add/', //URL where you want to post the form
        beforeSubmit: function($input) {
            //manipulate the form before posting
        },
        onComplete: function($input, iframeContent, options) {
            if (iframeContent) {
                $input.closest('form')[0].reset();
                if (!iframeContent) {
                    return;
                }
                var iframeJSON;
                try {
                    iframeJSON = $.parseJSON(iframeContent);
                    //use the response data
                } catch(err) {
                    console.log(err)
                }
            }
        }
    });
});

/*
 * Adds Django's messages to the template
 */
function addMessage(text, extra_tags) {
    var message = $('<div class="alert alert-' + extra_tags + '">' +
        '<a href="#" class="close" data-dismiss="alert">&times;</a>' +
        text + '</div>').hide();
    $("#alerts").append(message);
    message.fadeIn(50);
/*
    setTimeout(function() {
        message.fadeOut(500, function() {
            message.remove();
        });
    }, 10000);
*/
}

$(document).ready(function() {
    /*
     * Handle change in the province drop-down; updates the distirct drop-down accordingly.
     */
    
    // A global ajaxComplete method that shows you any messages that are set in Django's view
    $( document )
        .ajaxComplete(function(e, xhr, settings) {
            var contentType = xhr.getResponseHeader("Content-Type");

            if (contentType == "application/javascript" || contentType == "application/json") {
                var json = $.parseJSON(xhr.responseText);

                $.each(json.django_messages, function (i, item) {
                    addMessage(item.message, item.extra_tags);
                });
            }
        })
        .ajaxError(function(e, xhr, settings, thrownError) {
            //addMessage("There was an error processing your request, please try again.", "error");
            addMessage("Error " + xhr.status + ": " +  thrownError, "danger");
        });

    var $loading = $('#loading');
    $( document )
        .ajaxStart( function() {
            $loading.show();
        })
        .ajaxStop( function() {
            $loading.hide();
        });

    $("select#id_province").change(function() {
        var selected_province = $(this).val();
        if (selected_province == undefined || selected_province == -1 || selected_province == '') {
            $("select#id_district").html("<option>--Province--</option>");
        } else {
            var url = "/activitydb/province/" + selected_province + "/province_json/";
            $.getJSON(url, function(district) {
                var options = '<option value="0">--District--</option>';
                for (var i = 0; i < district.length; i++) {
                    options += '<option value="' + district[i].pk + '">' + district[i].fields['name'] + '</option>';
                }

                $("select#id_district").html(options);
                $("select#id_district option:first").attr('selected', 'selected');
            });
        }

        // page-specific-action call if a page has implemented the 'country_dropdwon_has_changed' function
        if(typeof country_dropdwon_has_changed != 'undefined') country_dropdwon_has_changed(selected_country);
    });

    /*
     * Handle change in office drop-down
     */
    $("select#id_district").change(function(vent) {
        var selected_distirct = $(this).val();
        if (selected_distirct == -1) {
            return;
        }

        // page-specific-action call if a page has implemented the 'office_dropdown_has_changed' function
        if(typeof district_dropdown_has_changed != 'undefined') distirct_dropdown_has_changed(district_office);
    });
});

/*
 * Get a cookie by name.
 */
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

/*
 * Set the csrf header before sending the actual ajax request
 * while protecting csrf token from being sent to other domains
 */
$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            //console.log("csrftoken: " + getCookie('csrftoken'));
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});




var tableObject = function (json, id) {
    var headerCount = new Object();

    var createTHEAD = function () {
        var thead = document.createElement('thead');
        return thead;
    }

    var createTBODY = function () {
        var tbody = document.createElement('tbody');
        return tbody;
    }

    var createTR = function (id) {
        var tr = document.createElement("tr");
        tr.ID = id;
        return tr;
    };

    var createTH = function (html) {
        var th = document.createElement("th");
        th.innerHTML = html;
        return th;
    };

    var createTD = function (html) {
        var td = document.createElement("td");
        td.innerHTML = html;
        return td;
    };

    var getName = function (id) {
        for (var name in headerCount) {
            if (eval("headerCount." + name) == id) {
                return name;
            }
        }
    };
    var data = json.slice();
    //data.forEach(function(v){ delete v.drilldown });
    var pTable;
    if (data.length > 0) {
        var index = 0;
        pTable = document.createElement("table");
        var thead = createTHEAD();
        var head = createTR();
        for (var i = 0; i < data.length; i++) {
            for (var item in data[i]) {
                if (item == 'drilldown'  || item == 'y') { continue };
                if (!headerCount.hasOwnProperty(item)) {
                    head.appendChild(createTH(item));
                    eval('headerCount.' + item + "=" + index);
                    index++;
                }
            }
        }
        thead.appendChild(head);
        pTable.appendChild(thead);
        var tbody = createTBODY();
        for (var i = 0; i < data.length; i++) {
            var row = new createTR(i);
            for (var j = 0; j < index; j++) {
                var name = getName(j);
                if (eval("data[" + i + "].hasOwnProperty('" + name + "')")) {
                    var cell_value = eval('data[' + i + '].' + name);
                    if (name == 'gait_id') {
                        cell_value = "<a href='https://gait.mercycorps.org/editgrant.vm?GrantID=" + cell_value + "' target='_blank'>" + cell_value + "</a>";
                    }
                    row.appendChild(createTD(cell_value));
                }
            }
            tbody.appendChild(row);
        }
        pTable.appendChild(tbody);
        pTable.setAttribute("id", id);
        pTable.setAttribute("class", "table table-striped table-bordered table-hover table-condensed");
    }
    return pTable;
};