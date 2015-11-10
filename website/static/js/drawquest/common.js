
dq = {};


dq._response_type = function (jq_xhr) {
    // Can detect text/html or application/json. If unknown, returns null. If known, returns the type name.
    var content_type = jq_xhr.getResponseHeader('Content-Type');
    var match = null;
    $(['text/html', 'application/json']).each(function (i, candidate) {
        if (content_type.indexOf(candidate) !== -1) {
            match = candidate;
        }
    });
    return match;
};

dq.api = function (api_path, params) {
    var def = new $.Deferred();

    if (api_path.indexOf('api/') === 0) {
        api_path = '/' + api_path;
    } else if (api_path.indexOf('/api/') !== 0) {
        api_path = '/api/' + api_path;
    }

    $.ajax({
        type        : 'POST',
        async       : true,
        url         : api_path,
        contentType : 'application/json',
        data        : JSON.stringify(params),
        success     : function (data, text_status, jq_xhr) {
            if (dq._response_type(jq_xhr) === 'text/html') {
                def.resolve(data, jq_xhr);
            } else {
                if (data.success) {
                    def.resolve(data, jq_xhr);
                } else {
                    def.reject(data, jq_xhr);
                }
            }
        },
        error: function (jq_xhr) {
            def.reject({'success': false, 'reason': jq_xhr.status}, jq_xhr);
        }
    });
    return def.promise();
};

