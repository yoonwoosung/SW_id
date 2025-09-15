// static/js/main.js

// 페이지의 모든 내용이 로드된 후 스크립트 실행
document.addEventListener('DOMContentLoaded', function() {
    // --- 관리 드롭다운 메뉴 토글 기능 ---
const dropdowns = document.querySelectorAll('.manage-dropdown');

dropdowns.forEach(dropdown => {
    const toggleButton = dropdown.querySelector('.dropdown-toggle');
    const menu = dropdown.querySelector('.dropdown-menu');

    toggleButton.addEventListener('click', function(event) {
        // 다른 열린 메뉴가 있으면 닫기
        document.querySelectorAll('.dropdown-menu.show').forEach(openMenu => {
            if (openMenu !== menu) {
                openMenu.classList.remove('show');
            }
        });
        // 현재 메뉴 열기/닫기
        menu.classList.toggle('show');
        event.stopPropagation();
    });
});

// 화면의 다른 곳을 클릭하면 메뉴 닫기
window.addEventListener('click', function(event) {
    if (!event.target.matches('.dropdown-toggle')) {
        document.querySelectorAll('.dropdown-menu.show').forEach(openMenu => {
            openMenu.classList.remove('show');
        });
    }
});
    
    // 봉사활동 상세 페이지의 날짜 선택 로직
    const dateGrid = document.querySelector('.date-grid');

    if (dateGrid) {
        const selectableDates = dateGrid.querySelectorAll('.date-box.selectable');
        const totalHoursDisplay = document.getElementById('total-hours');
        const hoursPerDay = parseInt(dateGrid.dataset.hoursPerDay, 10);

        selectableDates.forEach(function(dateBox) {
            dateBox.addEventListener('click', function() {
                // 'selected' 클래스를 추가하거나 제거하여 선택 상태를 토글
                dateBox.classList.toggle('selected');
                
                // 선택된 날짜들의 총 봉사 시간 다시 계산
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
