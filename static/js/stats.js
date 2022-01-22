var intervalID = setInterval(update_values, 1000);

function update_values() {
  $.getJSON("/_stats", function (data) {
    console.log(data);
    $("#members").text(data.members);
    $("#servers").text(data.servers);
    $("#messages").text(data.messages);
    $("#commands").text(data.commands);
    $("#uptime").text(data.uptime);
    $("#channels").text(data.channels);
  });
}