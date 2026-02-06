$(document).ready(function () {
    $(document).on("click", ".logout-user", function () {
        let route = $(this).data("route");
        let confirmationMsg = "Are you sure you want to logout?";
        confirmDelete(route, confirmationMsg, "GET", null);
    });

    $(".telephone").on("input", function () {
        let val = $(this)
            .val()
            .replace(/[^0-9,()-]/g, "");
        if (val.length > 15) {
            val = val.slice(0, 15);
        }
        $(this).val(val);
    });
    
});

function confirmDelete(url, msg, method, dataTable) {
    $.prompt(msg, {
        title: "Are you sure?",
        buttons: {
            No: false,
            Yes: true,
        },
        focus: 1,
        submit: function (e, v, m, f) {
            if (v) {
                e.preventDefault();
                $.ajax({
                    // headers: {
                    //     "X-CSRF-Token": $('meta[name="csrf-token"]').attr(
                    //         "content"
                    //     ),
                    // },
                    type: method,
                    url: url,
                    success: function (response) {
                        if (response.status == 200) {
                            toastr.success(response.message);

                            setTimeout(function () {
                                if (dataTable != null) {
                                    dataTable.ajax.reload(null, false);
                                } else {
                                    location.reload();
                                }
                            }, 1000);
                        } else {
                            toastr.error(response.message);
                        }
                    },
                });
            }
            $.prompt.close();
        },
    });
}

