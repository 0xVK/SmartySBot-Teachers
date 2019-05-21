function update_request_types_chart(){
  
  var request = new XMLHttpRequest();

  request.open('GET','statistics_by_types_during_the_week',true);
  request.addEventListener('readystatechange', function() {
    
    if ((request.readyState==4) && (request.status==200)) {

    ////////////////////////////////////////////////////////////////////
      response = JSON.parse(request.responseText);

      today = response['data']['TODAY'];
      tomorrow = response['data']['TOMORROW'];
      for_a_week = response['data']['FOR_A_WEEK'];
      for_a_teacher = response['data']['FOR_A_TEACHER'];
      timetable = response['data']['TIMETABLE'];
      for_a_group = response['data']['FOR_A_GROUP'];
      // change_group = response['data']['CHANGE_GROUP'];
      weather = response['data']['WEATHER'];
      help = response['data']['HELP'];
      for_a_date = response['data']['FOR_A_DATE'];
      other = response['data']['OTHER'];

      var ctx = document.getElementById("requests-types-chart");
      
      var myChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: [
                'Сьогодні',
                'Завтра',
                'Тиждень',
                'По викладачу',
                'Час пар',
                'По групі',
                //'Зм. групу',
                'Погода',
                'Довідка',
                'По даті',
                'Інше'
            ],
            datasets: [{
                data: [today,
                       tomorrow,
                       for_a_week,
                       for_a_teacher,
                       timetable,
                       for_a_group,
                       //change_group,
                       weather,
                       help,
                       for_a_date,
                       other
                      ],
                backgroundColor: [
                  "#3e95cd",
                  '#FE9A2E',
                  "#8e5ea2",
                  "#3cba9f",
                  "#F781D8",
                  '#9F81F7',
                  //"#c45850",
                  '#01DF01',
                  '#FFFF00',
                  '#81DAF5',
                  '#BDBDBD',
                   ],
            }],
          },
        options: {
            legend: { display: false },
            title: {
              display: true,
              text: 'Діаграма розподілення запитів (за тиждень)'
            }
          }
      });
      ////////////////////////////////////////////////////////////////////

        }
    }); 
    
request.send();
}

//window.onload = function() {
  update_request_types_chart();
  //setInterval(update_request_types_chart, 15000);
//}
