// main.js (farmer 기준으로 e-sibal 기능 추가 통합)

document.addEventListener('DOMContentLoaded', function() {

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
        
        const termsModal = document.getElementById('terms-modal');
        const viewTermsLink = document.getElementById('view-terms-link');
        const modalCloseBtn = document.getElementById('modal-close');
        const termsCheckbox = document.getElementById('terms');

        if (viewTermsLink) {
            viewTermsLink.addEventListener('click', function(event) {
                event.preventDefault();
                termsModal.style.display = 'flex';
            });
        }

        if (modalCloseBtn) {
            modalCloseBtn.addEventListener('click', function() {
                termsModal.style.display = 'none';
            });
        }
        
        if (termsModal) {
            termsModal.addEventListener('click', function(event) {
                if (event.target === termsModal) {
                    termsModal.style.display = 'none';
                }
            });
        }

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
            if (!termsCheckbox.checked) {
                alert('서비스 이용 약관에 동의해야 회원가입을 진행할 수 있습니다.');
                event.preventDefault();
            }
        });
    }

    // --- 농장주 대시보드 프로필/농장 사진 업로드 스크립트 ---
    const profilePicInput = document.getElementById('profile-pic-input');
    const profilePicForm = document.getElementById('profile-pic-form');
    const profilePicPreview = document.getElementById('profile-pic-preview');

    if (profilePicInput) {
        profilePicInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    profilePicPreview.src = e.target.result;
                }
                reader.readAsDataURL(this.files[0]);
                profilePicForm.submit();
            }
        });
    }

    const farmPhotoInput = document.getElementById('farm-photo-input');
    const farmPhotoForm = document.getElementById('farm-photo-form');

    if (farmPhotoInput) {
        farmPhotoInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                farmPhotoForm.submit();
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

    // --- 농장 등록 시간표 제출 로직 (farmer 방식) ---
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
            const timetableInput = document.getElementById('timetable-data');
            timetableInput.value = selectedSlots.join(',');
        });
    }

    // --- 이용가이드 슬라이더 스크립트 (farmer 기능) ---
    const slider = document.getElementById('guide-slider');
    if (slider) {
        const slides = slider.querySelector('.guide-slides');
        const slide = slider.querySelectorAll('.guide-slide');
        const prevBtn = slider.querySelector('.prev-btn');
        const nextBtn = slider.querySelector('.next-btn');
        const pagination = slider.querySelector('.slider-pagination');
        let currentIndex = 0;
        const slideCount = slide.length;

        for (let i = 0; i < slideCount; i++) {
            const dot = document.createElement('span');
            dot.classList.add('pagination-dot');
            dot.addEventListener('click', () => goToSlide(i));
            pagination.appendChild(dot);
        }

        const dots = pagination.querySelectorAll('.pagination-dot');

        function updateSlider() {
            slides.style.transform = `translateX(-${currentIndex * 100}%)`;
            dots.forEach((dot, index) => {
                dot.classList.toggle('active', index === currentIndex);
            });
        }

        function goToSlide(index) {
            currentIndex = index;
            updateSlider();
        }

        nextBtn.addEventListener('click', () => {
            currentIndex = (currentIndex + 1) % slideCount;
            updateSlider();
        });

        prevBtn.addEventListener('click', () => {
            currentIndex = (currentIndex - 1 + slideCount) % slideCount;
            updateSlider();
        });

        updateSlider();
    }
    
    // --- 캐러셀 배너 '후기 작성하기' 버튼 스크립트 (e-sibal 기능) ---
    const writeReviewBtn = document.getElementById('write-review-btn');
    if (writeReviewBtn) {
        writeReviewBtn.addEventListener('click', function(event) {
            event.preventDefault();
            const isLoggedIn = this.dataset.isLoggedIn === 'true';
            const loginUrl = this.dataset.loginUrl;
            const targetUrl = this.dataset.targetUrl;

            if (isLoggedIn) {
                alert("후기를 작성할 체험을 목록에서 선택해주세요.");
                window.location.href = targetUrl;
            } else {
                alert("후기를 작성하려면 먼저 로그인이 필요합니다.");
                window.location.href = loginUrl;
            }
        });
    }
    const recommendedSortLink = document.querySelector('.recommended-sort-link');
    if (recommendedSortLink && recommendedSortLink.classList.contains('active')) {
        const urlParams = new URLSearchParams(window.location.search);
        if (!urlParams.has('lat') || !urlParams.has('lon')) {
            navigator.geolocation.getCurrentPosition(function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                // 기존 쿼리 파라미터를 유지하면서 lat, lon 추가
                urlParams.set('sort', 'recommended');
                urlParams.set('lat', lat);
                urlParams.set('lon', lon);
                window.location.search = urlParams.toString();
            }, function(error) {
                console.error("Geolocation error: ", error);
                alert("위치 정보를 허용해야 추천순 정렬을 이용할 수 있습니다. 모집 임박순으로 정렬합니다.");
                // 위치 정보 거부 시, deadline으로 리디렉션
                urlParams.set('sort', 'deadline');
                urlParams.delete('lat');
                urlParams.delete('lon');
                window.location.search = urlParams.toString();
            });
        }
    }

    // --- Guide Modal for detail_experience.html ---
    const guideModal = document.getElementById('guide-modal');
    const guideModalBtn = document.getElementById('guide-modal-btn');
    const guideModalClose = document.getElementById('guide-modal-close');

    if (guideModalBtn) {
        guideModalBtn.addEventListener('click', function() {
            if (guideModal) guideModal.style.display = 'block';
        });
    }

    if (guideModalClose) {
        guideModalClose.addEventListener('click', function() {
            if (guideModal) guideModal.style.display = 'none';
        });
    }

    // --- Guide Popup Modal for detail_experience.html ---
    const guidePopupModal = document.getElementById('guide-popup-modal');
    const guidePopupBtn = document.getElementById('guide-popup-btn');
    const guidePopupModalClose = document.getElementById('guide-popup-modal-close');

    if (guidePopupBtn) {
        guidePopupBtn.addEventListener('click', function() {
            if (guidePopupModal) guidePopupModal.style.display = 'block';
        });
    }

    if (guidePopupModalClose) {
        guidePopupModalClose.addEventListener('click', function() {
            if (guidePopupModal) guidePopupModal.style.display = 'none';
        });
    }

    // --- Farmer Dashboard Modals ---
    const farmerGuidePopupModal = document.getElementById('farmer-guide-popup-modal');
    const farmerGuidePopupBtn = document.getElementById('farmer-guide-popup-btn');
    const farmerGuidePopupClose = document.getElementById('farmer-guide-popup-close');

    if (farmerGuidePopupBtn) {
        farmerGuidePopupBtn.addEventListener('click', function() {
            if (farmerGuidePopupModal) farmerGuidePopupModal.style.display = 'block';
        });
    }

    if (farmerGuidePopupClose) {
        farmerGuidePopupClose.addEventListener('click', function() {
            if (farmerGuidePopupModal) farmerGuidePopupModal.style.display = 'none';
        });
    }

    const farmerHowToUseModal = document.getElementById('farmer-how-to-use-modal');
    const farmerHowToUseBtn = document.getElementById('farmer-how-to-use-btn');
    const farmerHowToUseClose = document.getElementById('farmer-how-to-use-close');

    if (farmerHowToUseBtn) {
        farmerHowToUseBtn.addEventListener('click', function() {
            if (farmerHowToUseModal) farmerHowToUseModal.style.display = 'block';
        });
    }

    if (farmerHowToUseClose) {
        farmerHowToUseClose.addEventListener('click', function() {
            if (farmerHowToUseModal) {
                farmerHowToUseModal.style.display = 'none';
                // Stop carousel video from playing in the background if any
                $('#how-to-use-carousel').carousel('pause');
            }
        });
    }

    window.addEventListener('click', function(event) {
        if (event.target == guideModal) {
            guideModal.style.display = 'none';
        }
        if (event.target == guidePopupModal) {
            guidePopupModal.style.display = 'none';
        }
        if (event.target == farmerGuidePopupModal) {
            farmerGuidePopupModal.style.display = 'none';
        }
        if (event.target == farmerHowToUseModal) {
            farmerHowToUseModal.style.display = 'none';
            $('#how-to-use-carousel').carousel('pause');
        }
    });

}); // DOMContentLoaded end

// --- 체험 삭제 확인 함수 ---
function confirmDelete() {
    return confirm("정말로 이 체험을 삭제하시겠습니까?\n삭제된 데이터는 복구할 수 없으며, 이로 인한 모든 책임은 본인에게 있습니다.");
}