$(document).ready(function() {
    $(document).on('click', '.logout-user', function (e) {
        e.preventDefault(); // MUST prevent default navigation

        let route = $(this).data('route');
        let message = $(this).data('message') || "Are you sure you want to logout?";
        let loginUrl = $(this).data('login-url'); // <- get the rendered login URL


        // Configure modal
        $('#confirmDeleteTitle').text('Confirm Logout');
        $('#confirmDeleteMessage').text(message);
        $('#confirmDeleteBtn')
            .text('Logout')
            .removeClass('btn-secondary')
            .addClass('btn-danger')
            .off('click')
            .on('click', function () {
                $.ajax({
                    url: route,
                    type: 'POST', // must match backend
                    success: function () {
                        window.location.href = loginUrl; // redirect to login
                    },
                    error: function () {
                        alert('Logout failed');
                    }
                });
                $('#confirmDeleteModal').modal('hide');
            });

        $('#confirmDeleteModal').modal('show');
    });
});

// function confirmDelete(route, message, method, dataTable) {

//     $('#confirmDeleteMessage').text(message);
//     $('#confirmDeleteModal').modal('show');

//     $('#confirmDeleteBtn').off('click').on('click', function () {
//         $.ajax({
//             url: route,
//             type: method,
//             success: function () {
//                 $('#confirmDeleteModal').modal('hide');
//                 dataTable.ajax.reload(null, false);
//             },
            
//             error: function () {
//                 alert('Something went wrong!');
//             }
//         });
//     });
// }


function confirmDelete(route, message, method, onSuccess) {

    $('#confirmDeleteMessage').text(message);
    $('#confirmDeleteModal').modal('show');

    $('#confirmDeleteBtn').off('click').on('click', function () {

        $.ajax({
            url: route,
            type: method,
            success: function () {
                $('#confirmDeleteModal').modal('hide');

                // ✅ DataTable case
                if (onSuccess && typeof onSuccess === 'object') {
                    onSuccess.ajax.reload(null, false);
                }

                // ✅ Simple list / card case
                if (typeof onSuccess === 'function') {
                    onSuccess();
                }
            },
            error: function () {
                alert('Something went wrong!');
            }
        });

    });
}
