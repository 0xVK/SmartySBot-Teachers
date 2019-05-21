function update_request_days_chart(){
  
  var request = new XMLHttpRequest();

  request.open('GET','last_days_statistics',true);
  request.addEventListener('readystatechange', function() {
    
    if ((request.readyState==4) && (request.status==200)) {

    ////////////////////////////////////////////////////////////////////
      response = JSON.parse(request.responseText);

      var ctx = document.getElementById("requests-on-days");
      var myChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: response.data.labels,
          datasets: [{ 
              data: response.data.data,
              label: "Кількість запитів",
              borderColor: "#D358F7",
              fill: true
            },
          ]
        },
        options: {
          legend: { display: false },
          title: {
            display: true,
            text: 'Запити по дням'
          }
        }
      });
      ////////////////////////////////////////////////////////////////////

        }
    }); 
    
request.send();
}

//window.onload = function() {
  update_request_days_chart();
  //setInterval(update_request_types_chart, 15000);
//}
