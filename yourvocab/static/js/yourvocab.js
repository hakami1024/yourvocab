"use strict";

function submitForm(show_answer, no_upd) {
    var oFormElement = $('#test_form').get(0);
    console.log(oFormElement);
    var xhr = new XMLHttpRequest();
    xhr.onload = function () {
        var resp = JSON.parse(xhr.responseText);
        if (resp['result'] === 'ok') {
            $('#hint_row').hide();
            if (resp['last']) {
                $('#RespondingPart').hide();
            } else {
                $('#RespondingPart').show();
            }
            $('#mistake_field').hide();
            $('#Question').text(resp['question']);
            $('#answer_field').val('');
        } else if (resp['result'] === 'show_answer') {
            $('#RespondingPart').hide();
            $('#mistake_field').hide();
            $('#hint_field').text(resp['answer']);
            $('#hint_row').show()
        } else if (resp['result'] === 'mistake') {
            $('#hint_row').hide();
            $('#mistake_field').show();
            $('#RespondingPart').show();
        } else {
            alert(xhr.responseText);
        }

        $('#score_field').text(resp['score']);

        console.log(xhr.responseText)
    }; // success case
    xhr.onerror = function () {
        alert(xhr.responseText);
        console.log(xhr.responseText)
    }; // failure case
    xhr.open(oFormElement.method, oFormElement.action, true);
    var fd = new FormData(oFormElement);
    fd.append('show_answer', show_answer);
    fd.append('no_score_upd', no_upd);
    console.log(fd.entries());
    xhr.send(fd);
    return false;
}