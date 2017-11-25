var current_script = $("script[src*='js/common.js']");

function setVehicleImageById($image, id) {
    try {
        var color = $image.attr('data-exterior').toLowerCase();
        var url = "https://api.fuelapi.com/v1/json/vehicle/" + id + "/?api_key=" + current_script.attr('data-fuel-api') + "&productID=2&productFormatIDs=4";
        if (color != "none")
            url += "&color=" + color;

        $.getJSON(
            url,
            function (result) {
                var arr = result['products'][0]['productFormats'];
                for (var i in arr) {

                    var asset = undefined;

                    // find right color
                    for (var j in arr[i]['assets']) {

                        var temp_asset = arr[i]['assets'][j];

                        if (asset == undefined) {
                            asset = temp_asset;
                            break;
                        }
                    }
                }

                if (asset != undefined) {
                    $image.attr("src", asset['url']);
                }
            }
        ).fail(function () {

            // NOT FIND THE COLOR!!

            var url = "https://api.fuelapi.com/v1/json/vehicle/" + id + "/?api_key=" + current_script.attr('data-fuel-api') + "&productID=2&productFormatIDs=4";

            $.getJSON(
                url,
                function (result) {
                    var arr = result['products'][0]['productFormats'];
                    for (var i in arr) {
                        var asset = undefined;
                        var max_dist = undefined;

                        // find right color
                        for (var j in arr[i]['assets']) {

                            var temp_asset = arr[i]['assets'][j];
                            var dist = 0;

                            var temp_asset_color = temp_asset["shotCode"]["color"]["oem_name"].toLowerCase();
                            if (temp_asset_color.includes(color) || color.includes(temp_asset_color)) {
                                dist = 0;
                            }
                            else {
                                dist = CommonLength(temp_asset_color, color);
                            }

                            if (max_dist == undefined || dist > max_dist) {
                                asset = temp_asset;
                                max_dist = dist;

                                if (color == "none") {
                                    break;
                                }
                            }
                        }
                    }

                    if (asset != undefined) {
                        $image.attr("src", asset['url']);
                    }
                }
            ).fail(function (event, jqxhr, exception) {
                $image.attr("src", $image.attr('data-stock-image'));
            });

        });
    }
    catch (err) {
    }
}

function CommonLength(s, t) {
    var longest = 0;
    var i = 0;
    while (i < s.length) {
        var j = 0;
        while (j < t.length) {
            var common_length = 0;
            var k = 0;
            while (i + k < s.length && j + k < t.length && s[i + k] === t[j + k]) {
                common_length++;
                k++;
            }
            if (common_length > longest) {
                longest = common_length;
            }
            j++;
        }
        i++;
    }

    return longest;
}

function load_images() {
    $('.car-image.loading-image').each(function () {
        var $image = $(this);
        $image.removeClass('loading-image');
        try {
            $.getJSON(
                "https://api.fuelapi.com/v1/json/vehicles/?year=" + $image.attr('data-year') + "&make=" + $image.attr('data-make') + "&model=" + $image.attr('data-model') + "&api_key=" + current_script.attr('data-fuel-api'),
                function (result) {

                    var id = result[0]['id'];
                    setVehicleImageById($image, id);
                }
            ).fail(function (event, jqxhr, exception) {
                $image.attr("src", $image.attr('data-stock-image'));
            });
        }
        catch (err) {

        }
    });
}