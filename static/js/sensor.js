/* script to dyanically update sensors */
alert("Read sensor data");

var handle = setInterval(getsensordata, 2000);

function getsensordata()
{
    new_ajax_helper('/sensors', receivesensordata);
}

function receivesensordata(results)
{
    console.log(results);
    for (key in results)
    {
        document.getElementById(key).innerHTML = results[key]

    }
}