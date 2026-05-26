let chart;

// ================= SECTION NAVIGATION =================

function showSection(event, sectionId) {

    const sections =
        document.querySelectorAll('.content-section');

    sections.forEach(section => {

        section.classList.add('hidden-section');

    });

    document.getElementById(sectionId)
        .classList.remove('hidden-section');

    const buttons =
        document.querySelectorAll('.nav-btn');

    buttons.forEach(button => {

        button.classList.remove('active');

    });

    event.target.classList.add('active');
}

// ================= DATASET UPLOAD =================

async function uploadDataset() {

    const fileInput =
        document.getElementById('dataset');

    if (!fileInput.files.length) {

        alert('Please select CSV dataset');

        return;
    }

    const formData = new FormData();

    formData.append('file',
        fileInput.files[0]);

    const response = await fetch('/upload', {

        method: 'POST',

        body: formData

    });

    const data = await response.json();

    if (data.status === 'success') {

        alert('Dataset uploaded successfully');

    } else {

        alert(data.message);

    }
}

// ================= ANALYSIS =================

async function analyzeData() {

    const startDate =
        document.getElementById('startDate').value;

    const endDate =
        document.getElementById('endDate').value;

    const response = await fetch('/analysis', {

        method: 'POST',

        headers: {

            'Content-Type': 'application/json'

        },

        body: JSON.stringify({

            start_date: startDate,

            end_date: endDate

        })

    });

    const data = await response.json();

    if (data.status === 'error') {

        alert(data.message);

        return;
    }

    document.getElementById('loans').innerText =
        `₹${Number(data.total_loans).toLocaleString()}`;

    document.getElementById('deposits').innerText =
        `₹${Number(data.total_deposits).toLocaleString()}`;

    document.getElementById('balance').innerText =
        `₹${Number(data.average_balance).toLocaleString()}`;

    document.getElementById('segment').innerHTML =

        `Low: ${data.segmentation.low}<br>
         Medium: ${data.segmentation.medium}<br>
         High: ${data.segmentation.high}`;

    renderChart(data.segmentation);
}

// ================= CHART =================

function renderChart(segmentation) {

    const ctx =
        document.getElementById('chart')
        .getContext('2d');

    if (chart) {

        chart.destroy();

    }

    chart = new Chart(ctx, {

        type: 'doughnut',

        data: {

            labels: [

                'Low',

                'Medium',

                'High'

            ],

            datasets: [{

                data: [

                    segmentation.low,

                    segmentation.medium,

                    segmentation.high

                ],

                backgroundColor: [

                    '#ef4444',

                    '#f59e0b',

                    '#10b981'

                ],

                borderWidth: 2

            }]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

                legend: {

                    labels: {

                        color: 'white',

                        font: {

                            size: 14

                        }

                    }

                }

            }

        }

    });

}