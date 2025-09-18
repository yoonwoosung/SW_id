// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {

    // --- 체험 신청 페이지 스크립트 ---
    const applyForm = document.getElementById('apply-form');
    if (applyForm) {
        applyForm.addEventListener('submit', function(event) {
            const consent = document.getElementById('privacy_consent');
            if (!consent.checked) {
                alert('개인정보 수집 및 이용에 동의해주세요.');
                event.preventDefault();
                return;
            }

            const name = document.getElementById('name').value;
            const confirmationMessage = `${name} 님의 정보로 신청하시겠습니까?\n\n제출 후에는 수정이 불가능합니다.`;

            if (!confirm(confirmationMessage)) {
                event.preventDefault();
            }
        });
    }

    // --- 봉사활동 상세 페이지의 날짜 선택 로직 ---
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
});