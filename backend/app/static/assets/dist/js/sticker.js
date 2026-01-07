let currentPage = 1;
const itemsPerPage = 8;
let stickers = [];

function generateLabels(orderBoxes = [], storageBaseUrl = "") {
    // let quantity = parseInt(document.getElementById("quantityInput").value);

    let quantity = orderBoxes.length;

    if (quantity > 0) {
        document.getElementById("stickersSection").style.display = "block";
    } else {
        document.getElementById("stickersSection").style.display = "none";
    }

    const container = document.getElementById("labelsContainer");
    if (container) {
        container.innerHTML = "";
    }

    stickers = [];
    const table = document.createElement("table");
    table.className = "labels-table";

    // for (let i = 0; i < quantity; i += 2) {
    //     const row = document.createElement("tr");

    //     const checkboxCell = document.createElement("td");
    //     checkboxCell.className =
    //         "label-cell checkbox-cell text-center no-print p-3";

    //     const checkboxWrapper = document.createElement("label");
    //     checkboxWrapper.className = "checkbox-wrapper";

    //     const checkbox = document.createElement("input");
    //     checkbox.type = "checkbox";
    //     checkbox.classList.add("downloadRow");

    //     checkboxWrapper.appendChild(checkbox);
    //     checkboxCell.appendChild(checkboxWrapper);
    //     row.appendChild(checkboxCell);

    //     for (let j = 0; j < 2; j++) {
    //         const item = orderBoxes[i + j];
    //         if (!item) continue;

    //         if (j === 0) {
    //             checkbox.setAttribute("data-id", item.order_sequance_id);
    //         } else if (j === 1) {
    //             checkbox.setAttribute("data-order-id", item.order_sequance_id);
    //         }

    //         const qrCell = document.createElement("td");
    //         qrCell.className = "label-cell text-center";

    //         const image = storageBaseUrl + item.qr_code;

    //         const qrImg = document.createElement("img");
    //         qrImg.src = image;
    //         qrImg.alt = `QR for ${item.order_sequance_id}`;
    //         qrImg.style.display = "block";
    //         qrImg.style.margin = "0 auto";

    //         const orderIdText = document.createElement("div");
    //         orderIdText.innerText = item.order_sequance_id;
    //         orderIdText.style.fontSize = "12px";
    //         orderIdText.style.marginTop = "4px";

    //         qrCell.appendChild(orderIdText);
    //         qrCell.appendChild(qrImg);
    //         row.appendChild(qrCell);
    //         row.appendChild(createCell("DATE", "date"));
    //         row.appendChild(createCell("#ofboxes", "info"));
    //     }

    //     stickers.push(row);
    // }

    for (let i = 0; i < quantity; i++) {
        const item = orderBoxes[i];
        if (!item) continue;

        const row = document.createElement("tr");

        // Checkbox Cell
        const checkboxCell = document.createElement("td");
        checkboxCell.className =
            "label-cell checkbox-cell text-center no-print p-3";

        const checkboxWrapper = document.createElement("label");
        checkboxWrapper.className = "checkbox-wrapper";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.classList.add("downloadRow");
        checkbox.setAttribute("data-id", item.order_sequance_id);

        checkboxWrapper.appendChild(checkbox);
        checkboxCell.appendChild(checkboxWrapper);
        row.appendChild(checkboxCell);

        for (let repeat = 0; repeat < 2; repeat++) {
            const qrCell = document.createElement("td");
            qrCell.className = "label-cell text-center";

            const qrImg = document.createElement("img");
            qrImg.src = storageBaseUrl + item.qr_code;
            qrImg.alt = `QR for ${item.order_sequance_id}`;
            qrImg.style.display = "block";
            qrImg.style.margin = "0 auto";

            const orderIdText = document.createElement("div");
            orderIdText.innerText = item.order_sequance_id;
            orderIdText.style.fontSize = "12px";
            orderIdText.style.marginTop = "4px";

            qrCell.appendChild(orderIdText);
            qrCell.appendChild(qrImg);
            row.appendChild(qrCell);

            const dateCell = document.createElement("td");
            dateCell.className = "label-cell date";
            dateCell.innerText = "DATE";
            row.appendChild(dateCell);

            const infoCell = document.createElement("td");
            infoCell.className = "label-cell info";
            infoCell.innerText = "#ofboxes";
            row.appendChild(infoCell);
        }

        stickers.push(row);
    }

    const paginationContainer = document.createElement("div");
    paginationContainer.className = "pagination-container";

    const prevButton = document.createElement("button");
    prevButton.style.backgroundImage =
        'url("../../../icon/left-arrow-icon.svg")';
    prevButton.style.backgroundRepeat = "no-repeat";
    prevButton.style.backgroundPosition = "center";
    prevButton.style.padding = "15px";
    prevButton.style.border = "none";
    prevButton.style.cursor = "pointer";
    prevButton.disabled = currentPage === 1;
    prevButton.addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            renderPage(currentPage);
            updatePaginationButtons();
        }
    });

    const pageInfo = document.createElement("span");
    pageInfo.style.margin = "0 20px";
    pageInfo.style.fontWeight = "bold";

    const nextButton = document.createElement("button");
    nextButton.style.backgroundImage =
        'url("../../../icon/left-arrow-icon.svg")';
    nextButton.style.backgroundRepeat = "no-repeat";
    nextButton.style.backgroundPosition = "center";
    nextButton.style.transform = "rotate(180deg)";
    nextButton.style.padding = "15px";
    nextButton.style.border = "none";
    nextButton.style.cursor = "pointer";
    nextButton.disabled = currentPage * itemsPerPage >= quantity;
    nextButton.addEventListener("click", () => {
        if (currentPage * itemsPerPage < quantity) {
            currentPage++;
            renderPage(currentPage);
            updatePaginationButtons();
        }
    });

    function updatePaginationButtons() {
        prevButton.disabled = currentPage === 1;
        nextButton.disabled = currentPage * itemsPerPage >= quantity;
        const totalPages = Math.ceil(quantity / 2 / itemsPerPage);
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        pageInfo.classList.add("no-print");
    }

    paginationContainer.appendChild(prevButton);
    paginationContainer.appendChild(pageInfo);
    paginationContainer.appendChild(nextButton);

    if (container) {
        container.appendChild(table);
        container.appendChild(paginationContainer);
    }

    function renderPage(page) {
        const pageStart = (page - 1) * itemsPerPage;
        const pageEnd = pageStart + itemsPerPage;
        const pageStickers = stickers.slice(pageStart, pageEnd);
        table.innerHTML = "";
        pageStickers.forEach((row) => table.appendChild(row));
    }

    renderPage(currentPage);
    updatePaginationButtons();
}

document.addEventListener("DOMContentLoaded", function () {
    const checkboxes = document.querySelectorAll("input[type='checkbox']");
    const allUnchecked = [...checkboxes].every((checkbox) => !checkbox.checked);

    if (!allUnchecked) {
        generateLabels();
    }
});

function createCell(content, className) {
    const td = document.createElement("td");
    td.className = `label-cell ${className}`;
    td.textContent = content;
    return td;
}
