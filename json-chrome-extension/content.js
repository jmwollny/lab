// http://jsfiddle.net/alanwsmith/EwT4E/
function jsonPrettyHighlight(_jsonObj) {
    
    var json = JSON.stringify(_jsonObj, undefined, 2);
    
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    json = json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'json-value-int';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'json-key';
            } else {
                cls = 'json-value-str';
            }
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
    return json;    
}


try {
    jsonObject = JSON.parse(document.body.innerText);
    if (jsonObject) {

        var prettyPrintedJson = jsonPrettyHighlight(jsonObject);
        var container = document.createElement("pre");
        document.body.firstChild.style.display = "none";

        container.innerHTML = prettyPrintedJson;
        document.body.appendChild(container);    
    }
} catch (ex) {
    // do nothing, the current page is not altered
}
