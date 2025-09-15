// static/js/main.js

// 페이지의 모든 내용이 로드된 후 스크립트 실행
document.addEventListener('DOMContentLoaded', function() {
    
    // 봉사활동 상세 페이지의 날짜 선택 로직
    const dateGrid = document.querySelector('.date-grid');

    if (dateGrid) {
        const selectableDates = dateGrid.querySelectorAll('.date-box.selectable');
        const totalHoursDisplay = document.getElementById('total-hours');
        const hoursPerDay = parseInt(dateGrid.dataset.hoursPerDay, 10);

        selectableDates.forEach(function(dateBox) {
            dateBox.addEventListener('click', function() {
                dateBox.classList.toggle('selected');
                updateTotalHours();
            });
        });

        function updateTotalHours() {
            const selectedBoxes = dateGrid.querySelectorAll('.date-box.selected');
            const totalHours = selectedBoxes.length * hoursPerDay;
            totalHoursDisplay.textContent = totalHours;
        }
    }

    // 농장 등록 페이지 - 운영 시간표 선택 로직
    const timetable = document.querySelector('.timetable');
    if (timetable) {
        const timeSlots = timetable.querySelectorAll('.time-slot');
        timeSlots.forEach(function(slot) {
            slot.addEventListener('click', function() {
                slot.classList.toggle('selected');
            });
        });
    }
});