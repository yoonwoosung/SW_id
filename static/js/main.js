// main.js (farmer 기준으로 e-sibal 기능 추가 통합)

document.addEventListener('DOMContentLoaded', function() {

    function setupModal(btnId, modalId, closeBtnId) {
        const modal = document.getElementById(modalId);
        const btn = document.getElementById(btnId);
        const closeBtn = document.getElementById(closeBtnId);
        const carousel = modal ? modal.querySelector('.carousel') : null;

        if (btn && modal) {
            btn.onclick = function(e) {
                e.preventDefault();
                modal.style.display = "block";
                if (carousel) {
                    $(carousel).carousel('pause');
                }
            }
        }

        function closeModal() {
            if (modal) {
                modal.style.display = "none";
                if (carousel) {
                    $(carousel).carousel('pause');
                }
            }
            document.body.classList.remove('scroll-lock');
        }

        if (closeBtn) {
            closeBtn.onclick = closeModal;
        }

        window.addEventListener('click', function(event) {
            if (event.target == modal) {
                closeModal();
            }
        });
    }

    // --- 모든 모달 초기화 ---
    setupModal('guide-modal-btn', 'guide-modal', 'guide-modal-close');
    setupModal('guide-popup-btn', 'guide-popup-modal', 'guide-popup-modal-close');
    setupModal('farmer-guide-popup-btn', 'farmer-guide-popup-modal', 'farmer-guide-popup-close');
    setupModal('farmer-how-to-use-btn', 'farmer-how-to-use-modal', 'farmer-how-to-use-close');
    setupModal('view-terms-link', 'terms-modal', 'modal-close');


    // --- 회원가입 페이지 스크립트 ---
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        let isEmailChecked = false;
        const emailInput = document.getElementById('email');
        const checkEmailBtn = document.getElementById('check-email-btn');
        const emailMsg = emailInput.closest('.form-group').querySelector('.validation-message');
        emailInput.addEventListener('input', function() {
            isEmailChecked = false;
            emailMsg.textContent = ''; // 메시지도 초기화
        });

        checkEmailBtn.addEventListener('click', async function() {
            const email = emailInput.value;
            if (!email) {
                emailMsg.textContent = '이메일을 입력해주세요.';
                emailMsg.className = 'validation-message text-danger';
                return;
            }
            const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
            if (!emailRegex.test(email)) {
                emailMsg.textContent = '올바른 이메일 형식이 아닙니다.';
                emailMsg.className = 'validation-message text-danger';
                return;
            }
            const response = await fetch('/check_email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            });
            const data = await response.json();
            if (data.exists) {
                emailMsg.textContent = '해당 이메일은 이미 사용된 이메일입니다.';
                emailMsg.className = 'validation-message text-danger';
                isEmailChecked = false; // 실패 시 상태 변경
            } else {
                emailMsg.textContent = '사용 가능한 이메일입니다.';
                emailMsg.className = 'validation-message text-success';
                isEmailChecked = true;
            }
        });

        const passwordInput = document.getElementById('password');
        const passwordConfirmInput = document.getElementById('password-confirm');
        const passwordMsg = passwordConfirmInput.closest('.form-group').querySelector('.validation-message');

        function checkPasswords() {
            if (passwordConfirmInput.value && passwordInput.value !== passwordConfirmInput.value) {
                passwordMsg.textContent = '비밀번호가 일치하지 않습니다.';
                passwordMsg.className = 'validation-message text-danger';
            } else {
                passwordMsg.textContent = '';
            }
        }
        passwordInput.addEventListener('input', checkPasswords);
        passwordConfirmInput.addEventListener('input', checkPasswords);

        document.querySelectorAll('.toggle-password').forEach(button => {
            button.addEventListener('click', function() {
                const inputGroup = this.closest('.input-group');
                const input = inputGroup.querySelector('input');
                const icon = this.querySelector('i');
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                } else {
                    input.type = 'password';
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                }
            });
        });

        registerForm.addEventListener('submit', function(event) {
            const password = passwordInput.value;
            const passwordConfirm = passwordConfirmInput.value;

            if (password !== passwordConfirm) {
                alert('비밀번호가 일치하지 않습니다. 다시 확인해주세요.');
                event.preventDefault();
                return;
            }
            if (!isEmailChecked) {
                alert('이메일 중복 확인을 먼저 진행해주세요.');
                event.preventDefault();
                return;
            }
            if (!document.getElementById('terms').checked) {
                alert('서비스 이용 약관에 동의해야 회원가입을 진행할 수 있습니다.');
                event.preventDefault();
            }
        });
    }

    // --- 농장주 대시보드 프로필/농장 사진 업로드 스크립트 ---
    const profilePicInput = document.getElementById('profile-pic-input');
    if (profilePicInput) {
        profilePicInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                document.getElementById('profile-pic-form').submit();
            }
        });
    }

    const farmPhotoInput = document.getElementById('farm-photo-input');
    if (farmPhotoInput) {
        farmPhotoInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                document.getElementById('farm-photo-form').submit();
            }
        });
    }

    // --- 농장 등록 페이지 (jQuery 사용 부분) ---
    $('#images').on('change', function() {
        var fileList = "선택된 파일: ";
        for (var i = 0; i < this.files.length; i++) {
            fileList += this.files[i].name + ", ";
        }
        fileList = fileList.slice(0, -2);
        $(this).next('.custom-file-label').html(fileList);
    });

    $('#farm-register-form').on('submit', function(e) {
        if (!$('#terms').is(':checked')) {
            alert("서비스 이용 약관에 동의해주세요.");
            e.preventDefault();
        }
    });

    // --- 농장 등록 시간표 제출 로직 ---
    const farmRegisterFormForTimetable = document.getElementById('farm-register-form');
    if (farmRegisterFormForTimetable) {
        farmRegisterFormForTimetable.addEventListener('submit', function() {
            const selectedSlots = [];
            document.querySelectorAll('.timetable .time-slot.selected').forEach(slot => {
                const rowIndex = slot.parentNode.rowIndex;
                const cellIndex = slot.cellIndex;
                const time = document.querySelector(`.timetable tbody tr:nth-child(${rowIndex}) td:first-child`).textContent;
                const day = document.querySelector(`.timetable thead th:nth-child(${cellIndex + 1})`).textContent;
                selectedSlots.push(`${day}-${time.split(' ')[0]}`);
            });
            document.getElementById('timetable-data').value = selectedSlots.join(',');
        });
    }

    // --- 이용가이드 슬라이더 스크립트 ---
    const slider = document.getElementById('guide-slider');
    if (slider) {
        // ... (slider logic) ...
    }
    
    // --- 캐러셀 배너 '후기 작성하기' 버튼 스크립트 ---
    const writeReviewBtn = document.getElementById('write-review-btn');
    if (writeReviewBtn) {
        writeReviewBtn.addEventListener('click', function(event) {
            event.preventDefault();
            if (this.dataset.isLoggedIn === 'true') {
                alert("후기를 작성할 체험을 목록에서 선택해주세요.");
                window.location.href = this.dataset.targetUrl;
            } else {
                alert("후기를 작성하려면 먼저 로그인이 필요합니다.");
                window.location.href = this.dataset.loginUrl;
            }
        });
    }

    // --- 추천순 정렬 위치 정보 요청 ---
    const recommendedSortLink = document.querySelector('.recommended-sort-link');
    if (recommendedSortLink && recommendedSortLink.classList.contains('active')) {
        const urlParams = new URLSearchParams(window.location.search);
        if (!urlParams.has('lat') || !urlParams.has('lon')) {
            navigator.geolocation.getCurrentPosition(function(position) {
                urlParams.set('sort', 'recommended');
                urlParams.set('lat', position.coords.latitude);
                urlParams.set('lon', position.coords.longitude);
                window.location.search = urlParams.toString();
            }, function(error) {
                console.error("Geolocation error: ", error);
                alert("위치 정보를 허용해야 추천순 정렬을 이용할 수 있습니다. 모집 임박순으로 정렬합니다.");
                urlParams.set('sort', 'deadline');
                urlParams.delete('lat');
                urlParams.delete('lon');
                window.location.search = urlParams.toString();
            });
        }
    }

}); // DOMContentLoaded end

// --- 체험 삭제 확인 함수 ---
function confirmDelete() {
    return confirm("정말로 이 체험을 삭제하시겠습니까?\n삭제된 데이터는 복구할 수 없으며, 이로 인한 모든 책임은 본인에게 있습니다.");
}